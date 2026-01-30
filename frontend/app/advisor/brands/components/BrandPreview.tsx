import React from "react";

export type BrandStyleGroup = {
  style_name?: string | null;
  product_types?: string[];
  price_range?: {
    min_price?: number | null;
    max_price?: number | null;
    currency?: string | null;
  } | null;
  aesthetic_keywords?: string[];
  target_demographic?: string | null;
  sustainability_score?: number | null;
};

export type BrandProfile = {
  brand_name?: string | null;
  style_groups: BrandStyleGroup[];
  source?: string;
  created_at?: string;
  products?: Array<{
    id: string;
    product_name: string;
    product_description: string;
    image_base64?: string | null;
    azure_image_url?: string | null;
  }>;
};

type Props = {
  brand: BrandProfile | null;
};

export function BrandPreview({ brand }: Props) {
  if (!brand) {
    return (
      <div style={{
        padding: '32px 16px',
        textAlign: 'center',
        border: '2px dashed #cbd5e1',
        borderRadius: '16px',
        background: '#f8fafc',
        color: '#94a3b8',
        fontSize: '0.85rem'
      }}>
        <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto' }}>
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
        </svg>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div style={{
        background: 'var(--surface)',
        border: '1px solid #e2e8f0',
        borderRadius: '16px',
        padding: '16px',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.02)'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', alignItems: 'flex-start', gap: '12px' }}>
          <div style={{ width: '100%' }}>
            <h2 style={{ fontSize: '1.3rem', fontFamily: 'var(--font-serif)', margin: '0 0 4px 0', color: '#1e293b' }}>
              {brand.brand_name || "Unnamed brand"}
            </h2>
            {brand.source && (
              <p style={{ fontSize: '0.75rem', color: '#94a3b8', margin: 0 }}>Source: {brand.source}</p>
            )}
          </div>
          {brand.created_at && (
            <span style={{ 
              background: '#f1f5f9', 
              padding: '4px 8px', 
              borderRadius: '16px', 
              fontSize: '0.7rem', 
              color: '#64748b',
              whiteSpace: 'nowrap'
            }}>
              {new Date(brand.created_at).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gap: '12px', gridTemplateColumns: '1fr' }}>
        {brand.style_groups?.length === 0 && !brand.products?.length && (
          <div style={{ 
            padding: '24px 16px', 
            textAlign: 'center', 
            border: '1px solid #e2e8f0', 
            borderRadius: '12px', 
            background: '#ffffff',
            color: '#94a3b8',
            fontSize: '0.85rem'
          }}>
            No data extracted.
          </div>
        )}

        {/* Display Style Groups (from file ingestion) */}
        {brand.style_groups?.map((style, idx) => (
          <div key={idx} style={{
            background: 'var(--surface)',
            border: '1px solid #e2e8f0',
            borderRadius: '14px',
            padding: '14px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.03)',
            transition: 'all 0.3s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 12px 24px rgba(0, 0, 0, 0.06)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.03)';
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px', gap: '8px' }}>
              <h3 style={{ fontSize: '0.95rem', fontFamily: 'var(--font-serif)', margin: 0, color: '#1e293b' }}>
                {style.style_name || "Style"}
              </h3>
              {style.sustainability_score != null && (
                <span style={{ fontSize: '0.7rem', color: 'var(--primary)', fontWeight: 600, whiteSpace: 'nowrap' }}>
                  ♻ {style.sustainability_score}
                </span>
              )}
            </div>

            {style.product_types?.length ? (
              <p style={{ fontSize: '0.8rem', color: '#475569', margin: '0 0 6px 0', lineHeight: 1.4 }}>
                {style.product_types.join(", ")}
              </p>
            ) : (
              <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0 0 6px 0' }}>No product types found.</p>
            )}

            {style.price_range && (style.price_range.min_price != null || style.price_range.max_price != null) && (
              <p style={{ fontSize: '0.75rem', color: '#64748b', margin: '6px 0' }}>
                💰 {style.price_range.min_price ?? "?"} – {style.price_range.max_price ?? "?"} {style.price_range.currency || ""}
              </p>
            )}

            {style.aesthetic_keywords?.length ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '8px' }}>
                {style.aesthetic_keywords.map((kw, i) => (
                  <span
                    key={`${kw}-${i}`}
                    style={{
                      background: 'var(--primary-50)',
                      color: 'var(--primary)',
                      padding: '3px 8px',
                      borderRadius: '8px',
                      fontSize: '0.7rem',
                      fontWeight: 600
                    }}
                  >
                    {kw}
                  </span>
                ))}
              </div>
            ) : null}

            {style.target_demographic && (
              <p style={{ marginTop: '8px', fontSize: '0.75rem', color: '#94a3b8' }}>
                Target: {style.target_demographic}
              </p>
            )}
          </div>
        ))}

        {/* Display Products (from URL ingestion) */}
        {brand.products?.map((product) => (
          <div key={product.id} style={{
            background: 'var(--surface)',
            border: '1px solid #e2e8f0',
            borderRadius: '14px',
            padding: '12px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.03)',
            transition: 'all 0.3s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 12px 24px rgba(0, 0, 0, 0.06)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.03)';
          }}>
            {(product.azure_image_url || product.image_base64) && (
              <img
                src={product.azure_image_url || `data:image/jpeg;base64,${product.image_base64}`}
                alt={product.product_name}
                style={{
                  width: '100%',
                  height: '140px',
                  objectFit: 'cover',
                  borderRadius: '10px',
                  marginBottom: '10px'
                }}
              />
            )}
            <h3 style={{ fontSize: '0.95rem', fontFamily: 'var(--font-serif)', margin: '0 0 6px 0', color: '#1e293b' }}>
              {product.product_name}
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#475569', margin: 0, lineHeight: 1.4 }}>
              {product.product_description?.substring(0, 100)}...
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
