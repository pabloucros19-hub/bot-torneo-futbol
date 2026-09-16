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
  return "Bot de arbitraje y tarjetas activo.", 200


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
def procesar_mensaje_natural(message):
  texto = message.text.strip()

  # Ignorar mensajes que no tengan formato de registro
  if not re.search(r"\d{2}/\d{2}/\d{2}", texto):
    return

  try:
    # Extraer fecha
    match_fecha = re.search(r"(\d{2}/\d{2}/\d{2})", texto)
    fecha = match_fecha.group(1) if match_fecha else datetime.now().strftime("%d/%m/%y")
    texto_limpio = re.sub(r"^\d{2}/\d{2}/\d{2}:?", "", texto).strip()

    # -------------------------------------------------------------
    # CASO 1: REGISTRO DE TARJETAS (Ej: "Francia Jhonatan amarilla 1 5000" o similar)
    # -------------------------------------------------------------
    if "tarjeta" in texto_limpio.lower() or "amarilla" in texto_limpio.lower() or "roja" in texto_limpio.lower():
      # Limpiar palabra tarjeta si la trae
      limpio_t = re.sub(r"tarjeta", "", texto_limpio, flags=re.IGNORECASE).strip()
      partes = limpio_t.split()
      
      if len(partes) < 3:
        bot.reply_to(message, "⚠️ Formato de tarjeta incompleto. Ejemplo: `15/09/26 Francia Jhonatan amarilla 1 5000`")
        return

      equipo = partes[0]
      jugador = partes[1]
      
      # Buscar tipo de tarjeta y cantidad/multa
      amarilla = 1 if "amarilla" in texto_limpio.lower() else 0
      roja = 1 if "roja" in texto_limpio.lower() else 0
      
      # Extraer valor numérico de multa si viene al final
      numeros = [float(p) for p in partes if p.isdigit()]
      total_multa = numeros[-1] if numeros else 5000 # Valor por defecto o el que escribas

      payload = {
          "tipo": "tarjeta",
          "fecha": fecha,
          "equipo": equipo,
          "jugador": jugador,
          "amarilla": amarilla,
          "roja": roja,
          "total_multa": total_multa
      }

      response = requests.post(GOOGLE_SCRIPT_URL, json=payload)
      if response.status_code == 200:
        bot.reply_to(message, f"🟨🟥 ¡Tarjeta registrada en Google Sheets!\n📅 {fecha} | ⚽ {equipo} - 👤 {jugador}\n💵 Multa: ${total_multa:,.0f}")
      else:
        bot.reply_to(message, "❌ Error al guardar la tarjeta en la hoja.")
      return

    # -------------------------------------------------------------
    # CASO 2: REGISTRO DE PARTIDO / ARBITRAJE (Tu formato habitual)
    # -------------------------------------------------------------
    if "contra" in texto_limpio.lower() or "vs" in texto_limpio.lower():
      partes = re.split(r"\s+contra\s+|\s+vs\s+", texto_limpio, flags=re.IGNORECASE)
      if len(partes) < 2:
        bot.reply_to(message, "⚠️ Formato de partido incorrecto. Usa: `15/09/26: Francia 60000 nequi contra Brasil 60000 nequi`")
        return

      # Local
      local_raw = partes[0].strip()
      match_local = re.search(r"^(.*?)\s+(\d+)", local_raw, re.IGNORECASE)
      if match_local:
        equipo_local = match_local.group(1).strip()
        pago_local = float(match_local.group(2))
        metodo_local = "nequi" if "nequi" in local_raw.lower() else "efectivo"
      else:
        bot.reply_to(message, f"⚠️ Revisa el equipo local: '{local_raw}'")
        return

      # Visitante
      visita_raw = partes[1].strip()
      match_visita = re.search(r"^(.*?)\s+(\d+)", visita_raw, re.IGNORECASE)
      if match_visita:
        equipo_vis = match_visita.group(1).strip()
        pago_visita = float(match_visita.group(2))
        metodo_visita = "nequi" if "nequi" in visita_raw.lower() else "efectivo"
      else:
        bot.reply_to(message, f"⚠️ Revisa el equipo visitante: '{visita_raw}'")
        return

      # Cálculos
      efectivo_total = (pago_local if metodo_local == "efectivo" else 0) + (pago_visita if metodo_visita == "nequi" == False and metodo_visita == "efectivo" else 0) # Simplificado abajo:
      
      efectivo_total = 0
      nequi_total = 0
      if metodo_local == "nequi": nequi_total += pago_local
      else: efectivo_total += pago_local
      
      if metodo_visita == "nequi": nequi_total += pago_visita
      else: efectivo_total += pago_visita

      ingreso_total = efectivo_total + nequi_total
      descuento = 0
      caja_neta = ingreso_total - descuento

      payload = {
          "tipo": "arbitraje",
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

      response = requests.post(GOOGLE_SCRIPT_URL, json=payload)
      if response.status_code == 200:
        bot.reply_to(
            message,
            f"✅ ¡Arbitraje registrado en Google Sheet! 📊\n"
            f"📅 {fecha} | ⚽ {equipo_local} vs {equipo_vis}\n"
            f"💵 Efectivo: ${efectivo_total:,.0f} | 📱 Nequi: ${nequi_total:,.0f}\n"
            f"💰 Caja Neta: ${caja_neta:,.0f}",
        )
      else:
        bot.reply_to(message, "❌ Error al guardar el arbitraje.")

  except Exception as e:
    bot.reply_to(message, f"❌ Error procesando el mensaje: {e}")
