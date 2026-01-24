"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "../auth.module.css";
import { API } from "@/lib/api";
import { saveToken } from "@/lib/auth";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fromSignup = searchParams.get("from") === "signup";

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const body = new URLSearchParams();
      body.append("username", email);
      body.append("password", password);

      const res = await fetch(API.auth.login, {
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
      saveToken(data.access_token);
      router.replace("/");
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
            <p className={styles.eyebrow}>Access</p>
            <h1>Sign in to your closet</h1>
            <p className={styles.muted}>Securely continue to your outfits and wardrobe.</p>
          </div>
        </div>

        {fromSignup && (
          <div className={styles.toastSuccess}>Account created. Please sign in.</div>
        )}

        {error && <div className={styles.toastError}>{error}</div>}

        <form onSubmit={handleLogin} className={styles.form}>
          <label className={styles.label}>Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
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
          New here? <button type="button" className={styles.linkBtn} onClick={() => router.push("/auth/signup")}>Create account</button>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className={styles.shell}><div className={styles.card}>Loading...</div></div>}>
      <LoginForm />
    </Suspense>
  );
}
