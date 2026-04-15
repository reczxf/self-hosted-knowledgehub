/**
 * Parse a failed HTTP response into a readable error.
 * @param {Response} response
 * @returns {Promise<never>}
 */
async function raiseApiError(response) {
  const text = await response.text();
  throw new Error(text || `${response.status} ${response.statusText}`);
}

/**
 * Send an HTTP request to the backend API.
 * @param {string} path
 * @param {RequestInit} [options={}]
 * @returns {Promise<any>}
 */
export async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) };

  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(path, {
    ...options,
    headers
  });

  if (!response.ok) {
    return raiseApiError(response);
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

export const api = {
  health: () => apiRequest("/healthz"),
  listSources: () => apiRequest("/sources?limit=50"),
  getSource: (id) => apiRequest(`/sources/${id}`),
  listSourceVersions: (id) => apiRequest(`/sources/${id}/versions?limit=50`),
  getSourceVersion: (id) => apiRequest(`/versions/${id}`),
  listKnowledge: () => apiRequest("/knowledge?limit=50"),
  getKnowledge: (id) => apiRequest(`/knowledge/${id}`),
  listEvents: () => apiRequest("/events?limit=50"),
  listJobs: () => apiRequest("/jobs?limit=50"),
  runJobs: () => apiRequest("/jobs/run?limit=20", { method: "POST" }),
  searchText: (query) =>
    apiRequest(`/search/text?q=${encodeURIComponent(query)}&limit=20`),
  searchSemantic: (query) =>
    apiRequest(`/search/semantic?q=${encodeURIComponent(query)}&limit=20`),
  answerConversation: (payload) =>
    apiRequest("/conversation/answer", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  ingestStructured: (kind, payload) =>
    apiRequest(`/ingest/${kind}`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  ingestUpload: (formData) =>
    apiRequest("/ingest/upload", {
      method: "POST",
      body: formData
    })
};
