"""
Armado de correos de follow-up post-llamada. Función pura: recibe los
datos de un lead + material a enviar, devuelve asunto/cuerpo. Sin I/O
de red acá para que sea fácil de probar y reusar sin importar quién
la invoque (cron, webhook, o a mano).
"""

MATERIAL_LINKS = {
    "Documentación técnica": None,  # completar con el link real
    "Video": "https://youtu.be/ntu76rwAmsU",
    "Propuesta": None,
    "Case study": None,
}

MATERIAL_LABELS = {
    "Documentación técnica": "Documentación técnica",
    "Video": "Video de la solución",
    "Propuesta": "Propuesta",
    "Case study": "Case study",
}

# Gancho por industria -- personalización real, no merge-tag. Se elige
# por company_industry (ver leadgen/schema.py INDUSTRIES); "default" cubre
# industrias fuera de esa lista o cuando el dato viene vacío.
INDUSTRY_HOOKS = {
    "banking": (
        "Dado el volumen de sistemas mainframe que suelen manejar los bancos "
        "de tu escala, seguramente te resulte más relevante lo relacionado a "
        "modernización y soporte CICS-COBOL a gran escala."
    ),
    "insurance": (
        "En aseguradoras con core mainframe, lo que más suele generar interés "
        "es la continuidad operativa durante la migración, sin downtime en "
        "los procesos críticos."
    ),
    "government administration": (
        "En organismos públicos, lo que más pesa suele ser la trazabilidad y "
        "el cumplimiento normativo del proceso de modernización, más que la "
        "velocidad en sí."
    ),
    "hospital & health care": (
        "En sistemas de salud, la prioridad suele ser la continuidad del "
        "servicio 24/7 durante cualquier intervención sobre el mainframe."
    ),
    "telecommunications": (
        "En telecomunicaciones, el foco suele estar en escalabilidad y "
        "soporte a picos de tráfico sobre la infraestructura mainframe."
    ),
    "default": (
        "Por lo que charlamos, creo que te va a resultar útil sobre todo la "
        "parte de casos de uso aplicados a tu industria específica."
    ),
}

SUBJECT_VARIANTS = [
    "Documentación técnica y video — seguimiento a nuestra llamada",
    "Como quedamos en la llamada, te comparto el material",
    "Siguiendo nuestra conversación de hoy",
]


def _industry_hook(industry):
    key = (industry or "").strip().lower()
    return INDUSTRY_HOOKS.get(key, INDUSTRY_HOOKS["default"])


def _material_lines(material_a_enviar):
    lines = []
    for item in material_a_enviar or []:
        label = MATERIAL_LABELS.get(item, item)
        link = MATERIAL_LINKS.get(item)
        lines.append(f"- {label}: {link or '[LINK PENDIENTE]'}")
    return "\n".join(lines)


def build_follow_up_email(lead, subject_variant_index=0):
    """lead: dict con al menos full_name, company, industry, nota_llamada,
    material_a_enviar (lista de strings). Devuelve dict {subject, body}."""
    first_name = (lead.get("full_name") or "").split(" ")[0] or "equipo"
    subject = SUBJECT_VARIANTS[subject_variant_index % len(SUBJECT_VARIANTS)]

    nota = lead.get("nota_llamada")
    contexto = (
        f"Gracias por el tiempo en la llamada de hoy. {nota.strip()}"
        if nota
        else "Gracias por el tiempo en la llamada de hoy."
    )

    material = _material_lines(lead.get("material_a_enviar"))
    gancho = _industry_hook(lead.get("industry"))

    body = (
        f"Hola {first_name},\n\n"
        f"{contexto}\n\n"
        f"Como quedamos, te comparto el material:\n\n"
        f"{material}\n\n"
        f"{gancho}\n\n"
        f"Quedo atento a cualquier consulta que surja de la revisión, y con "
        f"gusto coordinamos una llamada corta de 15 minutos para resolver "
        f"dudas puntuales o ver una demo cuando te quede cómodo.\n\n"
        f"Saludos,\n"
        f"[TU NOMBRE]\n"
        f"[TU CARGO]"
    )

    return {"subject": subject, "body": body}
