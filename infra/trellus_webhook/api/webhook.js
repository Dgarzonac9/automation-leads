// Endpoint receptor del webhook de Trellus (POST al terminar cada llamada).
// Vincula la llamada con la Person en Attio por teléfono (target_number
// == phone, ambos en E.164) -- no por contact_id, que es un ID interno
// de Trellus sin relación con record_id de Attio (confirmado con el
// payload de ejemplo de Trellus). Ver infra/trellus_webhook/lib/attio.js.

import { recordCallSummary } from "../lib/attio.js";

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

  const payload = req.body || {};
  console.log("[trellus_webhook] payload recibido:", JSON.stringify(payload));

  const { target_number: phone, summary } = payload;

  if (!phone || !summary) {
    console.log("[trellus_webhook] payload sin target_number o summary -- nada que registrar");
    res.status(200).json({ received: true, skipped: "missing_phone_or_summary" });
    return;
  }

  try {
    const result = await recordCallSummary(phone, summary, payload);
    console.log("[trellus_webhook] resultado Attio:", JSON.stringify(result));
    res.status(200).json({ received: true, attio: result });
  } catch (err) {
    console.error("[trellus_webhook] error al escribir en Attio:", err.message);
    res.status(502).json({ received: true, error: "attio_write_failed", detail: err.message });
  }
}
