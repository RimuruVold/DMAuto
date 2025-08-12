from flask import Flask, render_template, request
import threading
import discord

app = Flask(__name__)
running = False
client = None
bot_thread = None
error = None

def run_bot(token, reply_text):
    global client, error
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Bot logged in as {client.user}")

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return
        await message.channel.send(reply_text)

    try:
        client.run(token)
    except Exception as e:
        error = str(e)
        print("Bot error:", e)

@app.route("/", methods=["GET", "POST"])
def index():
    global running, bot_thread, client, error

    if request.method == "POST":
        action = request.form.get("action")
        if action == "start" and not running:
            token = request.form.get("token")
            reply_text = request.form.get("reply")
            bot_thread = threading.Thread(target=run_bot, args=(token, reply_text), daemon=True)
            bot_thread.start()
            running = True
        elif action == "stop" and running:
            if client:
                try:
                    import asyncio
                    asyncio.run_coroutine_threadsafe(client.close(), client.loop)
                except Exception as e:
                    error = str(e)
            running = False

    return render_template("index.html", running=running, error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)