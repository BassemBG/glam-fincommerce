"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "../auth.module.css";
import { API } from "@/lib/api";
import { saveToken } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(API.auth.signup, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Signup failed. Please try again.");
      }

      const data = await res.json();
      saveToken(data.access_token);
      // Mark that this brand-new account should go through onboarding once
      if (typeof window !== 'undefined') {
        localStorage.setItem('needsOnboarding', '1');
      }
      router.replace("/onboarding");
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
            <p className={styles.eyebrow}>Welcome</p>
            <h1>Create your account</h1>
            <p className={styles.muted}>Sign up to start curating your digital wardrobe.</p>
          </div>
        </div>

        {error && <div className={styles.toastError}>{error}</div>}

        <form onSubmit={handleSignup} className={styles.form}>            
          <label className={styles.label}>Full Name
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              placeholder="Ava Ward"
            />
          </label>

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
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p className={styles.footerText}>
          Already have an account? <button type="button" className={styles.linkBtn} onClick={() => router.push("/auth/login")}>Sign in</button>
        </p>
      </div>
    </div>
  );
}
