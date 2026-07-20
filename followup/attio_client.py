"""
Cliente Attio para el módulo de follow-up post-llamada. Separado de
leadgen/attio.py a propósito: ese módulo sube leads nuevos al pipeline
de generación; este lee/actualiza leads que YA están en la lista y
tuvieron una llamada, para el envío de follow-up.

Los nombres de atributo (`ATTR_*`) son placeholders basados en lo
acordado; ajustar aquí si Attio normaliza los slugs distinto al
crear los campos en la lista.
"""
import os
import requests

BASE_URL = "https://api.attio.com/v2"
COBOL_LATAM_LIST_ID = "35c7dfa0-0f6f-41a2-a505-94e50535600d"

STAGE_LLAMADA_REALIZADA = "Llamada realizada"

FOLLOW_UP_PENDIENTE = "Pendiente"
FOLLOW_UP_DRAFT_GENERADO = "Draft generado"
FOLLOW_UP_ENVIADO = "Enviado"

ATTR_LEAD_STAGE = "lead_stage"
ATTR_LLAMADA_FECHA = "llamada_fecha"
ATTR_MATERIAL_A_ENVIAR = "material_a_enviar"
ATTR_NOTA_LLAMADA = "nota_llamada"
ATTR_CONTACTO_SECUNDARIO_EMAIL = "contacto_secundario_email"
ATTR_FOLLOW_UP_STATUS = "follow_up_status"


def _headers():
    return {
        "Authorization": f"Bearer {os.environ['ATTIO_API_KEY']}",
        "Content-Type": "application/json",
    }


def _first_value(entry_values, attr):
    """Los valores de entrada de Attio vienen como listas de objetos
    {"value": ...} (o variantes por tipo); devuelve el primer valor
    simple o None si el atributo no está seteado."""
    values = entry_values.get(attr) or []
    if not values:
        return None
    v = values[0]
    if isinstance(v, dict):
        return v.get("value") or v.get("option", {}).get("title")
    return v


def _person_values(record_id):
    r = requests.get(
        f"{BASE_URL}/objects/people/records/{record_id}",
        headers=_headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("data", {}).get("values", {})


def fetch_pending_follow_ups(list_id=COBOL_LATAM_LIST_ID, page_size=50):
    """Trae las entradas de la lista en stage 'Llamada realizada' que
    todavía no tienen follow-up generado, con los datos de Person
    (email, nombre, industria, etc.) ya resueltos."""
    pending = []
    offset = 0
    while True:
        r = requests.post(
            f"{BASE_URL}/lists/{list_id}/entries/query",
            headers=_headers(),
            json={"limit": page_size, "offset": offset},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            break
        for entry in data:
            entry_values = entry.get("entry_values", {})
            stage = _first_value(entry_values, ATTR_LEAD_STAGE)
            status = _first_value(entry_values, ATTR_FOLLOW_UP_STATUS) or FOLLOW_UP_PENDIENTE
            if stage != STAGE_LLAMADA_REALIZADA or status != FOLLOW_UP_PENDIENTE:
                continue

            record_id = entry.get("parent_record_id")
            if not record_id:
                continue
            person_values = _person_values(record_id)
            email_addrs = person_values.get("email_addresses") or []
            names = person_values.get("name") or []

            pending.append({
                "entry_id": entry["id"]["entry_id"],
                "record_id": record_id,
                "email": (email_addrs[0].get("email_address") if email_addrs else None),
                "full_name": (names[0].get("full_name") if names else None),
                "company": _first_value(entry_values, "company_name"),
                "industry": _first_value(entry_values, "company_industry"),
                "nota_llamada": _first_value(entry_values, ATTR_NOTA_LLAMADA),
                "material_a_enviar": [
                    m.get("option", {}).get("title") if isinstance(m, dict) else m
                    for m in (entry_values.get(ATTR_MATERIAL_A_ENVIAR) or [])
                ],
                "contacto_secundario_email": _first_value(entry_values, ATTR_CONTACTO_SECUNDARIO_EMAIL),
            })
        offset += page_size
        if len(data) < page_size:
            break
    return pending


def find_person_by_phone(phone, list_id=COBOL_LATAM_LIST_ID):
    """Busca la Person + su entrada en la lista por teléfono E.164 (así
    llega target_number en el webhook de Trellus). Devuelve
    (record_id, entry_id) o (None, None) si no hay match. No se puede
    vincular por contact_id de Trellus: ese ID es interno de Trellus,
    no corresponde al record_id de Attio (confirmado con un payload de
    prueba: contact_id no tenía formato de UUID de Attio)."""
    r = requests.post(
        f"{BASE_URL}/objects/people/records/query",
        headers=_headers(),
        json={"filter": {"phone_numbers": {"original_phone_number": phone}}},
        timeout=30,
    )
    r.raise_for_status()
    records = r.json().get("data", [])
    if not records:
        return None, None
    record_id = records[0]["id"]["record_id"]

    offset = 0
    while True:
        r = requests.post(
            f"{BASE_URL}/lists/{list_id}/entries/query",
            headers=_headers(),
            json={"filter": {"parent_record_id": record_id}, "limit": 50, "offset": offset},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        for entry in data:
            if entry.get("parent_record_id") == record_id:
                return record_id, entry["id"]["entry_id"]
        if len(data) < 50:
            break
        offset += 50
    return record_id, None


def record_call_summary(phone, summary, list_id=COBOL_LATAM_LIST_ID):
    """Punto de entrada del webhook de Trellus: busca la Person por
    teléfono, escribe el resumen en nota_llamada, mueve el stage a
    'Llamada realizada' y deja follow_up_status en 'Pendiente' para que
    followup/main.py la recoja. Devuelve dict con el resultado para
    que el endpoint pueda loguear/responder algo útil."""
    record_id, entry_id = find_person_by_phone(phone, list_id=list_id)
    if not entry_id:
        return {"matched": False, "record_id": record_id, "entry_id": None}

    payload = {
        "data": {
            "entry_values": {
                ATTR_NOTA_LLAMADA: [{"value": summary}],
                ATTR_LEAD_STAGE: [{"value": STAGE_LLAMADA_REALIZADA}],
                ATTR_FOLLOW_UP_STATUS: [{"value": FOLLOW_UP_PENDIENTE}],
            }
        }
    }
    r = requests.patch(
        f"{BASE_URL}/lists/{list_id}/entries/{entry_id}",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"no se pudo registrar resumen de llamada en {entry_id}: {r.status_code} {r.text[:500]}")
    return {"matched": True, "record_id": record_id, "entry_id": entry_id}


def mark_follow_up_status(entry_id, status, list_id=COBOL_LATAM_LIST_ID):
    """Actualiza follow_up_status en la entrada de lista -- es lo que
    hace idempotente al proceso: una corrida repetida del script no
    vuelve a generar/enviar el mismo follow-up."""
    payload = {"data": {"entry_values": {ATTR_FOLLOW_UP_STATUS: [{"value": status}]}}}
    r = requests.patch(
        f"{BASE_URL}/lists/{list_id}/entries/{entry_id}",
        headers=_headers(),
        json=payload,
        timeout=30,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"no se pudo actualizar follow_up_status de {entry_id}: {r.status_code} {r.text[:500]}")
