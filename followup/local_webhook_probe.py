"""
Servidor local de diagnóstico, NO para producción: recibe el webhook de
Trellus (vía túnel de ngrok) e imprime el payload completo, para
confirmar si contact_id coincide con record_id de Attio antes de
escribir la lógica real de sincronización.

Uso:
    python -m followup.local_webhook_probe
    (en otra terminal) ngrok http 8765
    -> pegar la URL https de ngrok + /webhook en Trellus, con el header
       X-Webhook-Secret configurado, y usar "Test Webhook" ahí.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv

load_dotenv()

PORT = 8765


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return

        secret = self.headers.get("X-Webhook-Secret")
        expected = os.environ.get("TRELLUS_WEBHOOK_SECRET")
        if not secret or secret != expected:
            print(f"[rechazado] secreto ausente o incorrecto: {secret!r}")
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error":"unauthorized"}')
            return

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length)
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            payload = {"_raw": raw_body.decode("utf-8", errors="replace")}

        print("\n=== Payload recibido de Trellus ===")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"\ncontact_id -> {payload.get('contact_id')!r}")
        print(f"custom_id  -> {payload.get('custom_id')!r}")
        print(f"summary    -> {payload.get('summary')!r}")
        print("====================================\n")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"received": true}')

    def log_message(self, format, *args):
        pass  # silenciar el log default de http.server, ya imprimimos lo útil arriba


if __name__ == "__main__":
    if not os.environ.get("TRELLUS_WEBHOOK_SECRET"):
        raise SystemExit("Falta TRELLUS_WEBHOOK_SECRET en .env")
    print(f"Escuchando en http://localhost:{PORT}/webhook (Ctrl+C para parar)")
    HTTPServer(("localhost", PORT), Handler).serve_forever()
