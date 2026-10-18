import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { getProviders, googleLogin, sendOtp, verifyOtp } from "../api/auth";
import { useAuth } from "../auth.jsx";
import GoogleButton from "../components/GoogleButton.jsx";

export default function Login() {
  const { user, startSession } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") || "/";
  const providers = useQuery({ queryKey: ["auth-providers"], queryFn: getProviders, staleTime: Infinity });
  const [method, setMethod] = useState("email");
  const [error, setError] = useState("");

  if (user) return <Navigate to={next} replace />;

  const done = (session) => {
    if (session) startSession(session);
    navigate(next, { replace: true });
  };
  const google = async (credential) => {
    setError("");
    try {
      done(await googleLogin(credential));
    } catch (err) {
      setError(err.message);
    }
  };

  const p = providers.data;
  return (
    <section className="auth-card card stack">
      <img src="/brand/mark.png" alt="QutnCandy" className="auth-mark" width="64" height="64" />
      {p?.phone_otp && (
        <div className="segmented" role="tablist">
          <button role="tab" aria-selected={method === "email"} className={method === "email" ? "active" : ""} onClick={() => setMethod("email")}>Email</button>
          <button role="tab" aria-selected={method === "phone"} className={method === "phone" ? "active" : ""} onClick={() => setMethod("phone")}>Mobile number</button>
        </div>
      )}
      {method === "phone" && p?.phone_otp ? <PhoneLogin onDone={done} /> : <EmailLogin onDone={done} />}
      {p?.google_client_id && (
        <>
          <div className="divider"><span>or</span></div>
          <GoogleButton clientId={p.google_client_id} onCredential={google} />
        </>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}

function EmailLogin({ onDone }) {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      // login/signup already start the session; onDone just navigates.
      if (mode === "login") await login({ email: form.email, password: form.password });
      else await signup(form);
      onDone(null);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <>
      <div className="tabs">
        <button className={mode === "login" ? "tab active" : "tab"} onClick={() => setMode("login")}>Log in</button>
        <button className={mode === "signup" ? "tab active" : "tab"} onClick={() => setMode("signup")}>Create account</button>
      </div>
      <form className="stack" onSubmit={submit}>
        {mode === "signup" && <label>Name<input value={form.name} onChange={set("name")} required maxLength={100} /></label>}
        <label>Email<input type="email" value={form.email} onChange={set("email")} required autoComplete="email" /></label>
        <label>
          Password
          <input type="password" value={form.password} onChange={set("password")} required minLength={mode === "signup" ? 8 : undefined}
            autoComplete={mode === "login" ? "current-password" : "new-password"} />
        </label>
        {mode === "login" && <Link to="/forgot-password" className="small">Forgot password?</Link>}
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}</button>
      </form>
    </>
  );
}

function PhoneLogin({ onDone }) {
  const [step, setStep] = useState("phone"); // phone -> code -> name
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (fn) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (err) {
      if (err.status === 428) setStep("name");
      else setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const send = (e) => {
    e?.preventDefault();
    run(async () => {
      await sendOtp(phone);
      setStep("code");
      setInfo(`We've sent a 6-digit code to ${phone}.`);
    });
  };
  const verify = (e) => {
    e.preventDefault();
    run(async () => onDone(await verifyOtp({ phone, code, ...(step === "name" && { name }) })));
  };

  if (step === "phone") {
    return (
      <form className="stack" onSubmit={send}>
        <label>
          Mobile number
          <span className="phone-input"><span className="muted">+91</span>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} required inputMode="numeric" maxLength={14}
              autoComplete="tel-national" placeholder="98765 43210" />
          </span>
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>{busy ? "Sending…" : "Send code"}</button>
      </form>
    );
  }

  return (
    <form className="stack" onSubmit={verify}>
      <span className="muted small">{info} <button type="button" className="link-btn" onClick={() => { setStep("phone"); setCode(""); }}>Change number</button></span>
      <label>
        Code
        <input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required inputMode="numeric"
          pattern="\d{6}" maxLength={6} autoComplete="one-time-code" autoFocus disabled={step === "name"} />
      </label>
      {step === "name" && (
        <label>
          Welcome! What's your name?
          <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} autoFocus autoComplete="name" />
        </label>
      )}
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? "Checking…" : step === "name" ? "Create account" : "Verify & continue"}</button>
      <button type="button" className="link-btn small" onClick={send} disabled={busy}>Resend code</button>
    </form>
  );
}
