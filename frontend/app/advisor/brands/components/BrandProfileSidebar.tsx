import React, { ChangeEvent } from "react";
import { BrandProfile } from "./BrandPreview";
import styles from "./BrandProfileSidebar.module.css";

export type BrandProfileForm = {
  brand_name: string;
  website_url: string;
  pdf_files: string[];
  logo_file?: File | null;
  logo_preview?: string | null;
  style_group_count?: number | null;
  product_types: string[];
  price_min?: number | null;
  price_max?: number | null;
  notes?: string;
};

type Props = {
  brand: BrandProfile | null;
  form: BrandProfileForm;
  saving?: boolean;
  onFieldChange: (field: keyof BrandProfileForm, value: any) => void;
  onAddProductType: (value: string) => void;
  onRemoveProductType: (value: string) => void;
  onSave: () => Promise<void> | void;
};

export function BrandProfileSidebar({ brand, form, saving, onFieldChange, onAddProductType, onRemoveProductType, onSave }: Props) {
  const [expanded, setExpanded] = React.useState(true);

  const handleLogoChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFieldChange("logo_file", file);
      const reader = new FileReader();
      reader.onloadend = () => {
        onFieldChange("logo_preview", reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const totalProducts = form.product_types?.length || 0;

  const handleAddTag = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const val = (e.target as HTMLInputElement).value.trim();
      if (val) {
        onAddProductType(val);
        (e.target as HTMLInputElement).value = "";
      }
    }
  };

  return (
    <div className={styles.sidebarCard}>
      <div className={styles.header}>
        <div className={styles.brandRow}>
          <div className={styles.logo}>{(form.brand_name || brand?.brand_name || "B").charAt(0).toUpperCase()}</div>
          <div style={{ flex: 1 }}>
            <h2 className={styles.brandName}>{form.brand_name || brand?.brand_name || "Brand Profile"}</h2>
            {(brand?.source || brand?.created_at) && (
              <span className={styles.source}>
                {brand?.source || "profile"}{brand?.created_at ? ` • ${new Date(brand.created_at).toLocaleDateString()}` : ""}
              </span>
            )}
          </div>
        </div>
        <button
          className={`${styles.toggleBtn} ${expanded ? styles.secondary : ""}`}
          onClick={() => setExpanded(!expanded)}
          type="button"
        >
          {expanded ? "Hide Details" : "View Brand Profile"}
        </button>
      </div>

      {expanded && (
        <div className={styles.body}>
          <div className={styles.field}>
            <label className={styles.label}>Brand Name</label>
            <input
              className={styles.input}
              value={form.brand_name}
              onChange={(e) => onFieldChange("brand_name", e.target.value)}
              placeholder="e.g., Zara"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Uploaded PDF(s)</label>
            <div className={styles.fileList}>
              {(form.pdf_files || []).length === 0 && <span style={{ color: "#94a3b8" }}>No files yet</span>}
              {(form.pdf_files || []).map((f, idx) => (
                <span key={`${f}-${idx}`}>• {f}</span>
              ))}
            </div>
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Brand Website URL</label>
            <input
              className={styles.input}
              value={form.website_url}
              onChange={(e) => onFieldChange("website_url", e.target.value)}
              placeholder="https://brand.com"
              type="url"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Brand Image / Logo</label>
            <input className={styles.fileInput} type="file" accept="image/*" onChange={handleLogoChange} />
            {form.logo_preview && (
              <img src={form.logo_preview} alt="Brand logo preview" className={styles.previewImage} />
            )}
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Collections / Style Groups</label>
            <input
              className={styles.numberInput}
              type="number"
              value={form.style_group_count ?? ""}
              onChange={(e) => onFieldChange("style_group_count", e.target.value === "" ? null : Number(e.target.value))}
              placeholder="Auto-calculated"
              min={0}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Key Product Types</label>
            <input
              className={styles.input}
              placeholder="Type and press Enter"
              onKeyDown={handleAddTag}
            />
            <div className={styles.tagsRow}>
              {(form.product_types || []).map((pt) => (
                <span key={pt} className={styles.tag}>
                  {pt}
                  <button type="button" onClick={() => onRemoveProductType(pt)}>×</button>
                </span>
              ))}
            </div>
          </div>

          <div className={styles.field} style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label className={styles.label}>Price Min</label>
              <input
                className={styles.numberInput}
                type="number"
                value={form.price_min ?? ""}
                onChange={(e) => onFieldChange("price_min", e.target.value === "" ? null : Number(e.target.value))}
                placeholder="e.g., 25"
                min={0}
              />
            </div>
            <div>
              <label className={styles.label}>Price Max</label>
              <input
                className={styles.numberInput}
                type="number"
                value={form.price_max ?? ""}
                onChange={(e) => onFieldChange("price_max", e.target.value === "" ? null : Number(e.target.value))}
                placeholder="e.g., 150"
                min={0}
              />
            </div>
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Notes / Description</label>
            <textarea
              className={styles.textarea}
              value={form.notes || ""}
              onChange={(e) => onFieldChange("notes", e.target.value)}
              placeholder="Any additional notes"
            />
          </div>

          <div className={styles.infoCard}>
            ✓ Ingested to vector store. Update details and save to refresh the profile.
          </div>

          <div className={styles.actions}>
            <button className={styles.saveBtn} type="button" onClick={onSave} disabled={!!saving}>
              {saving ? "Saving..." : "Save / Update"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
