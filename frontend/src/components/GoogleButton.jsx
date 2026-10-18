import { useEffect, useRef, useState } from "react";

const SCRIPT_URL = "https://accounts.google.com/gsi/client";
let scriptPromise = null;

const loadScript = () =>
  (scriptPromise ??= new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = SCRIPT_URL;
    s.async = true;
    s.onload = resolve;
    s.onerror = () => {
      scriptPromise = null;
      reject(new Error("Couldn't load Google sign-in"));
    };
    document.head.appendChild(s);
  }));

// Renders Google's own "Continue with Google" button; calls onCredential with the ID token.
export default function GoogleButton({ clientId, onCredential }) {
  const ref = useRef(null);
  const callback = useRef(onCredential);
  const [error, setError] = useState("");
  callback.current = onCredential;

  useEffect(() => {
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled || !ref.current) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (res) => callback.current(res.credential),
        });
        window.google.accounts.id.renderButton(ref.current, {
          theme: "outline", size: "large", text: "continue_with", width: ref.current.offsetWidth || 320,
        });
      })
      .catch((e) => setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [clientId]);

  return (
    <>
      <div ref={ref} className="google-btn" />
      {error && <span className="muted small">{error}</span>}
    </>
  );
}
