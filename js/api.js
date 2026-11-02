// Optional Flask API client. The current demo UI continues to use localStorage
// until ERP_API_URL is configured, so the static pages remain usable offline.
const ERPApi = (() => {
  const baseUrl = (
    window.ERP_API_URL ||
    localStorage.getItem("itpc_api_url") ||
    ""
  ).replace(/\/$/, "");
  const pendingWrites = new Map();

  async function request(path, options = {}) {
    if (!baseUrl) throw new Error("ERP_API_URL is not configured.");
    const response = await fetch(baseUrl + path, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || "The API request failed.");
    return body;
  }

  async function syncToLocalStorage() {
    if (!baseUrl) return;
    const [inventory, events, archives] = await Promise.all([
      request("/api/inventory"),
      request("/api/events"),
      request("/api/archives"),
    ]);
    const officers = await request("/api/officers");
    localStorage.setItem("itpc_inventory", JSON.stringify(inventory.items || []));
    localStorage.setItem("itpc_events", JSON.stringify(events.events || []));
    localStorage.setItem("itpc_archives", JSON.stringify(archives.archives || []));
    localStorage.setItem("itpc_officers", JSON.stringify(officers.officers || []));
    try {
      const logs = await request("/api/audit-logs");
      const normalizedLogs = (logs.logs || []).map((entry) => {
        if (Array.isArray(entry.details)) return entry;
        const details = entry.details || {};
        if (details.before && details.after) {
          const fields = new Set([
            ...Object.keys(details.before),
            ...Object.keys(details.after),
          ]);
          entry.details = [...fields].map((field) => ({
            field: field,
            from: details.before[field] ?? null,
            to: details.after[field] ?? null,
          }));
        } else {
          entry.details = Object.entries(details).map(([field, value]) => ({
            field: field,
            from: null,
            to: value,
          }));
        }
        return entry;
      });
      localStorage.setItem("itpc_changelog", JSON.stringify(normalizedLogs));
    } catch (error) {
      if (error.message.includes("Administrator")) throw error;
    }
  }

  function persist(key, data) {
    if (!baseUrl || !["itpc_inventory", "itpc_events", "itpc_archives", "itpc_officers"].includes(key)) {
      return Promise.resolve();
    }
    const route = {
      itpc_inventory: "/api/inventory/sync",
      itpc_events: "/api/events/sync",
      itpc_archives: "/api/archives/sync",
      itpc_officers: "/api/officers/sync",
    }[key];
    const field = {
      itpc_inventory: "items",
      itpc_events: "events",
      itpc_archives: "archives",
      itpc_officers: "officers",
    }[key];
    const previous = pendingWrites.get(key) || Promise.resolve();
    const next = previous
      .catch(() => undefined)
      .then(() =>
        request(route, {
          method: "PUT",
          body: JSON.stringify({ [field]: data }),
        }),
      );
    pendingWrites.set(key, next);
    return next;
  }

  return Object.freeze({
    enabled: Boolean(baseUrl),
    syncToLocalStorage,
    persist,
    login: (username, password) =>
      request("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),
    logout: () => request("/api/auth/logout", { method: "POST" }),
    me: () => request("/api/auth/me"),
    inventory: () => request("/api/inventory"),
    events: () => request("/api/events"),
    archives: () => request("/api/archives"),
    auditLogs: () => request("/api/audit-logs"),
    reportSummary: () => request("/api/reports/summary"),
  });
})();
