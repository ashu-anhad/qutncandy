import { useState } from "react";

const STATES = [
  "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chandigarh",
  "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa", "Gujarat", "Haryana",
  "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep",
  "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry",
  "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
  "West Bengal",
];

const EMPTY = { name: "", phone: "", line1: "", line2: "", city: "", state: "", pincode: "", is_default: false };

export default function AddressForm({ initial, onSubmit, onCancel, submitLabel = "Save address" }) {
  const [form, setForm] = useState({ ...EMPTY, ...initial });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSubmit(form);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="stack" onSubmit={submit}>
      <div className="grid-2">
        <label>Full name<input value={form.name} onChange={set("name")} required maxLength={100} autoComplete="name" /></label>
        <label>
          Mobile number
          <input value={form.phone} onChange={set("phone")} required pattern="[6-9][0-9]{9}" inputMode="numeric"
            maxLength={10} title="10-digit mobile number" autoComplete="tel-national" />
        </label>
      </div>
      <label>Address line 1<input value={form.line1} onChange={set("line1")} required maxLength={200} placeholder="House no., street" autoComplete="address-line1" /></label>
      <label>Address line 2 (optional)<input value={form.line2} onChange={set("line2")} maxLength={200} placeholder="Area, landmark" autoComplete="address-line2" /></label>
      <div className="grid-3">
        <label>City<input value={form.city} onChange={set("city")} required maxLength={100} autoComplete="address-level2" /></label>
        <label>
          State
          <select value={form.state} onChange={set("state")} required autoComplete="address-level1">
            <option value="" disabled>Choose…</option>
            {STATES.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label>
          PIN code
          <input value={form.pincode} onChange={set("pincode")} required pattern="[1-9][0-9]{5}" inputMode="numeric"
            maxLength={6} title="6-digit PIN code" autoComplete="postal-code" />
        </label>
      </div>
      <label className="check"><input type="checkbox" checked={form.is_default} onChange={set("is_default")} /> Make this my default address</label>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button type="submit" disabled={busy}>{busy ? "Saving…" : submitLabel}</button>
        {onCancel && <button type="button" className="secondary" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}

export function AddressLines({ address }) {
  return (
    <div className="address-lines">
      <strong>{address.name}</strong>
      <span>{address.line1}{address.line2 ? `, ${address.line2}` : ""}</span>
      <span>{address.city}, {address.state} {address.pincode}</span>
      <span className="muted">+91 {address.phone}</span>
    </div>
  );
}
