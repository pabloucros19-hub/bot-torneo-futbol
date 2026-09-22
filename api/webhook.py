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
      procesar_telegram_update(update)
    except Exception as e:
      print(f"Error procesando update: {e}")
      
    # IMPORTANTE: Respondemos "OK" a Telegram inmediatamente para liberar la conexión
    return "OK", 200
  else:
    return "Forbidden", 403


def enviar_mensaje_rapido(chat_id, texto):
  """Envía el mensaje a Telegram con un timeout corto para que no bloquee al bot"""
  try:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=2) # Timeout de solo 2 segundos
  except Exception as e:
    print(f"Error enviando mensaje rápido: {e}")


def procesar_telegram_update(update):
  if not update.message or not update.message.text:
    return

  message = update.message
  texto = message.text.strip()
  chat_id = message.chat.id

  if not re.search(r"\d{2}/\d{2}/\d{2,4}", texto):
    return

  match_fecha = re.search(r"(\d{2}/\d{2}/\d{2,4})", texto)
  fecha = match_fecha.group(1) if match_fecha else datetime.now().strftime("%d/%m/%y")
  texto_limpio = re.sub(r"^\d{2}/\d{2}/\d{2,4}:?", "", texto).strip()

  # -------------------------------------------------------------
  # CASO 1: REGISTRO DE TARJETAS
  # ---------------------------------------------
  if "tarjeta" in texto_limpio.lower() or "amarilla" in texto_limpio.lower() or "roja" in texto_limpio.lower():
    lineas = texto.split("\n")
    tarjetas_registradas = 0

    for linea in lineas:
      linea = linea.strip()
      if not linea:
        continue
      
      match_f_linea = re.search(r"(\d{2}/\d{2}/\d{2,4})", linea)
      fecha_linea = match_f_linea.group(1) if match_f_linea else fecha
      
      lin_limpia = re.sub(r"^\d{2}/\d{2}/\d{2,4}:?", "", linea).strip()

      if "amarilla" not in lin_limpia.lower() and "roja" not in lin_limpia.lower() and "tarjeta" not in lin_limpia.lower():
        continue

      amarilla = 1 if "amarilla" in lin_limpia.lower() else 0
      roja = 1 if "roja" in lin_limpia.lower() else 0

      if roja > 0 and amarilla == 0:
        total_multa = 10000
      else:
        total_multa = 5000

      t_limpia = re.sub(r"amarilla|roja|tarjeta|a\s+|de\s+", "", lin_limpia, flags=re.IGNORECASE)
      palabras = [p for p in t_limpia.split() if not re.search(r"\d{2}/\d{2}/\d{2,4}", p)]

      equipo = "Desconocido"
      jugador = "Desconocido"
      
      if len(palabras) >= 2:
        equipo = palabras[-1].capitalize()
        jugador = " ".join(palabras[:-1]).title()
      elif len(palabras) == 1:
        jugador = palabras[0].title()

      payload = {
          "tipo": "tarjeta",
          "fecha": fecha_linea,
          "equipo": equipo,
          "jugador": jugador,
          "amarilla": amarilla,
          "roja": roja,
          "total_multa": total_multa
      }

      try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=4)
        if response.status_code == 200:
          tarjetas_registradas += 1
      except Exception:
        pass

    if tarjetas_registradas > 0:
      enviar_mensaje_rapido(chat_id, f"🟨🟥 ¡Se registraron {tarjetas_registradas} tarjeta(s) en la pestaña Tarjetas! 📊")
    else:
      enviar_mensaje_rapido(chat_id, "❌ No se pudo registrar ninguna tarjeta. Revisa el formato.")
    return

  # -------------------------------------------------------------
  # CASO 2: REGISTRO DE PARTIDO / ARBITRAJE
  # -------------------------------------------------------------
  if "contra" in texto_limpio.lower() or "vs" in texto_limpio.lower():
    partes = re.split(r"\s+contra\s+|\s+vs\s+", texto_limpio, flags=re.IGNORECASE)
    if len(partes) < 2:
      enviar_mensaje_rapido(chat_id, "⚠️ Formato incorrecto. Ejemplo: `15/09/2026: Francia 30000 nequi 30000 efectivo contra Brasil 20000 nequi`")
      return

    def extraer_valores_equipo(texto_equipo):
      match_nombre = re.search(r"^(.*?)\s+\d+", texto_equipo)
      nombre = match_nombre.group(1).strip() if match_nombre else texto_equipo.strip()
      patrones = re.findall(r"(\d+)\s*(efectivo|nequi)?", texto_equipo, flags=re.IGNORECASE)
      
      efectivo_eq = 0
      nequi_eq = 0
      pago_total_eq = 0
      
      for monto_str, metodo in patrones:
        monto = float(monto_str)
        pago_total_eq += monto
        met = metodo.lower() if metodo else "efectivo"
        if met == "nequi":
          nequi_eq += monto
        else:
          efectivo_eq += monto
          
      return nombre, pago_total_eq, efectivo_eq, nequi_eq

    equipo_local, pago_local, ef_local, nq_local = extraer_valores_equipo(partes[0].strip())
    equipo_vis, pago_visita, ef_vis, nq_vis = extraer_valores_equipo(partes[1].strip())

    efectivo_total = ef_local + ef_vis
    nequi_total = nq_local + nq_vis
    ingreso_total = efectivo_total + nequi_total
    descuento = 70000 
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

    try:
      response = requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=4)
      if response.status_code == 200:
        texto_resp = (
            f"✅ ¡Arbitraje registrado en pestaña Arbitraje! 📊\n"
            f"📅 {fecha} | ⚽ {equipo_local} vs {equipo_vis}\n"
            f"💵 Efectivo: ${efectivo_total:,.0f} \vert{} 📱 Nequi: ${nequi_total:,.0f}\n"
            f"🏷️ Descuento Mesa: ${descuento:,.0f}\n"
            f"💰 Caja Neta: ${caja_neta:,.0f}"
        )
        enviar_mensaje_rapido(chat_id, texto_resp)
      else:
        enviar_mensaje_rapido(chat_id, "❌ Error al guardar el arbitraje.")
    except Exception as e:
      # Registramos en los logs de Vercel pero evitamos el falso positivo molesto al usuario
      print(f"Aviso menor de red o respuesta en arbitraje: {e}")
    return
