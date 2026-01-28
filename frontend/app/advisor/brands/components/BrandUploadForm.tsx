"use client";

import { useState, FormEvent } from "react";

export type BrandSubmitPayload = {
  file?: File | null;
  url?: string;
  brandName?: string;
};

type Props = {
  onSubmit: (payload: BrandSubmitPayload) => Promise<void>;
  loading?: boolean;
};

export function BrandUploadForm({ onSubmit, loading }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [brandName, setBrandName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!file && !url.trim()) {
      setError("Provide a PDF file or a website URL.");
      return;
    }

    try {
      await onSubmit({ file, url: url.trim() || undefined, brandName: brandName.trim() || undefined });
      // Clear form fields after successful ingestion
      setFile(null);
      setUrl("");
      setBrandName("");
    } catch (err: any) {
      setError(err?.message || "Failed to submit");
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'grid', gap: '20px', gridTemplateColumns: '1fr' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#334155' }}>Upload brand PDF</span>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            style={{ 
              fontSize: '0.9rem', 
              color: '#475569',
              padding: '10px',
              border: '1px solid #cbd5e1',
              borderRadius: '12px',
              background: '#f8fafc'
            }}
          />
          {file && <span style={{ fontSize: '0.85rem', color: '#22c55e', fontWeight: 600 }}>✓ Selected: {file.name}</span>}
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#334155' }}>Brand website URL</span>
          <input
            type="url"
            placeholder="https://brand.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            style={{
              padding: '13px 16px',
              border: '1px solid #cbd5e1',
              borderRadius: '12px',
              fontSize: '0.95rem',
              color: '#1e293b',
              background: '#ffffff',
              transition: 'all 0.2s'
            }}
            onFocus={(e) => { e.target.style.borderColor = '#93c5fd'; e.target.style.boxShadow = '0 0 0 3px rgba(147, 197, 253, 0.1)'; }}
            onBlur={(e) => { e.target.style.borderColor = '#cbd5e1'; e.target.style.boxShadow = 'none'; }}
          />
          <p style={{ fontSize: '0.8rem', color: '#64748b' }}>We will scrape the site if provided.</p>
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#334155' }}>Brand name (optional)</span>
          <input
            type="text"
            placeholder="e.g., Zara"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            style={{
              padding: '13px 16px',
              border: '1px solid #cbd5e1',
              borderRadius: '12px',
              fontSize: '0.95rem',
              color: '#1e293b',
              background: '#ffffff',
              transition: 'all 0.2s'
            }}
            onFocus={(e) => { e.target.style.borderColor = '#93c5fd'; e.target.style.boxShadow = '0 0 0 3px rgba(147, 197, 253, 0.1)'; }}
            onBlur={(e) => { e.target.style.borderColor = '#cbd5e1'; e.target.style.boxShadow = 'none'; }}
          />
          <p style={{ fontSize: '0.8rem', color: '#64748b' }}>Used to label the collection if the PDF/URL lacks a name.</p>
        </label>
      </div>

      {error && (
        <div style={{ 
          padding: '12px 16px', 
          background: '#fef2f2', 
          border: '1px solid #fecaca', 
          borderRadius: '12px', 
          color: '#dc2626', 
          fontSize: '0.9rem' 
        }}>
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        style={{
          width: '100%',
          padding: '15px',
          background: loading ? '#86efac' : '#22c55e',
          color: '#ffffff',
          border: 'none',
          borderRadius: '14px',
          fontSize: '0.98rem',
          fontWeight: 600,
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.25s ease',
          boxShadow: loading ? 'none' : '0 3px 10px rgba(34, 197, 94, 0.25)'
        }}
        onMouseEnter={(e) => {
          if (!loading) {
            e.currentTarget.style.transform = 'translateY(-1px)';
            e.currentTarget.style.boxShadow = '0 6px 16px rgba(34, 197, 94, 0.3)';
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = '0 3px 10px rgba(34, 197, 94, 0.25)';
        }}
      >
        {loading ? "Processing..." : "Ingest Brand"}
      </button>
    </form>
  );
}
