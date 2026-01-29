"use client";

import Link from "next/link";
import { useState } from "react";
import styles from "./page.module.css";
import { API } from "@/lib/api";
import { BrandUploadForm, BrandSubmitPayload } from "./components/BrandUploadForm";
import { BrandPreview, BrandProfile } from "./components/BrandPreview";
import { useAuthGuard } from "@/lib/useAuthGuard";
import { authFetch } from "@/lib/auth";

interface Product {
  id: string;
  product_name: string;
  product_description: string;
  azure_image_url?: string;
  image_base64?: string;
  source: string;
}

export default function BrandAdvisorPage() {
  useAuthGuard({ role: "brand", redirectTo: "/auth/brand/login" });
  const [selectedBrand, setSelectedBrand] = useState<BrandProfile | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBrandProducts = async (brandName: string) => {
    try {
      const encodedBrandName = encodeURIComponent(brandName);
      const url = `http://localhost:8000/api/v1/brands/products/${encodedBrandName}`;
      console.log("Fetching from:", url);
      
      const res = await fetch(url);
      console.log("Response status:", res.status);
      
      if (!res.ok) {
        const errorData = await res.text();
        console.error("API error:", errorData);
        throw new Error(`API returned ${res.status}: ${errorData}`);
      }
      
      const data = await res.json();
      console.log("Fetched products:", data);
      setProducts(data.products || []);
    } catch (err: any) {
      console.error("Error fetching products:", err);
      setError(`Could not fetch products: ${err.message}`);
    }
  };

  const ingestBrand = async ({ file, url, brandName }: BrandSubmitPayload) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      if (file) formData.append("file", file);
      if (url) formData.append("url", url);
      if (brandName) formData.append("brand_name", brandName);

      const res = await authFetch(API.brandIngestion.ingest, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Failed to ingest brand");
      }

      const result: BrandProfile = await res.json();
      setSelectedBrand(result);
      
      // Fetch products after successful ingestion
      if (result.brand_name) {
        await fetchBrandProducts(result.brand_name);
      }
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
        
        {/* Ingested products list hidden per request */}
      </div>
    </div>
  );
}
