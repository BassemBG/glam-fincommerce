"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import styles from "./page.module.css";

type ProfileForm = {
  brandName: string;
  description: string;
  websiteUrl: string;
  instagramUrl: string;
  logoFile: File | null;
  logoPreview: string | null;
};

export default function BrandProfilePage() {
  const [form, setForm] = useState<ProfileForm>({
    brandName: "",
    description: "",
    websiteUrl: "",
    instagramUrl: "",
    logoFile: null,
    logoPreview: null,
  });
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    return () => {
      if (form.logoPreview) URL.revokeObjectURL(form.logoPreview);
    };
  }, [form.logoPreview]);

  const handleLogoChange = (file: File | null) => {
    if (form.logoPreview) URL.revokeObjectURL(form.logoPreview);
    if (!file) {
      setForm((prev) => ({ ...prev, logoFile: null, logoPreview: null }));
      return;
    }
    const preview = URL.createObjectURL(file);
    setForm((prev) => ({ ...prev, logoFile: file, logoPreview: preview }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setStatus(null);

    try {
      // Local-only save. Wire to backend profile endpoint when available.
      await new Promise((resolve) => setTimeout(resolve, 400));
      setStatus({ type: "success", message: "Profile saved locally. Connect to backend when ready." });
    } catch (err: any) {
      setStatus({ type: "error", message: err?.message || "Unable to save right now." });
    } finally {
      setSaving(false);
    }
  };

  const initials = useMemo(() => {
    return (form.brandName || "Brand").slice(0, 2).toUpperCase();
  }, [form.brandName]);

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

        <div className={styles.logoUpload}>
          <div className={styles.logoPreview}>
            {form.logoPreview ? <img src={form.logoPreview} alt="Brand logo preview" /> : initials}
          </div>
          <label className={styles.uploadButton}>
            <input
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => handleLogoChange(e.target.files?.[0] || null)}
            />
            Upload logo
          </label>
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
