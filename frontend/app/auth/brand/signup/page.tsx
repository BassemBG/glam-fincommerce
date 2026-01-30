"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import styles from "../../auth.module.css";
import { API } from "@/lib/api";
import { saveToken } from "@/lib/auth";

export default function BrandSignupPage() {
  const router = useRouter();
  const [brandName, setBrandName] = useState("");
  const [officeEmail, setOfficeEmail] = useState("");
  const [brandType, setBrandType] = useState<"local" | "international">("local");
  const [password, setPassword] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(API.brandAuth.signup, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          brand_name: brandName,
          office_email: officeEmail,
          brand_type: brandType,
          password,
          website_url: websiteUrl || null,
          logo_url: null,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Signup failed. Please try again.");
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
            <p className={styles.eyebrow}>Brand Onboarding</p>
            <h1>Create a brand account</h1>
            <p className={styles.muted}>Get started with brand ingestion and profile tools.</p>
          </div>
        </div>

        {error && <div className={styles.toastError}>{error}</div>}

        <form onSubmit={handleSignup} className={styles.form}>
          <label className={styles.label}>Brand Name
            <input
              type="text"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              required
              placeholder="Noon"
            />
          </label>

          <label className={styles.label}>Office Email
            <input
              type="email"
              value={officeEmail}
              onChange={(e) => setOfficeEmail(e.target.value)}
              required
              placeholder="brand@company.com"
            />
          </label>

          <div className={styles.label}>
            <span style={{ marginBottom: '10px', display: 'block' }}>Brand Type</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <button
                type="button"
                onClick={() => setBrandType("local")}
                style={{
                  padding: '14px 16px',
                  border: brandType === "local" ? '2px solid var(--primary)' : '1.5px solid #e2e8f0',
                  borderRadius: '12px',
                  background: brandType === "local" ? 'var(--primary-50)' : '#ffffff',
                  color: brandType === "local" ? 'var(--primary-700)' : '#64748b',
                  fontSize: '0.95rem',
                  fontWeight: brandType === "local" ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  position: 'relative'
                }}
                onMouseEnter={(e) => {
                  if (brandType !== "local") {
                    e.currentTarget.style.borderColor = 'var(--primary-100)';
                    e.currentTarget.style.background = '#f8fafc';
                  }
                }}
                onMouseLeave={(e) => {
                  if (brandType !== "local") {
                    e.currentTarget.style.borderColor = '#e2e8f0';
                    e.currentTarget.style.background = '#ffffff';
                  }
                }}
              >
                {brandType === "local" && (
                  <span style={{ position: 'absolute', top: '8px', right: '8px', fontSize: '1rem' }}>✓</span>
                )}
                🏪 Local brand
              </button>
              <button
                type="button"
                onClick={() => setBrandType("international")}
                style={{
                  padding: '14px 16px',
                  border: brandType === "international" ? '2px solid var(--primary)' : '1.5px solid #e2e8f0',
                  borderRadius: '12px',
                  background: brandType === "international" ? 'var(--primary-50)' : '#ffffff',
                  color: brandType === "international" ? 'var(--primary-700)' : '#64748b',
                  fontSize: '0.95rem',
                  fontWeight: brandType === "international" ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  position: 'relative'
                }}
                onMouseEnter={(e) => {
                  if (brandType !== "international") {
                    e.currentTarget.style.borderColor = 'var(--primary-100)';
                    e.currentTarget.style.background = '#f8fafc';
                  }
                }}
                onMouseLeave={(e) => {
                  if (brandType !== "international") {
                    e.currentTarget.style.borderColor = '#e2e8f0';
                    e.currentTarget.style.background = '#ffffff';
                  }
                }}
              >
                {brandType === "international" && (
                  <span style={{ position: 'absolute', top: '8px', right: '8px', fontSize: '1rem' }}>✓</span>
                )}
                🌍 International
              </button>
            </div>
          </div>

          <label className={styles.label}>Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </label>

          <label className={styles.label}>Website URL (optional)
            <input
              type="url"
              value={websiteUrl}
              onChange={(e) => setWebsiteUrl(e.target.value)}
              placeholder="https://brand.com"
            />
          </label>

          <button type="submit" className={styles.primaryBtn} disabled={loading}>
            {loading ? "Creating account..." : "Create Brand Account"}
          </button>
        </form>

        <p className={styles.footerText}>
          Already have a brand account? <button type="button" className={styles.linkBtn} onClick={() => router.push("/auth/brand/login")}>Sign in</button>
        </p>
      </div>
    </div>
  );
}
