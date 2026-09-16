from datetime import datetime
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
  """Ejecuta consultas en Turso mediante la API REST"""
  if not TURSO_URL or not TURSO_TOKEN:
    print("Faltan credenciales de Turso")
    return None

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
  return "Bot de arbitraje activo en la nube", 200


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


# Comando exacto para registrar el partido/arbitraje tal como lo haces localmente
# Ejemplo de mensaje esperado de tus compañeros:
# /arbitraje Argentina 80000 60000 Usa 60000 60000 70000
# (O el formato exacto que ya maneje tu script local)
@bot.message_handler(commands=["arbitraje", "partido"])
def registrar_arbitraje(message):
  try:
    # Separamos los argumentos que envían en el mensaje de Telegram
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

    # Aplicamos exactamente la misma lógica matemática de tu Excel
    ingreso_total = efectivo_total + nequi_total
    caja_neta = ingreso_total - descuento

    # Guardamos en la base de datos de Turso
    query = """
            INSERT INTO partidos_arbitraje 
            (fecha, equipo_local, pago_local, equipo_vis, pago_visita, efectivo_total, nequi_total, ingreso_total, descuento, caja_neta) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
    params = [
        fecha_hoy,
        equipo_local,
        pago_local,
        equipo_vis,
        pago_visita,
        efectivo_total,
        nequi_total,
        ingreso_total,
        descuento,
        caja_neta,
    ]

    resultado = ejecutar_query_turso(query, params)

    if resultado:
      bot.reply_to(
          message,
          f"✅ Partido registrado con éxito en la nube:\n"
          f"⚽ {equipo_local} ({pago_local}) vs {equipo_vis} ({pago_visita})\n"
          f"💵 Efectivo: ${efectivo_total:,.0f} | Nequi: ${nequi_total:,.0f}\n"
          f"📊 Ingreso Total: ${ingreso_total:,.0f}\n"
          f"📉 Descuento: ${descuento:,.0f}\n"
          f"💰 Caja Neta: ${caja_neta:,.0f}",
      )
    else:
      bot.reply_to(
          message,
          "❌ Hubo un error al guardar los datos en la base de datos de Turso.",
      )

  except Exception as e:
    bot.reply_to(message, f"❌ Error procesando el registro: {e}")


@bot.message_handler(func=lambda message: True)
def default_response(message):
  bot.reply_to(
      message,
      "Bot de arbitraje en línea activo. Usa /arbitraje para registrar los"
      " pagos.",
  )
