import { api } from "./client";

const base = (slug) => `/api/products/${encodeURIComponent(slug)}/reviews`;

export const listReviews = (slug, page = 1) => api.get(`${base(slug)}?page=${page}`);
export const myReview = (slug) => api.get(`${base(slug)}/mine`);
export const writeReview = (slug, data) => api.put(base(slug), data);

export const adminListReviews = (status = "pending", page = 1) => api.get(`/api/admin/reviews?status=${status}&page=${page}`);
export const moderateReview = (id, action) => api.post(`/api/admin/reviews/${id}/${action}`);
export const deleteReview = (id) => api.del(`/api/admin/reviews/${id}`);
