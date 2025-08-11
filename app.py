import threading
import time
from flask import Flask, render_template, request, redirect, url_for
import discord
from discord.ext import commands

app = Flask(__name__)

bot_thread = None
bot_running = False
bot_error = None
discord_bot = None


def run_bot(token, reply_message):
    global bot_running, bot_error, discord_bot
    bot_running = True
    bot_error = None

    try:
        discord_bot = commands.Bot(command_prefix="!", self_bot=True)

        @discord_bot.event
        async def on_ready():
            print(f"Logged in as {discord_bot.user}")

        @discord_bot.event
        async def on_message(message):
            if message.author.id == discord_bot.user.id:
                return
            if isinstance(message.channel, discord.DMChannel):
                await message.channel.send(reply_message)

        discord_bot.run(token)
    except Exception as e:
        bot_error = str(e)
        bot_running = False


@app.route("/", methods=["GET", "POST"])
def index():
    global bot_thread, bot_running, bot_error

    if request.method == "POST":
        if "start" in request.form:
            token = request.form.get("token")
            reply_message = request.form.get("reply")
            if not bot_running:
                bot_thread = threading.Thread(target=run_bot, args=(token, reply_message))
                bot_thread.start()
        elif "stop" in request.form:
            if bot_running and discord_bot:
                bot_running = False
                try:
                    discord_bot.loop.stop()
                except:
                    pass
        return redirect(url_for("index"))

    return render_template("index.html", running=bot_running, error=bot_error)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)