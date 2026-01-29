"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "../../auth.module.css";
import { API } from "@/lib/api";
import { saveToken } from "@/lib/auth";

export default function BrandLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const body = new URLSearchParams();
      body.append("username", email);
      body.append("password", password);

      const res = await fetch(API.brandAuth.login, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Login failed. Check your credentials.");
      }

      const data = await res.json();
      saveToken(data.access_token, "brand");
      router.replace("/advisor/brands");
    } catch (err: any) {
      setError(err.message || "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.shell}>
      <div className={styles.hero}>AI Virtual Closet</div>
      <div className={styles.card}>
        <div className={styles.headerRow}>
          <div>
            <p className={styles.eyebrow}>Brand Access</p>
            <h1>Sign in as a brand</h1>
            <p className={styles.muted}>Manage your brand ingestion and profile.</p>
          </div>
        </div>

        {error && <div className={styles.toastError}>{error}</div>}

        <form onSubmit={handleLogin} className={styles.form}>
          <label className={styles.label}>Office Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="brand@company.com"
            />
          </label>

          <label className={styles.label}>Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </label>

          <button type="submit" className={styles.primaryBtn} disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className={styles.footerText}>
          New brand? <button type="button" className={styles.linkBtn} onClick={() => router.push("/auth/brand/signup")}>Create brand account</button>
        </p>

        <div style={{ marginTop: "24px", paddingTop: "24px", borderTop: "1px solid rgba(0, 0, 0, 0.1)" }}>
          <p className={styles.muted} style={{ marginBottom: "12px", fontSize: "0.9rem" }}>Are you a user?</p>
          <button 
            type="button" 
            className={styles.primaryBtn} 
            onClick={() => router.push("/auth/login")}
            style={{ width: "100%" }}
          >
            User Sign In
          </button>
        </div>
      </div>
    </div>
  );
}
