import os
import telebot
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
  return "Bot de Torneo de Fútbol activo correctamente", 200


@app.route("/api/webhook", methods=["POST"])
def webhook():
  if request.headers.get("content-type") == "application/json":
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)

    try:
      bot.process_new_updates([update])
    except Exception as e:
      print(f"Error procesando update: {e}")

    return "OK", 200
  else:
    return "Forbidden", 403


@bot.message_handler(func=lambda message: True)
def echo_all(message):
  bot.reply_to(message, "¡Mensaje recibido y procesado con éxito en Vercel! ⚽")
