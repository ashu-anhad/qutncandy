import { api } from "./client";

export const signup = (data) => api.post("/api/auth/signup", data);
export const login = (data) => api.post("/api/auth/login", data);
export const logout = () => api.post("/api/auth/logout");
export const logoutAll = () => api.post("/api/auth/logout-all");
export const updateProfile = (data) => api.patch("/api/me", data);
export const listUsers = (page = 1) => api.get(`/api/admin/users?page=${page}`);
export const forgotPassword = (email) => api.post("/api/auth/forgot-password", { email });
export const resetPassword = (token, password) => api.post("/api/auth/reset-password", { token, password });
export const getProviders = () => api.get("/api/auth/providers");
export const googleLogin = (credential) => api.post("/api/auth/google", { credential });
export const sendOtp = (phone) => api.post("/api/auth/otp/send", { phone });
export const verifyOtp = (data) => api.post("/api/auth/otp/verify", data);
