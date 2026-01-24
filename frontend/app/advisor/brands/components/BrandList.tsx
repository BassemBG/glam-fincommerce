import React from "react";
import { BrandProfile } from "./BrandPreview";

type Props = {
  brands: BrandProfile[];
  loading?: boolean;
  onSelect?: (brand: BrandProfile) => void;
  onRefresh?: () => void;
};

export function BrandList({ brands, loading, onSelect, onRefresh }: Props) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid #e2e8f0',
      borderRadius: '24px',
      padding: '24px',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.02)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3 style={{ fontSize: '1.25rem', fontFamily: 'var(--font-serif)', margin: 0, color: '#1e293b' }}>
          Ingested Brands
        </h3>
        <button
          type="button"
          onClick={onRefresh}
          style={{
            padding: '8px 16px',
            border: '1px solid #e2e8f0',
            borderRadius: '12px',
            background: '#ffffff',
            color: '#64748b',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--primary)';
            e.currentTarget.style.color = 'var(--primary)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = '#e2e8f0';
            e.currentTarget.style.color = '#64748b';
          }}
        >
          ↻ Refresh
        </button>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: '32px', color: '#94a3b8' }}>
          <div style={{
            width: '32px',
            height: '32px',
            border: '3px solid #f1f5f9',
            borderTopColor: 'var(--primary)',
            borderRadius: '50%',
            margin: '0 auto 12px',
            animation: 'spin 1s linear infinite'
          }} />
          Loading brands...
        </div>
      )}

      {!loading && brands.length === 0 && (
        <p style={{ textAlign: 'center', padding: '32px', color: '#94a3b8', fontSize: '0.95rem' }}>
          No brands ingested yet.
        </p>
      )}

      {!loading && brands.length > 0 && (
        <div style={{ overflowX: 'auto', borderRadius: '16px', border: '1px solid #f1f5f9' }}>
          <table style={{ width: '100%', fontSize: '0.9rem', borderCollapse: 'collapse' }}>
            <thead style={{ background: '#f8fafc', textAlign: 'left', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: '#64748b' }}>
              <tr>
                <th style={{ padding: '12px 16px' }}>Brand</th>
                <th style={{ padding: '12px 16px' }}>Styles</th>
                <th style={{ padding: '12px 16px' }}>Last Updated</th>
                <th style={{ padding: '12px 16px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {brands.map((brand, idx) => (
                <tr key={idx} style={{ borderTop: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '12px 16px', fontWeight: 600, color: '#1e293b' }}>
                    {brand.brand_name || "Unnamed brand"}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#64748b' }}>
                    {brand.style_groups?.length ?? 0}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#94a3b8', fontSize: '0.85rem' }}>
                    {brand.created_at ? new Date(brand.created_at).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <button
                      type="button"
                      onClick={() => onSelect?.(brand)}
                      style={{
                        padding: '6px 16px',
                        background: '#f0fdf4',
                        color: 'var(--primary)',
                        border: 'none',
                        borderRadius: '10px',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--primary)';
                        e.currentTarget.style.color = '#ffffff';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = '#f0fdf4';
                        e.currentTarget.style.color = 'var(--primary)';
                      }}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
