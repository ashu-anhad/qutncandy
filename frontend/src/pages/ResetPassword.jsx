import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPassword } from "../api/auth";
import { useAuth } from "../auth.jsx";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const { startSession } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (password !== confirm) return setError("The passwords don't match.");
    setBusy(true);
    setError("");
    try {
      startSession(await resetPassword(token, password));
      navigate("/account", { replace: true });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <section className="auth-card card stack">
        <h1>Reset link missing</h1>
        <p className="muted">Open the link from your email, or request a new one.</p>
        <Link to="/forgot-password">Request a new link</Link>
      </section>
    );
  }

  return (
    <section className="auth-card card stack">
      <h1>Choose a new password</h1>
      <form className="stack" onSubmit={submit}>
        <label>New password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoComplete="new-password" /></label>
        <label>Confirm new password<input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} autoComplete="new-password" /></label>
        {error && <p className="error">{error}</p>}
        {error.includes("expired") && <Link to="/forgot-password" className="small">Request a new link</Link>}
        <button type="submit" disabled={busy}>{busy ? "Saving…" : "Set new password"}</button>
      </form>
    </section>
  );
}
