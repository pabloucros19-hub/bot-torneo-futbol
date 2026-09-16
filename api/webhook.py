import os
import requests
import telebot
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

# Credenciales de Turso (Configuradas en Vercel)
TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


def ejecutar_query_turso(sql_query, params=None):
  """Función auxiliar para enviar consultas a Turso desde Vercel sin librerías pesadas"""
  if not TURSO_URL or not TURSO_TOKEN:
    return None

  # Turso acepta consultas HTTP SQL fácilmente mediante su API REST /v2/pipeline
  url = f"{TURSO_URL.replace('libsql://', 'https://')}/v2/pipeline"
  headers = {
      "Authorization": f"Bearer {TURSO_TOKEN}",
      "Content-Type": "application/json",
  }

  payload = {
      "requests": [{"type": "execute", "stmt": {"sql": sql_query, "args": params or []}}]
  }

  try:
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
  except Exception as e:
    print(f"Error conectando a Turso: {e}")
    return None


@app.route("/", methods=["GET"])
def index():
  return "Bot de Torneo de Fútbol activo correctamente en la nube", 200


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


# Manejador de ejemplo para cuando tus compañeros escriban en Telegram
@bot.message_handler(commands=["gol", "resultado"])
def registrar_accion(message):
  # Aquí puedes capturar lo que escriban tus amigos (ej: /gol EquipoA EquipoB)
  texto_usuario = message.text

  # Ejemplo de guardado en Turso (puedes crear tu tabla previamente en Turso)
  # ejecutar_query_turso("INSERT INTO partidos (mensaje, usuario) VALUES (?, ?)", [texto_usuario, message.from_user.username])

  bot.reply_to(
      message,
      f"¡Dato registrado en la nube con éxito! ⚽ Procesé: {texto_usuario}",
  )


@bot.message_handler(func=lambda message: True)
def echo_all(message):
  bot.reply_to(
      message,
      "¡Hola! El bot del torneo está activo 24/7 en la nube. Usa los comandos"
      " habilitados para actualizar datos.",
  )
