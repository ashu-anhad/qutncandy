import { api, download } from "./client";

const qs = (params) => {
  const sp = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ""));
  const s = sp.toString();
  return s ? `?${s}` : "";
};

export const getStats = () => api.get("/api/admin/stats");
export const listOrders = (params = {}) => api.get(`/api/admin/orders${qs(params)}`);
export const getOrder = (number) => api.get(`/api/admin/orders/${encodeURIComponent(number)}`);
export const orderAction = (number, action, body = {}) =>
  api.post(`/api/admin/orders/${encodeURIComponent(number)}/${action}`, body);
export const getInventory = (params = {}) => api.get(`/api/admin/inventory${qs(params)}`);

export const salesReport = (params) => api.get(`/api/admin/reports/sales${qs(params)}`);
export const topProductsReport = (params) => api.get(`/api/admin/reports/top-products${qs(params)}`);
export const discountsReport = (params) => api.get(`/api/admin/reports/discounts${qs(params)}`);
export const downloadReport = (name, params) =>
  download(`/api/admin/reports/${name}${qs({ ...params, format: "csv" })}`, `${name}_${params.start}_to_${params.end}.csv`);
