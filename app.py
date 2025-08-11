import threading
import time
import random
from flask import Flask, render_template, request, redirect, url_for
import sys

# Attempt import discord (discord.py-self or compatible). If missing, error shown on web.
try:
    import discord
    from discord.ext import commands
except Exception as e:
    discord = None
    import traceback
    tb = traceback.format_exc()
    # We'll set an error message to show on the UI later
    DISCORD_IMPORT_ERROR = tb
else:
    DISCORD_IMPORT_ERROR = None

app = Flask(__name__, static_folder="static", template_folder="templates")

# Globals to share state with web UI
bot_thread = None
bot_running = False
bot_error = None
discord_client = None
_stop_event = threading.Event()


def _make_client(reply_message):
    """
    Create a discord client / bot with minimal handlers.
    Note: relies on discord library available (discord.py-self or similar).
    """
    intents = None
    client = None
    try:
        # Try create commands.Bot if available
        # For very old versions this may differ; this is a best-effort.
        intents = discord.Intents.default() if hasattr(discord, "Intents") else None
    except Exception:
        intents = None

    try:
        if hasattr(commands, "Bot"):
            if intents:
                client = commands.Bot(command_prefix="!", self_bot=True, intents=intents)
            else:
                client = commands.Bot(command_prefix="!", self_bot=True)
        else:
            # fallback minimal client
            client = discord.Client()
    except Exception:
        # fallback plain client
        client = discord.Client()

    @client.event
    async def on_ready():
        print(f"[bot] Logged in as {getattr(client, 'user', 'UNKNOWN')}")

    @client.event
    async def on_message(message):
        # ignore our own messages
        try:
            if message.author.id == client.user.id:
                return
        except Exception:
            pass

        # Only reply to DMs
        try:
            if isinstance(message.channel, discord.DMChannel):
                # typing indicator + random delay to look less instant
                try:
                    await message.channel.trigger_typing()
                except Exception:
                    pass
                # random human-like delay
                await discord.utils.sleep_until(discord.utils.snowflake_time(message.id)) if False else None
                delay = random.uniform(2.0, 6.5)
                await discord.asyncio.sleep(delay) if hasattr(discord, 'asyncio') else discord.py_sleep(delay, client)
                try:
                    await message.channel.send(reply_message)
                except Exception as e:
                    print("[bot] Failed to send reply:", e)
        except Exception as e:
            print("[bot] on_message handler error:", e)

    return client


def discord.py_sleep(seconds, client):
    # fallback if library integration not available; try asyncio
    import asyncio
    return asyncio.sleep(seconds)


def run_bot(token, reply_message):
    """
    Runs the discord client in this thread. Stores errors into bot_error global.
    """
    global bot_running, bot_error, discord_client, _stop_event
    bot_error = None
    _stop_event.clear()
    bot_running = True
    discord_client = None

    if DISCORD_IMPORT_ERROR:
        bot_error = "discord library not available. Import error:\n" + DISCORD_IMPORT_ERROR
        bot_running = False
        return

    try:
        client = _make_client(reply_message)
        discord_client = client
        # This call blocks until the client finishes / raises
        # Use client.run(token) which handles event loop internally
        client.run(token)
    except Exception as e:
        bot_error = f"{type(e).__name__}: {e}"
        print("[run_bot] exception:", bot_error)
    finally:
        bot_running = False
        discord_client = None
        _stop_event.set()


@app.route("/", methods=["GET", "POST"])
def index():
    global bot_thread, bot_running, bot_error, discord_client

    if request.method == "POST":
        action = request.form.get("action")
        token = request.form.get("token", "").strip()
        reply = request.form.get("reply", "").strip()

        if action == "start":
            if bot_running:
                # already running
                pass
            else:
                # clear prior error
                bot_error = None
                # start thread
                bot_thread = threading.Thread(target=run_bot, args=(token, reply), daemon=True)
                bot_thread.start()
                time.sleep(0.2)
        elif action == "stop":
            if bot_running and discord_client:
                try:
                    # best-effort: attempt to stop loop / logout
                    try:
                        # If client has loop, ask it to stop
                        loop = getattr(discord_client, "loop", None)
                        if loop and loop.is_running():
                            loop.call_soon_threadsafe(loop.stop)
                    except Exception:
                        pass
                    try:
                        # try logout
                        coro = discord_client.close()
                        import asyncio
                        asyncio.run_coroutine_threadsafe(coro, getattr(discord_client, "loop", None))
                    except Exception:
                        pass
                except Exception as e:
                    print("Stop attempt failed:", e)
            else:
                # nothing to stop
                pass

        return redirect(url_for("index"))

    # GET
    return render_template("index.html",
                           running=bot_running,
                           error=bot_error,
                           discord_import_error=DISCORD_IMPORT_ERROR)


if __name__ == "__main__":
    # Replit typically expects port from env; default to 3000
    import os
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=False)