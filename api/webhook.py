# -------------------------------------------------------------
    # CASO 2: REGISTRO DE PARTIDO / ARBITRAJE (Con descuento fijo de 70000)
    # -------------------------------------------------------------
    if "contra" in texto_limpio.lower() or "vs" in texto_limpio.lower():
      partes = re.split(r"\s+contra\s+|\s+vs\s+", texto_limpio, flags=re.IGNORECASE)
      if len(partes) < 2:
        bot.reply_to(message, "⚠️ Formato incorrecto. Ejemplo: `15/09/2026: Francia 30000 nequi 30000 efectivo contra Brasil 20000 nequi`")
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
      
      # Descuento fijo por partido (Pago a la mesa)
      descuento = 70000 
      
      # Caja Neta = Ingreso Total - Descuento Fijo
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
            f"🏷️ Descuento Mesa: ${descuento:,.0f}\n"
            f"💰 Caja Neta: ${caja_neta:,.0f}",
        )
      else:
        bot.reply_to(message, "❌ Error al guardar el arbitraje.")
      return
