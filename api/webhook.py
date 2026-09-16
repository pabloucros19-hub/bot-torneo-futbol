from datetime import datetime
import os
import re
import requests
import telebot
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL")


@app.route("/", methods=["GET"])
def index():
  return "Bot de arbitraje activo", 200


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


# Procesamiento automático de mensajes naturales (Ej: 15/09/26: Francia 60000 nequi contra Brasil 60000 nequi)
@bot.message_handler(func=lambda message: True)
def procesar_mensaje_natural(message):
  texto = message.text.strip()

  # Si el mensaje no parece un registro de partido, lo ignoramos o respondemos guía
  if not re.search(r"\d{2}/\d{2}/\d{2}", texto) and "contra" not in texto.lower():
    return

  try:
    # Ejemplo de formato esperado: 15/09/26: Francia 60000 nequi contra Brasil 60000 nequi
    # Limpiamos y separamos usando regex o splits precisos
    # Extraer fecha
    match_fecha = re.search(r"(\d{2}/\d{2}/\d{2})", texto)
    fecha = match_fecha.group(1) if match_fecha else datetime.now().strftime("%d/%m/%y")

    # Limpiamos la fecha del texto para procesar los equipos y pagos
    texto_limpio = re.sub(r"^\d{2}/\d{2}/\d{2}:?", "", texto).strip()

    # Dividir por "contra" o "vs"
    partes = re.split(r"\s+contra\s+|\s+vs\s+", texto_limpio, flags=re.IGNORECASE)
    if len(partes) < 2:
      bot.reply_to(message, "⚠️ Formato no reconocido. Usa: `DD/MM/YY: Local [Pago] [Método] contra Visita [Pago] [Método]`")
      return

    # Lado Local
    local_raw = partes[0].strip()
    # Separar equipo local y su pago/método (ej: Francia 60000 nequi)
    match_local = re.search(r"^(.*?)\s+(\d+)\s*(efectivo|nequi)?$", local_raw, re.IGNORECASE)
    
    if match_local:
      equipo_local = match_local.group(1).strip()
      pago_local = float(match_local.group(2))
      metodo_local = (match_local.group(3) or "efectivo").lower()
    else:
      # Si no especifica monto explícito en una parte, ajustamos
      bot.reply_to(message, "⚠️ Revisa el monto o método del equipo local.")
      return

    # Lado Visitante
    visita_raw = partes[1].strip()
    match_visita = re.search(r"^(.*?)\s+(\d+)\s*(efectivo|nequi)?$", visita_raw, re.IGNORECASE)
    
    if match_visita:
      equipo_vis = match_visita.group(1).strip()
      pago_visita = float(match_visita.group(2))
      metodo_visita = (match_visita.group(3) or "efectivo").lower()
    else:
      bot.reply_to(message, "⚠️ Revisa el monto o método del equipo visitante.")
      return

    # Cálculos automáticos de Totales
    efectivo_total = 0
    nequi_total = 0

    if metodo_local == "efectivo":
      efectivo_total += pago_local
    else:
      nequi_total += pago_local

    if metodo_visita == "efectivo":
      efectivo_total += pago_visita
    else:
      nequi_total += pago_visita

    ingreso_total = efectivo_total + nequi_total
    descuento = 0  # Se puede ajustar si viene en el texto
    caja_neta = ingreso_total - descuento

    # Estructura de la fila para Google Sheets
    payload = {
        "fecha": fecha,
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
      bot.reply_to(message, "❌ Error: Falta configurar GOOGLE_SCRIPT_URL en Vercel.")
      return

    response = requests.post(GOOGLE_SCRIPT_URL, json=payload)

    if response.status_code == 200:
      bot.reply_to(
          message,
          f"✅ Registrado con éxito 📊\n"
          f"📅 {fecha} | ⚽ {equipo_local} vs {equipo_vis}\n"
          f"💵 Efectivo: ${efectivo_total:,.0f} | Nequi: ${nequi_total:,.0f}\n"
          f"💰 Caja Neta: ${caja_neta:,.0f}",
      )
    else:
      bot.reply_to(message, "❌ Error al comunicarse con la hoja de cálculo.")

  except Exception as e:
    bot.reply_to(message, f"❌ Error procesando el mensaje: {e}")
