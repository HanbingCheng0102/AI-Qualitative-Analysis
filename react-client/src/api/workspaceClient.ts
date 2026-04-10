const API_URI = import.meta.env.VITE_API_URI ?? "http://localhost:3000";

async function readJson(response) {
  if (!response.ok) {
    const maybeJson = await response.json().catch(() => null);
    throw new Error(maybeJson?.error ?? response.statusText ?? "Request failed");
  }

  return response.json();
}

export async function getBootstrapData() {
  const response = await fetch(`${API_URI}/api/bootstrap`);
  return readJson(response);
}

export async function getWorkspaceSession() {
  const response = await fetch(`${API_URI}/api/workspace/session`);
  return readJson(response);
}

export async function saveWorkspaceSession(snapshot) {
  const response = await fetch(`${API_URI}/api/workspace/session`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(snapshot),
  });

  return readJson(response);
}

export async function getFloors() {
  const response = await fetch(`${API_URI}/api/floors`);
  return readJson(response);
}

export async function createFloor(payload) {
  const response = await fetch(`${API_URI}/api/floors`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return readJson(response);
}

export async function updateFloor(id, payload) {
  const response = await fetch(`${API_URI}/api/floors/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return readJson(response);
}
