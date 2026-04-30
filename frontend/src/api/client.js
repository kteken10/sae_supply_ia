import axios from "axios";

// En dev, `/api` est proxifie par Vite vers le backend local (vite.config.js).
// En prod, VITE_API_BASE_URL pointe vers l'URL absolue du backend (Fly.io).
const baseURL = import.meta.env.VITE_API_BASE_URL || "/api";

export const api = axios.create({
  baseURL,
  timeout: 30000,
});

export const catalogApi = {
  meta: () => api.get("/catalog/meta").then((r) => r.data),
};

export const kpisApi = {
  overview: (now) => api.get("/kpis", { params: { now } }).then((r) => r.data),
  timeseries: (now) =>
    api.get("/kpis/timeseries", { params: { now } }).then((r) => r.data),
};

export const stockApi = {
  alerts: (now, max_items = 20) =>
    api.get("/stock/alerts", { params: { now, max_items } }).then((r) => r.data),
  snapshot: (now, store_id, product_id) =>
    api
      .get("/stock/snapshot", { params: { now, store_id, product_id } })
      .then((r) => r.data),
  timeseries: (store_id, product_id) =>
    api
      .get("/stock/timeseries", { params: { store_id, product_id } })
      .then((r) => r.data),
};

export const forecastApi = {
  get: (store_id, product_id, now, horizon_weeks = 4) =>
    api
      .get("/forecast", { params: { store_id, product_id, now, horizon_weeks } })
      .then((r) => r.data),
};

export const recosApi = {
  list: (now, max_items = 30) =>
    api
      .get("/recommendations", { params: { now, max_items } })
      .then((r) => r.data),
  one: (store_id, product_id, now) =>
    api
      .get("/recommendations/one", { params: { store_id, product_id, now } })
      .then((r) => r.data),
  validate: (payload) =>
    api.post("/recommendations/validate", payload).then((r) => r.data),
};

export const suppliersApi = {
  list: () => api.get("/suppliers").then((r) => r.data),
  detail: (id) => api.get(`/suppliers/${id}`).then((r) => r.data),
};

export const auditApi = {
  list: (limit = 100) =>
    api.get("/audit", { params: { limit } }).then((r) => r.data),
  modelCard: () => api.get("/audit/model-card").then((r) => r.data),
};

export const settingsApi = {
  get: () => api.get("/settings").then((r) => r.data),
  setUseEnriched: (value) =>
    api.post("/settings", { use_enriched: value }).then((r) => r.data),
};
