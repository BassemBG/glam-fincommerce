"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { API } from "@/lib/api";
import styles from "./page.module.css";

type ProfileForm = {
  brandName: string;
  description: string;
  websiteUrl: string;
  instagramUrl: string;
};

export default function BrandProfilePage() {
  const [form, setForm] = useState<ProfileForm>({
    brandName: "",
    description: "",
    websiteUrl: "",
    instagramUrl: "",
  });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setStatus(null);

    try {
      if (!form.brandName.trim()) {
        throw new Error("Brand name is required.");
      }

      // Call backend to upsert profile brand
      const response = await fetch(API.profileBrands.upsert, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_name: form.brandName.trim(),
          description: form.description.trim() || null,
          brand_website: form.websiteUrl.trim() || null,
          instagram_link: form.instagramUrl.trim() || null,
          brand_logo_url: null,
        }),
        credentials: "include",
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || "Failed to save profile");
      }

      setStatus({ type: "success", message: "Brand profile saved successfully!" });
      // Clear form after success
      setTimeout(() => {
        setForm({
          brandName: "",
          description: "",
          websiteUrl: "",
          instagramUrl: "",
        });
      }, 1500);
    } catch (err: any) {
      setStatus({ type: "error", message: err?.message || "Unable to save profile." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Brand Profile</h1>
        <p>Keep the brand bio, links, and avatar consistent across your advisor flows.</p>
      </header>

      <form className={styles.card} onSubmit={handleSubmit}>
        <div>
          <h2 className={styles.sectionTitle}>Profile</h2>
          <p className={styles.hint}>Instagram-style bio that stays on-brand.</p>
        </div>

        <div className={styles.grid}>
          <div className={styles.field}>
            <div className={styles.labelRow}>Brand name</div>
            <input
              className={styles.input}
              value={form.brandName}
              onChange={(e) => setForm((prev) => ({ ...prev, brandName: e.target.value }))}
              placeholder="House of Aurora"
              required
            />
          </div>

          <div className={styles.field}>
            <div className={styles.labelRow}>Website URL</div>
            <input
              className={styles.input}
              value={form.websiteUrl}
              onChange={(e) => setForm((prev) => ({ ...prev, websiteUrl: e.target.value }))}
              placeholder="https://aura.example"
              type="url"
            />
          </div>

          <div className={styles.field}>
            <div className={styles.labelRow}>Instagram URL</div>
            <input
              className={styles.input}
              value={form.instagramUrl}
              onChange={(e) => setForm((prev) => ({ ...prev, instagramUrl: e.target.value }))}
              placeholder="https://instagram.com/aura"
              type="url"
            />
          </div>
        </div>

        <div className={styles.field}>
          <div className={styles.labelRow}>Short description</div>
          <textarea
            className={styles.textarea}
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
            placeholder="Soft tailoring, sculptural knitwear, and essentials for creative directors."
          />
        </div>

        <div className={styles.actions}>
          {status && (
            <div className={`${styles.status} ${status.type === "error" ? styles.error : ""}`.trim()}>
              {status.message}
            </div>
          )}
          <button type="submit" className={styles.saveButton} disabled={saving}>
            {saving ? "Saving..." : "Save / Update"}
          </button>
        </div>
      </form>
    </div>
  );
}
