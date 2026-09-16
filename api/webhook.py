import os
import telebot
from flask import Flask, request

# Recuperamos el token de las variables de entorno de Vercel que acabamos de configurar
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
    bot.process_new_updates([update])
    return "", 200
  else:
    return "Forbidden", 403
