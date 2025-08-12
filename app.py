import os
import threading
import random
import asyncio
import discord
from flask import Flask, render_template, request, jsonify

# Variabel global
bot_thread = None
discord_client = None
bot_running = False
bot_error = None
_last_start_params = None

# Simpan user_id yang sudah pernah dibalas
responded_users = set()

# Flask app
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', bot_running=bot_running, bot_error=bot_error)

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_thread, bot_running, bot_error, _last_start_params

    if bot_running:
        return jsonify({'status': 'error', 'message': 'Bot sudah berjalan'}), 400

    data = request.json
    token = data.get('token')
    reply_message = data.get('reply_message')

    if not token or not reply_message:
        return jsonify({'status': 'error', 'message': 'Token dan pesan wajib diisi'}), 400

    _last_start_params = (token, reply_message)

    bot_thread = threading.Thread(target=run_bot, args=(token, reply_message))
    bot_thread.start()

    return jsonify({'status': 'success', 'message': 'Bot dimulai'})


@app.route('/stop', methods=['POST'])
def stop_bot():
    global discord_client, bot_running, responded_users
    if discord_client:
        asyncio.run_coroutine_threadsafe(discord_client.close(), discord_client.loop)
    bot_running = False
    responded_users.clear()
    return jsonify({'status': 'success', 'message': 'Bot dihentikan'})


def run_bot(token, reply_message):
    global discord_client, bot_running, bot_error, responded_users
    bot_error = None
    responded_users.clear()

    intents = discord.Intents.default()
    intents.messages = True
    intents.dm_messages = True
    intents.guild_messages = True
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        global bot_running
        bot_running = True
        print(f"[bot] Logged in as {client.user}")

    @client.event
    async def on_message(message):
        global responded_users

        # Jangan balas pesan sendiri
        if message.author.id == client.user.id:
            return

        # Cek channel DM
        is_dm = False
        if isinstance(message.channel, discord.DMChannel):
            is_dm = True
        else:
            ch_type = getattr(message.channel, "type", None)
            if ch_type and str(ch_type).lower().startswith("private"):
                is_dm = True

        if is_dm:
            # Balas hanya jika belum pernah dibalas
            if message.author.id not in responded_users:
                try:
                    await message.channel.trigger_typing()
                except Exception:
                    pass
                await asyncio.sleep(random.uniform(2.0, 5.5))
                try:
                    await message.channel.send(reply_message)
                    responded_users.add(message.author.id)
                except Exception as e:
                    print("[bot] Gagal mengirim pesan:", e)

    try:
        discord_client = client
        client.run(token)
    except Exception as e:
        bot_error = str(e)
        bot_running = False
        print("[bot] Error:", e)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)