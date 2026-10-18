import { api } from "./client";

export const getQuote = (discount_code) => api.post("/api/orders/quote", { discount_code: discount_code || null });
export const placeOrder = (data) => api.post("/api/orders", data);
export const listOrders = (page = 1) => api.get(`/api/orders?page=${page}`);
export const getOrder = (number) => api.get(`/api/orders/${encodeURIComponent(number)}`);
export const cancelOrder = (number) => api.post(`/api/orders/${encodeURIComponent(number)}/cancel`);

export const listAddresses = () => api.get("/api/me/addresses");
export const createAddress = (data) => api.post("/api/me/addresses", data);
export const updateAddress = (id, data) => api.put(`/api/me/addresses/${id}`, data);
export const deleteAddress = (id) => api.del(`/api/me/addresses/${id}`);

export const adminListDiscounts = () => api.get("/api/admin/discounts");
export const createDiscount = (data) => api.post("/api/admin/discounts", data);
export const updateDiscount = (id, data) => api.patch(`/api/admin/discounts/${id}`, data);
export const deleteDiscount = (id) => api.del(`/api/admin/discounts/${id}`);

export const startPayment = (number) => api.post(`/api/orders/${encodeURIComponent(number)}/pay`);
export const verifyPayment = (data) => api.post("/api/payments/verify", data);
