from flask import Flask, render_template, request
import threading
import os

app = Flask(__name__)

running = False
bot_thread = None
error_message = None

# Simpan daftar ID user yang sudah pernah dibalas
already_replied_users = set()

try:
    import discord
    from discord.ext import commands
    discord_import_error = False
except ImportError:
    discord_import_error = True

bot_instance = None

def run_bot(token, reply_message):
    global running, error_message, bot_instance, already_replied_users
    try:
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True

        bot = commands.Bot(command_prefix="!", self_bot=True, intents=intents)
        bot_instance = bot

        # Kosongkan daftar user setiap kali bot dijalankan ulang
        already_replied_users.clear()

        @bot.event
        async def on_ready():
            print(f"Bot logged in as {bot.user}")

        @bot.event
        async def on_message(message):
            global already_replied_users
            # Jangan balas diri sendiri
            if message.author.id == bot.user.id:
                return

            # Jika user belum pernah dibalas
            if message.author.id not in already_replied_users:
                try:
                    await message.channel.send(reply_message)
                    already_replied_users.add(message.author.id)
                    print(f"Replied to {message.author} ({message.author.id})")
                except Exception as e:
                    print(f"Error replying to {message.author}: {e}")

        running = True
        bot.run(token)
    except Exception as e:
        error_message = str(e)
        running = False


@app.route("/", methods=["GET", "POST"])
def index():
    global running, bot_thread, error_message, bot_instance

    if request.method == "POST":
        action = request.form.get("action")
        token = request.form.get("token")
        reply_message = request.form.get("reply")

        if action == "start" and not running:
            if discord_import_error:
                error_message = "Discord library not installed."
            else:
                error_message = None
                bot_thread = threading.Thread(target=run_bot, args=(token, reply_message))
                bot_thread.start()

        elif action == "stop" and running:
            try:
                if bot_instance:
                    bot_instance.loop.call_soon_threadsafe(bot_instance.loop.stop)
                running = False
            except Exception as e:
                error_message = str(e)

    return render_template("index.html", running=running, error=error_message, discord_import_error=discord_import_error)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)