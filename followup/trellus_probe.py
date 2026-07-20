"""
Script de diagnóstico, no de producción: consulta la API de Trellus
para ver qué trae el payload de llamadas recientes (¿incluye resumen
de IA en texto? ¿qué campos expone?), así se puede decidir si conviene
un webhook Trellus -> Attio.

Lee TRELLUS_API_KEY de variables de entorno -- nunca hardcodear la key
acá ni pasarla por línea de comandos (quedaría en el historial de shell).

Uso:
    python -m followup.trellus_probe
"""
import os
import json

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.bytrellus.com/v1"


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['TRELLUS_API_KEY']}",
        "Content-Type": "application/json",
    }


def probe_calls(limit=5):
    """Intenta listar llamadas recientes. El endpoint exacto no está
    confirmado públicamente (docs bloqueadas para fetch automático), así
    que se prueban las rutas más probables según convención REST."""
    candidate_paths = ["/calls", "/call-logs", "/calls/recent"]
    for path in candidate_paths:
        try:
            r = requests.get(f"{BASE_URL}{path}", headers=_headers(),
                              params={"limit": limit}, timeout=30)
        except requests.RequestException as e:
            print(f"[{path}] error de red: {e}")
            continue
        print(f"[{path}] status={r.status_code}")
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:3000])
            return
        else:
            print(f"  body: {r.text[:300]}")
    print("\nNinguna ruta candidata funcionó. Revisar la documentación real "
          "en support.bytrellus.com/hc/en-us/articles/12325049210267 (API "
          "Introduction) para el path correcto de listado de llamadas.")


if __name__ == "__main__":
    probe_calls()
