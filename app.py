import os
import threading
import random
import asyncio
import time
import traceback

from flask import Flask, render_template, request, redirect, url_for, jsonify

# coba import discord (discord.py-self). Jika gagal, tampilkan pesan di UI.
try:
    import discord
    from discord.ext import commands
    DISCORD_IMPORT_ERROR = None
except Exception:
    discord = None
    commands = None
    DISCORD_IMPORT_ERROR = traceback.format_exc()

app = Flask(__name__, static_folder="static", template_folder="templates")

# Global state
bot_thread = None
discord_client = None
bot_running = False
bot_error = None
_last_start_params = None

# Simpan user_id yang sudah pernah dibalas selama bot hidup
responded_users = set()


def _create_client(reply_message):
    """
    Buat client / bot object (best-effort compatible).
    """
    # configure intents jika tersedia
    intents = None
    try:
        if hasattr(discord, "Intents"):
            intents = discord.Intents.default()
            if hasattr(intents, "messages"):
                intents.messages = True
            if hasattr(intents, "dm_messages"):
                intents.dm_messages = True
            # beberapa versi butuh message_content untuk membaca teks
            if hasattr(intents, "message_content"):
                intents.message_content = True
    except Exception:
        intents = None

    try:
        if commands is not None and hasattr(commands, "Bot"):
            if intents is not None:
                client = commands.Bot(command_prefix=".", self_bot=True, intents=intents)
            else:
                client = commands.Bot(command_prefix=".", self_bot=True)
        else:
            # fallback ke Client
            if intents is not None:
                client = discord.Client(intents=intents)
            else:
                client = discord.Client()
    except Exception:
        client = discord.Client()

    @client.event
    async def on_ready():
        print(f"[bot] Logged in as: {getattr(client, 'user', None)}")

    @client.event
    async def on_message(message):
        global responded_users
        # jangan balas pesan sendiri
        try:
            if message.author.id == client.user.id:
                return
        except Exception:
            pass

        # cek channel DM (private)
        try:
            is_dm = False
            if hasattr(discord, "DMChannel") and isinstance(message.channel, discord.DMChannel):
                is_dm = True
            else:
                ch_type = getattr(message.channel, "type", None)
                if ch_type is not None:
                    if str(ch_type).lower().startswith("private") or str(ch_type).lower() == "dm":
                        is_dm = True
        except Exception:
            is_dm = False

        if is_dm:
            # hanya balas sekali per user selama bot hidup
            try:
                uid = message.author.id
            except Exception:
                uid = None

            if uid is not None and uid in responded_users:
                # sudah pernah dibalas -> skip
                return

            try:
                # indikator mengetik jika tersedia
                try:
                    await message.channel.trigger_typing()
                except Exception:
                    pass

                # jeda acak supaya terlihat manusiawi
                await asyncio.sleep(random.uniform(2.0, 5.5))

                # kirim balasan
                await message.channel.send(reply_message)

                # tandai user ini sudah dibalas
                if uid is not None:
                    responded_users.add(uid)
            except Exception as e:
                print("[bot] Failed to reply:", e)

    return client


def _run_bot(token, reply_message):
    """
    Fungsi yang akan dijalankan di thread terpisah; blok sampai client berhenti.
    """
    global bot_running, bot_error, discord_client, responded_users
    bot_error = None

    if DISCORD_IMPORT_ERROR is not None:
        bot_error = "Discord import error. Lihat server console."
        bot_running = False
        return

    # reset daftar yang sudah dibalas setiap kali bot start baru
    responded_users.clear()

    try:
        client = _create_client(reply_message)
        discord_client = client
        bot_running = True
        print("[run_bot] starting client.run() …")
        # client.run akan membuat dan menjalankan event loop sendiri (blocking)
        client.run(token)
    except Exception as e:
        bot_error = traceback.format_exc()
        print("[run_bot] Exception:\n", bot_error)
    finally:
        bot_running = False
        discord_client = None
        print("[run_bot] client ended.")


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html",
                           running=bot_running,
                           error=bot_error,
                           discord_import_error=DISCORD_IMPORT_ERROR)


def _read_request_data():
    """
    Helper: baca data baik dari JSON (AJAX) atau dari form (standard form POST).
    Kembalikan dict-like object.
    """
    if request.is_json:
        return request.get_json()
    return request.form


@app.route("/start", methods=["POST"])
def start():
    global bot_thread, bot_running, bot_error, _last_start_params

    data = _read_request_data()
    token = (data.get("token") or "").strip()
    # terima nama field 'reply' atau 'reply_message'
    reply = (data.get("reply") or data.get("reply_message") or data.get("message") or "").strip()

    if not token or not reply:
        bot_error = "Token dan pesan wajib diisi."
        # kalau request asal form (browser) redirect ke UI
        if not request.is_json:
            return redirect(url_for("index"))
        return jsonify({"status": "error", "message": bot_error}), 400

    if bot_running:
        bot_error = "Bot sudah berjalan. Stop dulu sebelum start ulang."
        if not request.is_json:
            return redirect(url_for("index"))
        return jsonify({"status": "error", "message": bot_error}), 400

    _last_start_params = {"token_preview": token[:6] + "...", "reply": reply}
    bot_error = None
    bot_thread = threading.Thread(target=_run_bot, args=(token, reply), daemon=True)
    bot_thread.start()
    time.sleep(0.2)

    if not request.is_json:
        return redirect(url_for("index"))
    return jsonify({"status": "ok", "message": "Bot dimulai"})


@app.route("/stop", methods=["POST"])
def stop():
    global bot_running, discord_client, bot_error, responded_users

    if not bot_running:
        bot_error = "Bot tidak sedang berjalan."
        if not request.is_json:
            return redirect(url_for("index"))
        return jsonify({"status": "error", "message": bot_error}), 400

    try:
        client = discord_client
        if client:
            loop = getattr(client, "loop", None)
            try:
                coro = client.close()
                if loop:
                    asyncio.run_coroutine_threadsafe(coro, loop)
                else:
                    asyncio.get_event_loop().run_until_complete(coro)
            except Exception as e:
                print("[stop] close() failed:", e)
            try:
                if loop and loop.is_running():
                    loop.call_soon_threadsafe(loop.stop)
            except Exception as e:
                print("[stop] stop loop failed:", e)
    except Exception as e:
        print("[stop] general stop error:", e)

    # beri waktu agar thread berhenti
    time.sleep(0.5)
    # clear list responded users ketika stop (sesuai permintaan)
    responded_users.clear()

    if not request.is_json:
        return redirect(url_for("index"))
    return jsonify({"status": "ok", "message": "Stop diminta"})


@app.route("/status", methods=["GET"])
def status():
    """Endpoint JSON untuk polling status dari frontend jika perlu."""
    return jsonify({
        "running": bot_running,
        "error": bot_error,
        "responded_count": len(responded_users)
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)