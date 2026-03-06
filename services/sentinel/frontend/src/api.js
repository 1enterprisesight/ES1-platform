const BASE = '/api';

function fetchWithTimeout(url, options = {}, timeoutMs = 60000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal, credentials: 'same-origin' }).finally(() => clearTimeout(timer));
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function login(email, password) {
  const res = await fetchWithTimeout(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Login failed: ${res.status}`);
  }
  return res.json();
}

export async function register(email, password, displayName) {
  const res = await fetchWithTimeout(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, display_name: displayName || undefined }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Registration failed: ${res.status}`);
  }
  return res.json();
}

export async function forgotPassword(email) {
  const res = await fetchWithTimeout(`${BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function resetPassword(token, password) {
  const res = await fetchWithTimeout(`${BASE}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Reset failed: ${res.status}`);
  }
  return res.json();
}

export async function verifyEmail(token) {
  const res = await fetchWithTimeout(`${BASE}/auth/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Verification failed: ${res.status}`);
  }
  return res.json();
}

export async function logout() {
  const res = await fetchWithTimeout(`${BASE}/auth/logout`, { method: 'POST' });
  if (!res.ok) throw new Error(`Logout failed: ${res.status}`);
  return res.json();
}

export async function fetchMe() {
  const res = await fetchWithTimeout(`${BASE}/auth/me`);
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`Failed to fetch user: ${res.status}`);
  return res.json();
}

export async function fetchUsers() {
  const res = await fetchWithTimeout(`${BASE}/admin/users`);
  if (!res.ok) throw new Error(`Failed to fetch users: ${res.status}`);
  return res.json();
}

export async function updateUserStatus(userId, status) {
  const res = await fetchWithTimeout(`${BASE}/admin/users/${userId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error(`Failed to update user: ${res.status}`);
  return res.json();
}

export async function updateUserRole(userId, role) {
  const res = await fetchWithTimeout(`${BASE}/admin/users/${userId}/role`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  });
  if (!res.ok) throw new Error(`Failed to update user: ${res.status}`);
  return res.json();
}

export async function deleteUser(userId) {
  const res = await fetchWithTimeout(`${BASE}/admin/users/${userId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete user: ${res.status}`);
  return res.json();
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

// ---------------------------------------------------------------------------
// Datasets
// ---------------------------------------------------------------------------

export async function fetchDatasets() {
  const res = await fetchWithTimeout(`${BASE}/datasets`);
  if (!res.ok) throw new Error(`Failed to fetch datasets: ${res.status}`);
  return res.json();
}

export async function uploadDataset(file, name) {
  const form = new FormData();
  form.append('file', file);
  if (name) form.append('name', name);
  const res = await fetchWithTimeout(`${BASE}/datasets/upload`, {
    method: 'POST',
    body: form,
  }, 120000); // 2min for large uploads
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function deleteDataset(datasetId) {
  const res = await fetchWithTimeout(`${BASE}/datasets/${datasetId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete dataset: ${res.status}`);
  return res.json();
}

export async function reloadDatasets() {
  const res = await fetchWithTimeout(`${BASE}/datasets/reload`, { method: 'POST' }, 120000);
  if (!res.ok) throw new Error(`Failed to reload datasets: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Workspaces
// ---------------------------------------------------------------------------

export async function fetchWorkspaces() {
  const res = await fetchWithTimeout(`${BASE}/workspaces`);
  if (!res.ok) throw new Error(`Failed to fetch workspaces: ${res.status}`);
  return res.json();
}

export async function createWorkspace(name) {
  const res = await fetchWithTimeout(`${BASE}/workspaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`Failed to create workspace: ${res.status}`);
  return res.json();
}

export async function deleteWorkspace(workspaceId) {
  const res = await fetchWithTimeout(`${BASE}/workspaces/${workspaceId}`, { method: 'DELETE' });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to delete workspace: ${res.status}`);
  }
  return res.json();
}

export async function activateWorkspace(workspaceId) {
  const res = await fetchWithTimeout(`${BASE}/workspaces/${workspaceId}/activate`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to activate workspace: ${res.status}`);
  return res.json();
}

export async function saveWorkspaceState(workspaceId, state) {
  const res = await fetchWithTimeout(`${BASE}/workspaces/${workspaceId}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(state),
  });
  if (!res.ok) throw new Error(`Failed to save workspace: ${res.status}`);
  return res.json();
}
