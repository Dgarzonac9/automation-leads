// Endpoint receptor del webhook de Trellus (POST al terminar cada llamada).
// Fase de diagnóstico: valida el secreto y devuelve el payload recibido,
// para confirmar el mapeo de campos (contact_id, summary, etc.) contra
// Attio usando el botón "Test Webhook" de Trellus antes de escribir la
// lógica real de sincronización.

export default async function handler(req, res) {
  // Trellus dispara el webhook desde una extensión de Chrome (no un
  // backend), así que el request queda sujeto a CORS del navegador --
  // sin estos headers, el browser bloquea la respuesta antes de que
  // Trellus la vea, aunque el servidor sí haya procesado el POST.
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-Webhook-Secret");

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }

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
