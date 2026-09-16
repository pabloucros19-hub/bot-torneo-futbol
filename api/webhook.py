from datetime import datetime
import os
import requests
import telebot
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

# URL del Apps Script que pegaste en Vercel
GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL")


@app.route("/", methods=["GET"])
def index():
  return "Bot de arbitraje con Google Sheets activo", 200


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


# Comando para registrar el partido desde Telegram
# Ejemplo: /arbitraje Argentina 80000 Usa 60000 130000 10000 70000
@bot.message_handler(commands=["arbitraje", "partido"])
def registrar_arbitraje(message):
  try:
    text_parts = message.text.split()
    if len(text_parts) < 8:
      bot.reply_to(
          message,
          "⚠️ Formato incorrecto. Usa:\n`/arbitraje [Local] [PagoLocal]"
          " [Visitante] [PagoVisita] [Efectivo] [Nequi] [Descuento]`",
      )
      return

    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    equipo_local = text_parts[1]
    pago_local = float(text_parts[2])
    equipo_vis = text_parts[3]
    pago_visita = float(text_parts[4])
    efectivo_total = float(text_parts[5])
    nequi_total = float(text_parts[6])
    descuento = float(text_parts[7])

    # Cálculos idénticos a los de tu Excel
    ingreso_total = efectivo_total + nequi_total
    caja_neta = ingreso_total - descuento

    # Datos que enviaremos al Script de Google
    payload = {
        "fecha": fecha_hoy,
        "equipo_local": equipo_local,
        "pago_local": pago_local,
        "equipo_vis": equipo_vis,
        "pago_visita": pago_visita,
        "efectivo_total": efectivo_total,
        "nequi_total": nequi_total,
        "ingreso_total": ingreso_total,
        "descuento": descuento,
        "caja_neta": caja_neta,
    }

    if not GOOGLE_SCRIPT_URL:
      bot.reply_to(
          message, "❌ Error: Falta configurar GOOGLE_SCRIPT_URL en Vercel."
      )
      return

    # Enviamos los datos mediante una petición HTTP POST al Script de Google
    response = requests.post(GOOGLE_SCRIPT_URL, json=payload)

    if response.status_code == 200:
      bot.reply_to(
          message,
          f"✅ ¡Registrado en Google Sheets al instante! 📊\n"
          f"⚽ {equipo_local} vs {equipo_vis}\n"
          f"💵 Efectivo: ${efectivo_total:,.0f} | Nequi: ${nequi_total:,.0f}\n"
          f"💰 Caja Neta: ${caja_neta:,.0f}",
      )
    else:
      bot.reply_to(message, "❌ Error al comunicarse con la hoja de cálculo.")

  except Exception as e:
    bot.reply_to(message, f"❌ Error procesando el registro: {e}")


@bot.message_handler(func=lambda message: True)
def default_response(message):
  bot.reply_to(
      message,
      "Bot conectado a Google Sheets. Usa /arbitraje para registrar los datos.",
  )
