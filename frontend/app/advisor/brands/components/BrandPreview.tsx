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
        padding: '48px 24px',
        textAlign: 'center',
        border: '2px dashed #cbd5e1',
        borderRadius: '24px',
        background: '#f8fafc',
        color: '#94a3b8',
        fontSize: '0.95rem'
      }}>
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto' }}>
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
        </svg>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{
        background: 'var(--surface)',
        border: '1px solid #e2e8f0',
        borderRadius: '24px',
        padding: '24px',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.02)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.75rem', fontFamily: 'var(--font-serif)', margin: '0 0 8px 0', color: '#1e293b' }}>
              {brand.brand_name || "Unnamed brand"}
            </h2>
            {brand.source && (
              <p style={{ fontSize: '0.85rem', color: '#94a3b8', margin: 0 }}>Source: {brand.source}</p>
            )}
          </div>
          {brand.created_at && (
            <span style={{ 
              background: '#f1f5f9', 
              padding: '6px 12px', 
              borderRadius: '20px', 
              fontSize: '0.8rem', 
              color: '#64748b',
              whiteSpace: 'nowrap'
            }}>
              {new Date(brand.created_at).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
        {brand.style_groups?.length === 0 && !brand.products?.length && (
          <div style={{ 
            padding: '32px', 
            textAlign: 'center', 
            border: '1px solid #e2e8f0', 
            borderRadius: '16px', 
            background: '#ffffff',
            color: '#94a3b8'
          }}>
            No data extracted.
          </div>
        )}

        {/* Display Style Groups (from file ingestion) */}
        {brand.style_groups?.map((style, idx) => (
          <div key={idx} style={{
            background: 'var(--surface)',
            border: '1px solid #e2e8f0',
            borderRadius: '20px',
            padding: '20px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.03)',
            transition: 'all 0.3s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-4px)';
            e.currentTarget.style.boxShadow = '0 12px 24px rgba(0, 0, 0, 0.06)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.03)';
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h3 style={{ fontSize: '1.1rem', fontFamily: 'var(--font-serif)', margin: 0, color: '#1e293b' }}>
                {style.style_name || "Style"}
              </h3>
              {style.sustainability_score != null && (
                <span style={{ fontSize: '0.75rem', color: 'var(--primary)', fontWeight: 600 }}>
                  ♻ {style.sustainability_score}
                </span>
              )}
            </div>

            {style.product_types?.length ? (
              <p style={{ fontSize: '0.9rem', color: '#475569', margin: '0 0 8px 0', lineHeight: 1.5 }}>
                {style.product_types.join(", ")}
              </p>
            ) : (
              <p style={{ fontSize: '0.9rem', color: '#94a3b8', margin: '0 0 8px 0' }}>No product types found.</p>
            )}

            {style.price_range && (style.price_range.min_price != null || style.price_range.max_price != null) && (
              <p style={{ fontSize: '0.85rem', color: '#64748b', margin: '8px 0' }}>
                💰 {style.price_range.min_price ?? "?"} – {style.price_range.max_price ?? "?"} {style.price_range.currency || ""}
              </p>
            )}

            {style.aesthetic_keywords?.length ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '12px' }}>
                {style.aesthetic_keywords.map((kw, i) => (
                  <span
                    key={`${kw}-${i}`}
                    style={{
                      background: '#f0fdf4',
                      color: 'var(--primary)',
                      padding: '4px 12px',
                      borderRadius: '12px',
                      fontSize: '0.75rem',
                      fontWeight: 600
                    }}
                  >
                    {kw}
                  </span>
                ))}
              </div>
            ) : null}

            {style.target_demographic && (
              <p style={{ marginTop: '12px', fontSize: '0.8rem', color: '#94a3b8' }}>
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
            borderRadius: '20px',
            padding: '20px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.03)',
            transition: 'all 0.3s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-4px)';
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
                  height: '180px',
                  objectFit: 'cover',
                  borderRadius: '12px',
                  marginBottom: '12px'
                }}
              />
            )}
            <h3 style={{ fontSize: '1.1rem', fontFamily: 'var(--font-serif)', margin: '0 0 8px 0', color: '#1e293b' }}>
              {product.product_name}
            </h3>
            <p style={{ fontSize: '0.9rem', color: '#475569', margin: 0, lineHeight: 1.5 }}>
              {product.product_description?.substring(0, 120)}...
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
