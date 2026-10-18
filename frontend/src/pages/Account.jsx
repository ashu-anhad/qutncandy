import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { updateProfile } from "../api/auth";
import * as ordersApi from "../api/orders";
import { useAuth } from "../auth.jsx";
import AddressForm, { AddressLines } from "../components/AddressForm.jsx";

export default function Account() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState(user.name);
  const [status, setStatus] = useState("");

  const save = async (e) => {
    e.preventDefault();
    try {
      setUser(await updateProfile({ name }));
      setStatus("Saved");
    } catch (err) {
      setStatus(err.message);
    }
  };

  const signOut = async (everywhere) => {
    await logout({ everywhere });
    navigate("/");
  };

  return (
    <section className="narrow-wide stack">
      <div className="section-head">
        <h1>My account</h1>
        <Link to="/orders" className="button secondary">My orders</Link>
      </div>
      <form className="card stack" onSubmit={save}>
        <h2>Profile</h2>
        <div className="grid-2">
          <label>Name<input value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} /></label>
          {user.email && <label>Email<input value={user.email} disabled /></label>}
          {user.phone && <label>Mobile<input value={`+91 ${user.phone}`} disabled /></label>}
        </div>
        <div className="row">
          <button type="submit">Save</button>
          {status && <span className="muted">{status}</span>}
        </div>
      </form>
      <Addresses />
      <div className="row">
        <button className="secondary" onClick={() => signOut(false)}>Log out</button>
        <button className="secondary" onClick={() => signOut(true)}>Log out of all devices</button>
      </div>
    </section>
  );
}

function Addresses() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["addresses"], queryFn: ordersApi.listAddresses });
  const [editing, setEditing] = useState(null); // address id, "new", or null
  const [error, setError] = useState("");

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["addresses"] });
  const save = async (form) => {
    if (editing === "new") await ordersApi.createAddress(form);
    else await ordersApi.updateAddress(editing, form);
    await refresh();
    setEditing(null);
  };
  const remove = async (a) => {
    if (!confirm("Delete this address?")) return;
    await ordersApi.deleteAddress(a.id).catch((e) => setError(e.message));
    refresh();
  };
  const makeDefault = (a) => ordersApi.updateAddress(a.id, { ...a, is_default: true }).then(refresh);

  return (
    <div className="card stack">
      <div className="section-head">
        <h2>Saved addresses</h2>
        {editing === null && <button className="secondary" onClick={() => setEditing("new")}>Add address</button>}
      </div>
      {isLoading && <p className="muted">Loading…</p>}
      {error && <p className="error">{error}</p>}
      {editing === "new" && <AddressForm onSubmit={save} onCancel={() => setEditing(null)} />}
      {data?.length === 0 && editing === null && <p className="muted">No saved addresses yet.</p>}
      <div className="address-options">
        {data?.map((a) =>
          editing === a.id ? (
            <AddressForm key={a.id} initial={a} onSubmit={save} onCancel={() => setEditing(null)} />
          ) : (
            <div key={a.id} className="address-option">
              <AddressLines address={a} />
              <div className="row address-actions">
                {a.is_default ? <span className="pill pill-ok">Default</span> : (
                  <button className="small-btn secondary" onClick={() => makeDefault(a)}>Make default</button>
                )}
                <button className="small-btn secondary" onClick={() => setEditing(a.id)}>Edit</button>
                <button className="danger-link" onClick={() => remove(a)}>Delete</button>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
