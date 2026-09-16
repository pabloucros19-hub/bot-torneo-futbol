from http.server import BaseHTTPRequestHandler
import json
import asyncio
from telegram import Update
from bot import get_application

# Inicializar la aplicación de Telegram
app = get_application()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            update = Update.de_json(data, app.bot)
            
            async def process():
                await app.initialize()
                await app.process_update(update)
                await app.shutdown()

            asyncio.run(process())
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot de Torneo en ejecucion (Vercel Webhook Active)')