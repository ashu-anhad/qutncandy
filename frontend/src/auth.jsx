import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import * as authApi from "./api/auth";
import { refreshSession, setAccessToken, setSessionLostHandler } from "./api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore the session from the refresh cookie on first load.
  useEffect(() => {
    setSessionLostHandler(() => setUser(null));
    refreshSession().then((data) => {
      setUser(data?.user ?? null);
      setLoading(false);
    });
  }, []);

  const startSession = useCallback((data) => {
    setAccessToken(data.access_token);
    setUser(data.user);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      setUser,
      startSession,
      login: async (creds) => startSession(await authApi.login(creds)),
      signup: async (data) => startSession(await authApi.signup(data)),
      logout: async ({ everywhere = false } = {}) => {
        await (everywhere ? authApi.logoutAll() : authApi.logout()).catch(() => {});
        setAccessToken(null);
        setUser(null);
      },
    }),
    [user, loading, startSession]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

export function RequireAuth({ children, admin = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p className="muted center">Loading…</p>;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  if (admin && user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}
