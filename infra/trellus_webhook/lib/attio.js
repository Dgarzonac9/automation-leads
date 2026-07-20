// Cliente Attio mínimo para el webhook de Trellus. Espejo en JS de
// followup/attio_client.py (Python) -- Vercel no puede invocar Python
// desde esta función Node, así que la misma lógica de vinculación por
// teléfono vive acá también. Si cambia el contrato de campos, actualizar
// ambos lados.

const BASE_URL = "https://api.attio.com/v2";
const COBOL_LATAM_LIST_ID = "35c7dfa0-0f6f-41a2-a505-94e50535600d";

const STAGE_LLAMADA_REALIZADA = "Llamada realizada";
const FOLLOW_UP_PENDIENTE = "Pendiente";

const ATTR_LEAD_STAGE = "lead_stage";
const ATTR_NOTA_LLAMADA = "nota_llamada";
const ATTR_FOLLOW_UP_STATUS = "follow_up_status";

function headers() {
  return {
    Authorization: `Bearer ${process.env.ATTIO_API_KEY}`,
    "Content-Type": "application/json",
  };
}

async function findPersonByPhone(phone, listId = COBOL_LATAM_LIST_ID) {
  const searchRes = await fetch(`${BASE_URL}/objects/people/records/query`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      filter: { phone_numbers: { original_phone_number: phone } },
    }),
  });
  if (!searchRes.ok) {
    throw new Error(`attio person search failed: ${searchRes.status} ${await searchRes.text()}`);
  }
  const searchData = await searchRes.json();
  const records = searchData.data || [];
  if (records.length === 0) {
    return { recordId: null, entryId: null };
  }
  const recordId = records[0].id.record_id;

  let offset = 0;
  while (true) {
    const entriesRes = await fetch(`${BASE_URL}/lists/${listId}/entries/query`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({
        filter: { parent_record_id: recordId },
        limit: 50,
        offset,
      }),
    });
    if (!entriesRes.ok) {
      throw new Error(`attio list entries query failed: ${entriesRes.status} ${await entriesRes.text()}`);
    }
    const entriesData = await entriesRes.json();
    const data = entriesData.data || [];
    const match = data.find((e) => e.parent_record_id === recordId);
    if (match) {
      return { recordId, entryId: match.id.entry_id };
    }
    if (data.length < 50) break;
    offset += 50;
  }
  return { recordId, entryId: null };
}

async function recordCallSummary(phone, summary, listId = COBOL_LATAM_LIST_ID) {
  const { recordId, entryId } = await findPersonByPhone(phone, listId);
  if (!entryId) {
    return { matched: false, recordId, entryId: null };
  }

  const patchRes = await fetch(`${BASE_URL}/lists/${listId}/entries/${entryId}`, {
    method: "PATCH",
    headers: headers(),
    body: JSON.stringify({
      data: {
        entry_values: {
          [ATTR_NOTA_LLAMADA]: [{ value: summary }],
          [ATTR_LEAD_STAGE]: [{ value: STAGE_LLAMADA_REALIZADA }],
          [ATTR_FOLLOW_UP_STATUS]: [{ value: FOLLOW_UP_PENDIENTE }],
        },
      },
    }),
  });
  if (!patchRes.ok) {
    throw new Error(`attio entry update failed: ${patchRes.status} ${await patchRes.text()}`);
  }
  return { matched: true, recordId, entryId };
}

export { recordCallSummary, findPersonByPhone };
