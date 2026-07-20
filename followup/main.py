"""
Orquestador del follow-up post-llamada.

Flujo:
  1. Lee de Attio las entradas en stage "Llamada realizada" con
     follow_up_status = "Pendiente".
  2. Arma el correo personalizado (gancho por industria + nota de la
     llamada + material marcado por el vendedor).
  3. Deja el correo como draft (por ahora: solo lo imprime / guarda en
     runs/ en modo dry-run, hasta conectar un proveedor de email real).
  4. Marca follow_up_status = "Draft generado" en Attio -- corridas
     repetidas no reprocesan el mismo lead.

Uso:
    python -m followup.main              # dry-run: imprime, no manda nada
    python -m followup.main --apply      # marca follow_up_status en Attio
"""
import argparse
import json
import os

from dotenv import load_dotenv

load_dotenv()

from followup import attio_client, templates  # noqa: E402

RUNS_DIR = "runs"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="marca follow_up_status en Attio (default: dry-run, no escribe nada)")
    args = parser.parse_args()

    def log(msg):
        print(msg)

    log(f"=== Follow-up post-llamada (apply={args.apply}) ===")

    pending = attio_client.fetch_pending_follow_ups()
    log(f"Leads pendientes de follow-up: {len(pending)}")

    drafts = []
    for i, lead in enumerate(pending):
        email = templates.build_follow_up_email(lead, subject_variant_index=i)
        drafts.append({
            "record_id": lead["record_id"],
            "entry_id": lead["entry_id"],
            "to": lead.get("email"),
            "cc": lead.get("contacto_secundario_email"),
            "subject": email["subject"],
            "body": email["body"],
        })
        log(f"\n--- Draft para {lead.get('full_name')} ({lead.get('email')}) ---")
        log(f"Asunto: {email['subject']}")
        log(email["body"])

        if args.apply:
            attio_client.mark_follow_up_status(lead["entry_id"], attio_client.FOLLOW_UP_DRAFT_GENERADO)
            log(f"[Attio] follow_up_status -> Draft generado (entry {lead['entry_id']})")

    os.makedirs(RUNS_DIR, exist_ok=True)
    out_path = os.path.join(RUNS_DIR, "follow_up_drafts.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=2)
    log(f"\n=== {len(drafts)} draft(s) guardados en {out_path} ===")


if __name__ == "__main__":
    main()
