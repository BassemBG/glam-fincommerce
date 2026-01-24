"use client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import TryOnVisualizer from '../components/TryOnVisualizer';
import { API } from '../lib/api';
import { authFetch } from '../lib/auth';
import { useAuthGuard } from '../lib/useAuthGuard';

interface ClothingItem {
  id: string;
  category: string;
  sub_category: string;
  body_region: string;
  image_url: string;
  mask_url: string;
  metadata_json: {
    colors?: string[];
    vibe?: string;
    material?: string;
    description?: string;
    styling_tips?: string;
    season?: string;
  };
}

export default function Home() {
  const router = useRouter();
  const [selectedItem, setSelectedItem] = useState<ClothingItem | null>(null);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedForOutfit, setSelectedForOutfit] = useState<string[]>([]);
  const [isAnimating, setIsAnimating] = useState(false);
  const [showSparks, setShowSparks] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showTryOn, setShowTryOn] = useState(false);
  const [userPhoto, setUserPhoto] = useState<string | null>(null);
  const [items, setItems] = useState<ClothingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthGuard();

  const timerRef = useRef<any>(null);

  useEffect(() => {
    if (!token) return;
    const fetchData = async () => {
      try {
        const [userRes, itemsRes] = await Promise.all([
          authFetch(API.users.me),
          authFetch(API.closet.items)
        ]);

        if (userRes.ok) {
          const userData = await userRes.json();
          setUserPhoto(userData.full_body_image);

          // Redirect to onboarding ONLY if:
          // 1. localStorage flag is set (brand-new account) AND
          // 2. User hasn't actually completed onboarding on server
          const needs = typeof window !== 'undefined' ? localStorage.getItem('needsOnboarding') : null;
          if (needs === '1' && !userData.onboarding_completed) {
            router.push('/onboarding');
            return;
          }

          // If onboarding is already completed, clear the localStorage flag
          if (userData.onboarding_completed && needs === '1') {
            if (typeof window !== 'undefined') {
              localStorage.removeItem('needsOnboarding');
            }
          }
        }

        if (itemsRes.ok) {
          const itemsData = await itemsRes.json();
          setItems(itemsData);
        }
      } catch (err) {
        console.error("Failed to fetch data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const handleTouchStart = (id: string) => {
    if (isSelectionMode) return;
    timerRef.current = setTimeout(() => {
      setIsSelectionMode(true);
      setSelectedForOutfit([id]);
    }, 600);
  };

  const handleTouchEnd = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
  };

  const toggleItemSelection = (id: string) => {
    if (selectedForOutfit.includes(id)) {
      setSelectedForOutfit(prev => prev.filter(i => i !== id));
    } else {
      setSelectedForOutfit(prev => [...prev, id]);
    }
  };

  const handleCreateOutfit = async () => {
    setIsAnimating(true);

    // Build outfit data from selected items
    const selectedItems = items.filter(item => selectedForOutfit.includes(item.id));
    const outfitData = {
      name: `Outfit ${new Date().toLocaleDateString()}`,
      items: selectedForOutfit,
      occasion: "casual",
      vibe: selectedItems[0]?.metadata_json?.vibe || "chic"
    };

    try {
      // Save outfit to backend
      const response = await authFetch(API.outfits.save, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(outfitData)
      });

      if (!response.ok) {
        console.error('Failed to save outfit');
      }
    } catch (err) {
      console.error('Error saving outfit:', err);
    }

    setTimeout(() => {
      setShowSparks(true);
      setTimeout(() => {
        setShowSuccess(true);
        setTimeout(() => {
          setIsAnimating(false);
          setIsSelectionMode(false);
          if (userPhoto) {
            setShowTryOn(true);
          } else {
            setSelectedForOutfit([]);
          }
          setShowSparks(false);
          setShowSuccess(false);
        }, 2500);
      }, 1000);
    }, 2000);
  };

  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to remove this item?')) return;

    setIsDeleting(true);
    try {
      const res = await fetch(API.closet.delete(id), { method: 'DELETE' });
      if (res.ok) {
        setItems(prev => prev.filter(item => item.id !== id));
        setSelectedItem(null);
      } else {
        alert('Failed to delete item');
      }
    } catch (err) {
      console.error(err);
      alert('Error deleting item');
    } finally {
      setIsDeleting(false);
    }
  };

  const handlePinterestConnect = async () => {
    try {
      const oauthResponse = await fetch(`${API.base}/auth/pinterest/login`);
      const oauthData = await oauthResponse.json();
      if (typeof window !== "undefined") {
        window.location.href = oauthData.oauth_url;
      }
    } catch (err: any) {
      console.error("Failed to connect to Pinterest", err);
    }
  };

  // Empty state when no items
  if (!loading && items.length === 0) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyContent}>
          <div className={styles.emptyIcon}>👗</div>
          <h1>Your Closet Awaits</h1>
          <p>
            Start building your digital wardrobe. Add your first piece and let
            our AI stylist help you discover new outfit possibilities.
          </p>
          <div style={{ display: "flex", gap: "12px", justifyContent: "center", flexWrap: "wrap", marginTop: "24px" }}>
            <button
              className={styles.addFirstBtn}
              onClick={() => router.push('/upload')}
            >
              Add Your First Piece
            </button>
          </div>
          <p className={styles.emptyHint}>
            Pro tip: Start with your favorite pieces—the ones you reach for first.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.dashboard} ${isSelectionMode ? styles.selectionActive : ''}`}>
      <header className={styles.header}>
        <div className={styles.headerTop}>
          <h1>{isSelectionMode ? "Select Pieces" : "My Closet"}</h1>
          {isSelectionMode && (
            <button className={styles.cancelBtn} onClick={() => {
              setIsSelectionMode(false);
              setSelectedForOutfit([]);
            }}>Done</button>
          )}
        </div>
        {!isSelectionMode && (
          <div className={styles.stats}>
            <div className={styles.statCard}>
              <span className={styles.statValue}>{items.length}</span>
              <span className={styles.statLabel}>Items</span>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statValue}>0</span>
              <span className={styles.statLabel}>Outfits</span>
            </div>
          </div>
        )}
      </header>

      {!isSelectionMode && (
        <div className={styles.filters}>
          <button className={`${styles.filterBtn} ${styles.active}`}>All</button>
          <button className={styles.filterBtn}>Tops</button>
          <button className={styles.filterBtn}>Bottoms</button>
          <button className={styles.filterBtn}>Dresses</button>
          <button className={styles.filterBtn}>Shoes</button>
        </div>
      )}

      {loading ? (
        <div className={styles.loadingState}>
          <div className={styles.spinner}></div>
          <p>Loading your wardrobe...</p>
        </div>
      ) : (
        <div className={styles.grid}>
          {items.map((item) => (
            <div
              key={item.id}
              className={`${styles.card} ${isSelectionMode ? styles.jiggle : ''} ${selectedForOutfit.includes(item.id) ? styles.selected : ''}`}
              onMouseDown={() => handleTouchStart(item.id)}
              onMouseUp={handleTouchEnd}
              onMouseLeave={handleTouchEnd}
              onTouchStart={() => handleTouchStart(item.id)}
              onTouchEnd={handleTouchEnd}
              onClick={() => {
                if (isSelectionMode) {
                  toggleItemSelection(item.id);
                } else {
                  setSelectedItem(item);
                }
              }}
            >
              <div className={styles.imageWrapper}>
                <img src={item.mask_url || item.image_url} alt={item.sub_category || 'Clothing'} className={styles.image} />
                {isSelectionMode && (
                  <div className={styles.selectionIndicator}>
                    {selectedForOutfit.includes(item.id) ? "✓" : ""}
                  </div>
                )}
              </div>
              <div className={styles.itemInfo}>
                <span className={styles.itemSub}>{item.sub_category || item.category}</span>
                <span className={styles.itemCategory}>{item.body_region.replace('_', ' ')}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {isSelectionMode && selectedForOutfit.length > 0 && (
        <button className={styles.floatingActionBtn} onClick={handleCreateOutfit}>
          Create Outfit ({selectedForOutfit.length})
        </button>
      )}

      {/* Animation Magic */}
      {isAnimating && (
        <div className={styles.animationOverlay}>
          {!showSuccess ? (
            <div className={styles.magicContainer}>
              <div className={`${styles.closetDoor} ${showSparks ? styles.closed : styles.open}`}>
                <div className={styles.doorLeft}></div>
                <div className={styles.doorRight}></div>
              </div>
              <div className={styles.flyingPieces}>
                {selectedForOutfit.map((id, idx) => {
                  const item = items.find(i => i.id === id);
                  return (
                    <div key={id} className={styles.flyingItem} style={{ animationDelay: `${idx * 0.2}s` }}>
                      <img src={item?.image_url} alt="" />
                    </div>
                  );
                })}
              </div>
              {showSparks && (
                <div className={styles.sparkles}>
                  <div className={styles.lightBurst}></div>
                  {[...Array(12)].map((_, i) => (
                    <div key={i} className={styles.spark} style={{ transform: `rotate(${i * 30}deg) translateY(-80px)` }}></div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className={styles.successMessage}>
              <div className={styles.successCheck}>✓</div>
              <h2>Outfit added to closet</h2>
            </div>
          )}
        </div>
      )}

      {selectedItem && !isSelectionMode && (
        <div className={styles.overlay} onClick={() => setSelectedItem(null)}>
          <div className={styles.detailCard} onClick={e => e.stopPropagation()}>
            <button className={styles.closeBtn} onClick={() => setSelectedItem(null)}>✕</button>

            <div className={styles.detailHeader}>
              <span className={styles.vibeTag}>{selectedItem.metadata_json?.vibe || 'Casual'}</span>
              <h1>{selectedItem.sub_category || selectedItem.category}</h1>
              <div className={styles.metaRow}>
                <span className={styles.colorDot} style={{ background: selectedItem.metadata_json?.colors?.[0] || '#ccc' }}></span>
                <p className="text-muted">
                  {selectedItem.metadata_json?.colors?.join(', ') || 'Multi'} • {selectedItem.metadata_json?.material || 'Fabric'}
                </p>
              </div>
            </div>

            <div className={styles.imageReveal}>
              <img src={selectedItem.mask_url || selectedItem.image_url} alt={selectedItem.sub_category} className={styles.largeImage} />
            </div>

            <div className={styles.detailBody}>
              <section className={styles.section}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h3>AI Perspective</h3>
                  <button
                    onClick={(e) => handleDelete(e, selectedItem.id)}
                    disabled={isDeleting}
                    style={{
                      background: 'none',
                      border: '1px solid #ff4444',
                      borderRadius: '4px',
                      padding: '4px 8px',
                      color: '#ff4444',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    {isDeleting ? 'Deleting...' : '🗑️ Delete Item'}
                  </button>
                </div>
                <p className={styles.description}>
                  {selectedItem.metadata_json?.description || 'A versatile piece that can be styled in many ways.'}
                </p>
              </section>

              <div className={styles.tipBox}>
                <strong>How to style it:</strong>
                <p>{selectedItem.metadata_json?.styling_tips || 'Pair with complementary pieces from your closet.'}</p>
              </div>

              <div className={styles.infoGrid}>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>Best Season</span>
                  <span className={styles.infoValue}>{selectedItem.metadata_json?.season || 'All Seasons'}</span>
                </div>
                <div className={styles.infoItem}>
                  <span className={styles.infoLabel}>Body Region</span>
                  <span className={styles.infoValue}>{selectedItem.body_region.replace('_', ' ')}</span>
                </div>
              </div>
            </div>

            <button className={styles.primaryBtn} onClick={() => setSelectedItem(null)}>
              Close
            </button>
          </div>
        </div>
      )}

      {showTryOn && userPhoto && selectedForOutfit.length > 0 && (
        <TryOnVisualizer
          bodyImage={userPhoto}
          items={selectedForOutfit.map(id => {
            const item = items.find(i => i.id === id);
            return { image_url: item?.image_url || '', body_region: item?.body_region || 'top' };
          })}
          onClose={() => {
            setShowTryOn(false);
            setSelectedForOutfit([]);
          }}
        />
      )}
    </div>
  );
}
