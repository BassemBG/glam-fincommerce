"use client";

import Link from "next/link";
import { useState } from "react";
import styles from "./page.module.css";
import { API } from "@/lib/api";
import { BrandUploadForm, BrandSubmitPayload } from "./components/BrandUploadForm";
import { BrandPreview, BrandProfile } from "./components/BrandPreview";

export default function BrandAdvisorPage() {
  const [selectedBrand, setSelectedBrand] = useState<BrandProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ingestBrand = async ({ file, url, brandName }: BrandSubmitPayload) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      if (file) formData.append("file", file);
      if (url) formData.append("url", url);
      if (brandName) formData.append("brand_name", brandName);

      const res = await fetch(API.brandIngestion.ingest, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Failed to ingest brand");
      }

      const result: BrandProfile = await res.json();
      setSelectedBrand(result);
    } catch (err: any) {
      setError(err?.message || "Ingestion failed");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.headerBar}>
        <div>
          <h1>Brand Ingestion</h1>
          <p>Upload catalog PDFs or scrape brand websites to extract collections.</p>
        </div>
        <Link href="/advisor/brands/profile" className={styles.profileButton}>
          Brand Profile
        </Link>
      </div>

      {error && (
        <div className={styles.errorBanner}>{error}</div>
      )}

      <div className={styles.stack}>
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Add New Brand</h2>
          <BrandUploadForm onSubmit={ingestBrand} loading={loading} />
        </div>

        <BrandPreview brand={selectedBrand} />
      </div>
    </div>
  );
}
