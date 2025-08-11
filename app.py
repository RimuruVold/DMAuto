from flask import Flask, render_template, request, jsonify
import threading
import time
import os

app = Flask(__name__)

# Status bot
bot_status = {
    "active": False,
    "progress": "",
    "error": ""
}

# Simulasi fungsi bot
def bot_auto_reply(token, message):
    try:
        bot_status["active"] = True
        bot_status["progress"] = "Bot sedang berjalan..."
        bot_status["error"] = ""

        # Simulasi proses bot
        for i in range(5):
            bot_status["progress"] = f"Memproses pesan... {i+1}/5"
            time.sleep(1)

        bot_status["progress"] = "Pesan berhasil diproses!"
        bot_status["active"] = False
    except Exception as e:
        bot_status["error"] = f"Terjadi error: {str(e)}"
        bot_status["active"] = False


@app.route("/")
def index():
    return render_template("index.html", status=bot_status)


@app.route("/start", methods=["POST"])
def start_bot():
    token = request.form.get("token")
    message = request.form.get("message")
    # Jalankan bot atau proses sesuai kebutuhan
    return "Bot berhasil dijalankan!"

    if not token or not message:
        return jsonify({"error": "Token dan pesan wajib diisi!"}), 400

    threading.Thread(target=bot_auto_reply, args=(token, message)).start()
    return jsonify({"status": "Bot dimulai"})


@app.route("/status")
def get_status():
    return jsonify(bot_status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)