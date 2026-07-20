// Endpoint receptor del webhook de Trellus (POST al terminar cada llamada).
// Fase de diagnóstico: valida el secreto y devuelve el payload recibido,
// para confirmar el mapeo de campos (contact_id, summary, etc.) contra
// Attio usando el botón "Test Webhook" de Trellus antes de escribir la
// lógica real de sincronización.

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ error: "method_not_allowed" });
    return;
  }

  const secret = req.headers["x-webhook-secret"];
  if (!secret || secret !== process.env.TRELLUS_WEBHOOK_SECRET) {
    res.status(401).json({ error: "unauthorized" });
    return;
  }

  const payload = req.body;
  console.log("[trellus_webhook] payload recibido:", JSON.stringify(payload));

  res.status(200).json({ received: true, echo: payload });
}
