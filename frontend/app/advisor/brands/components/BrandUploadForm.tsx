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
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'grid', gap: '14px', gridTemplateColumns: '1fr' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>Upload brand PDF</span>
          <div style={{ position: 'relative' }}>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              style={{ 
                fontSize: '0.85rem', 
                color: '#475569',
                padding: '12px 14px',
                border: '2px dashed var(--primary-100)',
                borderRadius: '12px',
                background: 'var(--primary-50)',
                cursor: 'pointer',
                width: '100%',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--primary)';
                e.currentTarget.style.background = 'var(--primary-100)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--primary-100)';
                e.currentTarget.style.background = 'var(--primary-50)';
              }}
            />
          </div>
          {file && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px', 
              padding: '10px 12px', 
              background: 'var(--primary-50)', 
              border: '1px solid var(--primary-100)', 
              borderRadius: '10px' 
            }}>
              <span style={{ fontSize: '1.2rem' }}>📄</span>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--primary-700)', fontWeight: 600, margin: 0 }}>{file.name}</p>
                <p style={{ fontSize: '0.7rem', color: '#64748b', margin: '2px 0 0 0' }}>{(file.size / 1024).toFixed(1)} KB</p>
              </div>
              <button
                type="button"
                onClick={() => setFile(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '1.2rem',
                  padding: '4px',
                  lineHeight: 1
                }}
              >×</button>
            </div>
          )}
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>Brand website URL</span>
          <input
            type="url"
            placeholder="https://brand.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            style={{
              padding: '10px 12px',
              border: '1px solid #cbd5e1',
              borderRadius: '10px',
              fontSize: '0.9rem',
              color: '#1e293b',
              background: '#ffffff',
              transition: 'all 0.2s'
            }}
            onFocus={(e) => { e.target.style.borderColor = 'var(--primary)'; e.target.style.boxShadow = '0 0 0 3px rgba(124, 58, 237, 0.1)'; }}
            onBlur={(e) => { e.target.style.borderColor = '#cbd5e1'; e.target.style.boxShadow = 'none'; }}
          />
          <p style={{ fontSize: '0.75rem', color: '#64748b', margin: 0 }}>We will scrape the site if provided.</p>
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>Brand name (optional)</span>
          <input
            type="text"
            placeholder="e.g., Zara"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            style={{
              padding: '10px 12px',
              border: '1px solid #cbd5e1',
              borderRadius: '10px',
              fontSize: '0.9rem',
              color: '#1e293b',
              background: '#ffffff',
              transition: 'all 0.2s'
            }}
            onFocus={(e) => { e.target.style.borderColor = 'var(--primary)'; e.target.style.boxShadow = '0 0 0 3px rgba(124, 58, 237, 0.1)'; }}
            onBlur={(e) => { e.target.style.borderColor = '#cbd5e1'; e.target.style.boxShadow = 'none'; }}
          />
          <p style={{ fontSize: '0.75rem', color: '#64748b', margin: 0 }}>Used to label the collection if the PDF/URL lacks a name.</p>
        </label>
      </div>

      {error && (
        <div style={{ 
          padding: '10px 12px', 
          background: '#fef2f2', 
          border: '1px solid #fecaca', 
          borderRadius: '10px', 
          color: '#dc2626', 
          fontSize: '0.8rem' 
        }}>
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        style={{
          width: '100%',
          padding: '16px 24px',
          background: loading 
            ? 'linear-gradient(135deg, var(--primary-100) 0%, var(--primary-50) 100%)' 
            : 'linear-gradient(135deg, var(--primary) 0%, var(--primary-700) 100%)',
          color: loading ? '#94a3b8' : '#ffffff',
          border: 'none',
          borderRadius: '14px',
          fontSize: '1rem',
          fontWeight: 700,
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: loading ? 'none' : '0 8px 20px rgba(124, 58, 237, 0.35)',
          position: 'relative',
          overflow: 'hidden'
        }}
        onMouseEnter={(e) => {
          if (!loading) {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 12px 28px rgba(124, 58, 237, 0.45)';
          }
        }}
        onMouseLeave={(e) => {
          if (!loading) {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 8px 20px rgba(124, 58, 237, 0.35)';
          }
        }}
        onMouseDown={(e) => {
          if (!loading) {
            e.currentTarget.style.transform = 'translateY(0)';
          }
        }}
      >
        {loading ? (
          <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <span style={{ 
              width: '16px', 
              height: '16px', 
              border: '2px solid #94a3b8',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }}></span>
            Processing...
          </span>
        ) : (
          <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.2rem' }}>✨</span>
            Ingest Brand
          </span>
        )}
      </button>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </form>
  );
}
