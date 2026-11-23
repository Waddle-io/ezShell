"use client";

import { useState } from "react";

export default function WaitlistForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setStatus("loading");

    try {
      const response = await fetch("/api/v1/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: "landing" }),
      });
      if (!response.ok) throw new Error("waitlist");
      setStatus("success");
      setEmail("");
    } catch {
      setStatus("error");
    }
  }

  return (
    <form className="footer-waitlist" onSubmit={submit}>
      <label htmlFor="footer-waitlist-email">Reçois l&apos;annonce du lancement</label>
      <div className="footer-waitlist-row">
        <input
          id="footer-waitlist-email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="vous@exemple.com"
        />
        <button type="submit" disabled={status === "loading"}>
          {status === "loading" ? "Envoi…" : "M’avertir"}
        </button>
      </div>
      {status === "success" && <p role="status">Inscription enregistrée.</p>}
      {status === "error" && <p role="alert">Impossible d&apos;enregistrer cette adresse.</p>}
    </form>
  );
}
