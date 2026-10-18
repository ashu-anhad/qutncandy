import { api } from "./client";

const qs = (params) => {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    (Array.isArray(value) ? value : [value]).forEach((v) => sp.append(key, v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
};

// storefront
export const listCategories = () => api.get("/api/categories");
export const listProducts = (params = {}) => api.get(`/api/products${qs(params)}`);
export const getFilters = () => api.get("/api/products/filters");
export const getProduct = (slug) => api.get(`/api/products/${encodeURIComponent(slug)}`);

// admin
export const adminListProducts = (params = {}) => api.get(`/api/admin/products${qs(params)}`);
export const adminGetProduct = (id) => api.get(`/api/admin/products/${id}`);
export const createProduct = (data) => api.post("/api/admin/products", data);
export const updateProduct = (id, data) => api.patch(`/api/admin/products/${id}`, data);
export const deleteProduct = (id) => api.del(`/api/admin/products/${id}`);

export const createVariant = (productId, data) => api.post(`/api/admin/products/${productId}/variants`, data);
export const updateVariant = (id, data) => api.patch(`/api/admin/variants/${id}`, data);
export const deleteVariant = (id) => api.del(`/api/admin/variants/${id}`);

export const uploadImage = (productId, file, colour) => {
  const form = new FormData();
  form.append("file", file);
  if (colour) form.append("colour", colour);
  return api.upload(`/api/admin/products/${productId}/images`, form);
};
export const deleteImage = (id) => api.del(`/api/admin/images/${id}`);

export const createCategory = (data) => api.post("/api/admin/categories", data);
export const updateCategory = (id, data) => api.patch(`/api/admin/categories/${id}`, data);
export const deleteCategory = (id) => api.del(`/api/admin/categories/${id}`);
