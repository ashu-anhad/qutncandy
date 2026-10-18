import { api } from "./client";

export const listNotifications = () => api.get("/api/notifications");
export const markRead = (id) => api.post(`/api/notifications/${id}/read`);
export const markAllRead = () => api.post("/api/notifications/read-all");
