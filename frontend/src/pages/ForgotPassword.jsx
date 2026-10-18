import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api/auth";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="auth-card card stack">
      <h1>Forgot your password?</h1>
      {sent ? (
        <>
          <p>If an account exists for <strong>{email}</strong>, we've emailed a link to reset your password. It's valid for 30 minutes.</p>
          <Link to="/login">Back to log in</Link>
        </>
      ) : (
        <form className="stack" onSubmit={submit}>
          <p className="muted">Enter your email and we'll send you a link to choose a new password.</p>
          <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" /></label>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={busy}>{busy ? "Sending…" : "Send reset link"}</button>
          <Link to="/login" className="small">Back to log in</Link>
        </form>
      )}
    </section>
  );
}
