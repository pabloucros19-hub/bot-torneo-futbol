import os
import telebot
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
  return "Bot de Torneo de Fútbol activo correctamente", 200


@app.route("/api/webhook", methods=["POST"])
def webhook():
  if request.headers.get("content-type") == "application/json":
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)

    # Procesamos la actualización en el bot
    bot.process_new_updates([update])

    return "", 200
  else:
    return "Forbidden", 403


# Manejador de ejemplo para que el bot responda cuando le escribas
@bot.message_handler(func=lambda message: True)
def echo_all(message):
  # Aquí puedes poner la lógica de tu torneo o un mensaje de confirmación
  bot.reply_to(message, "¡Mensaje recibido y procesado con éxito en Vercel! ⚽")
