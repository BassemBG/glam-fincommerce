"use client";

import { FormEvent, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { API } from "@/lib/api";
import styles from "./page.module.css";
import { useAuthGuard } from "@/lib/useAuthGuard";
import { authFetch, clearToken } from "@/lib/auth";

type ProfileForm = {
  brandName: string;
  description: string;
  websiteUrl: string;
  instagramUrl: string;
  officeEmail: string;  // read-only
  brandType: string;    // read-only
};

export default function BrandProfilePage() {
  useAuthGuard({ role: "brand", redirectTo: "/auth/brand/login" });

  const router = useRouter();
  
  const [form, setForm] = useState<ProfileForm>({
    brandName: "",
    description: "",
    websiteUrl: "",
    instagramUrl: "",
    officeEmail: "",
    brandType: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Load profile data on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        const response = await authFetch(API.profileBrands.me, {
          method: "GET",
        });

        if (!response.ok) {
          const error = await response.text();
          console.error("Profile API error:", response.status, error);
          throw new Error(`${response.status}: ${error || "Failed to load profile"}`);
        }

        const profile = await response.json();
        console.log("Profile loaded:", profile);
        setForm({
          brandName: profile.brand_name || "",
          description: profile.description || "",
          websiteUrl: profile.brand_website || "",
          instagramUrl: profile.instagram_link || "",
          officeEmail: profile.office_email || "",
          brandType: profile.brand_type || "",
        });
      } catch (err: any) {
        console.error("Error loading profile:", err);
        setStatus({ type: "error", message: `Failed to load profile: ${err?.message || "Unknown error"}` });
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setStatus(null);

    try {
      if (!form.brandName.trim()) {
        throw new Error("Brand name is required.");
      }

      // Call backend to update profile brand
      const response = await authFetch(API.profileBrands.meUpdate, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brand_name: form.brandName.trim(),
          description: form.description.trim() || null,
          brand_website: form.websiteUrl.trim() || null,
          instagram_link: form.instagramUrl.trim() || null,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error || "Failed to save profile");
      }

      const updated = await response.json();
      setForm({
        brandName: updated.brand_name || "",
        description: updated.description || "",
        websiteUrl: updated.brand_website || "",
        instagramUrl: updated.instagram_link || "",
        officeEmail: updated.office_email || "",
        brandType: updated.brand_type || "",
      });

      setStatus({ type: "success", message: "Brand profile updated successfully!" });
    } catch (err: any) {
      setStatus({ type: "error", message: err?.message || "Unable to save profile." });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingContainer}>
          <div className={styles.spinner}></div>
          <p>Loading your brand profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Brand Profile</h1>
        <p>Manage your brand information and presence</p>
      </header>

      {/* Brand Identity Card */}
      <div className={styles.profileSection}>
        <div className={styles.avatar}>{form.brandName?.charAt(0) || 'B'}</div>
        <div className={styles.userInfo}>
          <h2>{form.brandName || 'Brand Name'}</h2>
          <p className={styles.emailText}>{form.officeEmail || 'brand@example.com'}</p>
          <span className={styles.brandTypeBadge}>
            {form.brandType === "local" ? "Local Brand" : "International Brand"}
          </span>
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.backButton}
            onClick={() => router.push("/advisor/brands")}
          >
            ← Back
          </button>
          <button
            type="button"
            className={styles.signOutButton}
            onClick={() => {
              clearToken();
              router.replace("/auth/brand/login");
            }}
          >
            Sign Out
          </button>
        </div>
      </div>

      <form className={styles.card} onSubmit={handleSubmit}>
        <div className={styles.sectionHeader}>
          <h3>Brand Information</h3>
          <p>Update your brand details and online presence</p>
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
          <div className={styles.labelRow}>Short description / Bio</div>
          <textarea
            className={styles.textarea}
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
            placeholder="Soft tailoring, sculptural knitwear, and essentials for creative directors."
          />
        </div>

        {status && (
          <div className={`${styles.status} ${status.type === "error" ? styles.error : ""}`.trim()}>
            {status.message}
          </div>
        )}

        <div className={styles.actions}>
          <button type="submit" className={styles.saveButton} disabled={saving}>
            {saving ? (
              <>
                <span className={styles.buttonSpinner}></span>
                Saving...
              </>
            ) : (
              "Save Changes"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
