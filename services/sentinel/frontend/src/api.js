const BASE = '/api';

function fetchWithTimeout(url, options = {}, timeoutMs = 60000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timer));
}

export async function fetchSilos() {
  const res = await fetchWithTimeout(`${BASE}/silos`);
  if (!res.ok) throw new Error(`Failed to fetch silos: ${res.status}`);
  return res.json();
}

export async function fetchTiles() {
  const res = await fetchWithTimeout(`${BASE}/tiles`);
  if (!res.ok) throw new Error(`Failed to fetch tiles: ${res.status}`);
  return res.json();
}

export async function moveTile(tileId, column) {
  const res = await fetchWithTimeout(`${BASE}/tiles/${tileId}/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ column }),
  });
  if (!res.ok) throw new Error(`Failed to move tile: ${res.status}`);
  return res.json();
}

export async function recordInteraction(tileId, data) {
  const res = await fetchWithTimeout(`${BASE}/tiles/${tileId}/interact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to record interaction: ${res.status}`);
  return res.json();
}

export async function fetchInteractions() {
  const res = await fetchWithTimeout(`${BASE}/interactions`);
  if (!res.ok) throw new Error(`Failed to fetch interactions: ${res.status}`);
  return res.json();
}

export async function resetInteractions() {
  const res = await fetchWithTimeout(`${BASE}/interactions/reset`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to reset interactions: ${res.status}`);
  return res.json();
}

export async function resetTileInteraction(tileId) {
  const res = await fetchWithTimeout(`${BASE}/tiles/${tileId}/interaction/reset`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to reset tile interaction: ${res.status}`);
  return res.json();
}

export async function fetchDatasources() {
  const res = await fetchWithTimeout(`${BASE}/datasources`);
  if (!res.ok) throw new Error(`Failed to fetch datasources: ${res.status}`);
  return res.json();
}

export async function fetchSiloHints() {
  const res = await fetchWithTimeout(`${BASE}/silos/hints`);
  if (!res.ok) throw new Error(`Failed to fetch hints: ${res.status}`);
  return res.json();
}

export async function rediscoverSilos(hints) {
  const res = await fetchWithTimeout(`${BASE}/silos/rediscover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hints }),
  }, 90000); // 90s for rediscovery (LLM call)
  if (!res.ok) throw new Error(`Failed to rediscover: ${res.status}`);
  return res.json();
}

export async function fetchRowConfig() {
  const res = await fetchWithTimeout(`${BASE}/rows/config`);
  if (!res.ok) throw new Error(`Failed to fetch row config: ${res.status}`);
  return res.json();
}

export async function saveRowConfig(rows) {
  const res = await fetchWithTimeout(`${BASE}/rows/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rows }),
  });
  if (!res.ok) throw new Error(`Failed to save row config: ${res.status}`);
  return res.json();
}

export async function askQuestion(question, tileContext = null, createTile = false) {
  const res = await fetchWithTimeout(`${BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, tile_context: tileContext, create_tile: createTile }),
  }, 90000); // 90s for ask (LLM call)
  if (!res.ok) throw new Error(`Failed to ask: ${res.status}`);
  return res.json();
}
