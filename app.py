from flask import Flask, render_template, request
import threading
import discord
from discord.ext import commands

app = Flask(__name__)

# Variabel global
bot_thread = None
running = False
error = None
discord_import_error = False
bot_instance = None
responded_users = set()  # Menyimpan user yang sudah dibalas

# Fungsi untuk membuat bot
def create_bot(token, reply_message):
    intents = discord.Intents.default()
    intents.messages = True
    intents.dm_messages = True
    intents.message_content = True

    bot = commands.Bot(command_prefix="!", self_bot=True, intents=intents)

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")

    @bot.event
    async def on_message(message):
        if message.author.id == bot.user.id:
            return
        
        if isinstance(message.channel, discord.DMChannel):
            # Balas hanya sekali per user
            if message.author.id not in responded_users:
                try:
                    await message.channel.send(reply_message)
                    responded_users.add(message.author.id)
                    print(f"Balas ke: {message.author} ({message.author.id})")
                except Exception as e:
                    print(f"Error saat balas: {e}")

    bot.run(token)

# Halaman utama
@app.route("/", methods=["GET", "POST"])
def index():
    global bot_thread, running, error, discord_import_error, bot_instance

    if request.method == "POST":
        action = request.form.get("action")
        token = request.form.get("token")
        reply = request.form.get("reply")

        if action == "start" and not running:
            error = None
            try:
                bot_thread = threading.Thread(target=create_bot, args=(token, reply), daemon=True)
                bot_thread.start()
                running = True
            except ImportError:
                discord_import_error = True
                running = False
            except Exception as e:
                error = str(e)
                running = False

        elif action == "stop" and running:
            # Tidak ada cara resmi stop self-bot discord.py, biasanya restart server
            running = False

    return render_template("index.html", running=running, error=error, discord_import_error=discord_import_error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)