import { api } from "./client";

export const getCart = () => api.get("/api/cart");
export const addToCart = (variant_id, qty = 1) => api.post("/api/cart/items", { variant_id, qty });
export const setCartQty = (variantId, qty) => api.patch(`/api/cart/items/${variantId}`, { qty });
export const removeFromCart = (variantId) => api.del(`/api/cart/items/${variantId}`);
export const mergeCart = (items) => api.post("/api/cart/merge", { items });
export const previewCart = (items) => api.post("/api/cart/preview", { items });
