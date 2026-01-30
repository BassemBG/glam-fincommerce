
"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import { API } from '../../lib/api';
import { authFetch } from '../../lib/auth';
import { useAuthGuard } from '../../lib/useAuthGuard';

interface Product {
    id: string;
    brand_name: string;
    product_name: string;
    product_description: string;
    price: string | null;
    azure_image_url: string;
    personal_score?: number;
    source?: string;
}

export default function BrandsExplore() {
    const router = useRouter();
    const token = useAuthGuard();
    const [products, setProducts] = useState<Product[]>([]);
    const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
    const [loading, setLoading] = useState(true);
    const [userInfo, setUserInfo] = useState<any>(null);
    const [topVibe, setTopVibe] = useState<string | null>(null);
    const [addingToCloset, setAddingToCloset] = useState(false);

    useEffect(() => {
        if (!token) return;

        const fetchExplore = async () => {
            try {
                const userRes = await authFetch(API.users.me);
                let userId = undefined;
                if (userRes.ok) {
                    const userData = await userRes.json();
                    setUserInfo(userData);
                    userId = userData.id;
                }

                const exploreRes = await authFetch(API.brandIngestion.explore(userId));
                if (exploreRes.ok) {
                    const data = await exploreRes.json();
                    setProducts(data.products || []);
                    setTopVibe(data.top_vibe || null);
                }
            } catch (err) {
                console.error("Failed to fetch brand exploration:", err);
            } finally {
                setLoading(false);
            }
        };

        fetchExplore();
    }, [token]);

    const handleProductClick = async (product: Product) => {
        if (!userInfo?.id) return;
        if (window.navigator?.vibrate) window.navigator.vibrate(10);
        setSelectedProduct(product);

        try {
            await authFetch(API.brandIngestion.recordClick(userInfo.id), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_id: product.id,
                    brand_name: product.brand_name,
                    source: 'explore'
                })
            });
        } catch (err) {
            console.error("Failed to record click:", err);
        }
    };

    const isInternalOrPlaceholder = (url?: string) => {
        if (!url) return true;
        if (url === 'website') return true;
        return !url.startsWith('http');
    };

    const [redirecting, setRedirecting] = useState<string | null>(null);

    const handleBuyNow = async (product: Product) => {
        if (!userInfo?.id) return;

        setRedirecting(product.brand_name);

        // Record the purchase intent
        try {
            await authFetch(API.brandIngestion.recordPurchaseClick(userInfo.id), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_id: product.id,
                    brand_name: product.brand_name,
                    source: 'explore'
                })
            });
        } catch (err) {
            console.error("Failed to record purchase click:", err);
        }

        // Wait a brief moment for the premium UX feel
        setTimeout(() => {
            if (!isInternalOrPlaceholder(product.source)) {
                window.open(product.source, '_blank');
            } else {
                const query = encodeURIComponent(`${product.brand_name} ${product.product_name}`);
                window.open(`https://www.google.com/search?q=${query}`, '_blank');
            }
            setRedirecting(null);
        }, 1200);
    };

    const handleAddToCloset = async (product: Product) => {
        setAddingToCloset(true);
        try {
            const response = await authFetch(API.clothing.ingest, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    imageUrl: product.azure_image_url,
                    brand_name: product.brand_name,
                    product_name: product.product_name,
                    product_description: product.product_description,
                    price: product.price
                })
            });

            if (response.ok) {
                alert("Added to your digital closet!");
                setSelectedProduct(null);
            } else {
                alert("Failed to add to closet.");
            }
        } catch (err) {
            console.error("Error adding to closet:", err);
        } finally {
            setAddingToCloset(false);
        }
    };

    if (loading) {
        return (
            <div className={styles.container}>
                <div className={styles.loading}>
                    <div className={styles.spinner}></div>
                    <p>Curating your personalized boutique...</p>
                </div>
            </div>
        );
    }

    return (
        <main className={styles.container}>
            <header className={styles.header}>
                <h1>Curated Shop</h1>
                <p>Pieces that reflect your {topVibe || 'unique'} vision.</p>
            </header>

            <div className={styles.filters}>
                <button className={`${styles.filterBtn} ${styles.active}`}>All</button>
                <button className={styles.filterBtn}>For You</button>
                <button className={styles.filterBtn}>Trending</button>
                <button className={styles.filterBtn}>New In</button>
            </div>

            <section className={styles.grid}>
                {products.map((product) => (
                    <div
                        key={product.id}
                        className={styles.card}
                        onClick={() => handleProductClick(product)}
                    >
                        <div className={styles.imageWrapper}>
                            <img
                                src={product.azure_image_url || '/placeholder-product.jpg'}
                                alt={product.product_name}
                                className={styles.image}
                            />
                            {product.personal_score !== undefined && product.personal_score > 0.5 && (
                                <div className={styles.matchBadge}>
                                    {Math.round(product.personal_score * 100)}% Match
                                </div>
                            )}
                        </div>

                        <div className={styles.cardContent}>
                            <span className={styles.brandName}>{product.brand_name}</span>
                            <h3 className={styles.productName}>{product.product_name}</h3>
                            <div className={styles.price}>
                                {product.price || 'Contact'}
                            </div>
                        </div>
                    </div>
                ))}
            </section>

            {/* Bottom Sheet Modal */}
            {selectedProduct && (
                <div className={styles.overlay} onClick={() => setSelectedProduct(null)}>
                    <div className={styles.detailCard} onClick={e => e.stopPropagation()}>
                        <div className={styles.sheetHandle}></div>
                        <button className={styles.closeBtn} onClick={() => setSelectedProduct(null)}>✕</button>

                        <div className={styles.modalHeader}>
                            <span className={styles.modalBrand}>{selectedProduct.brand_name}</span>
                            <h1 className={styles.modalTitle}>{selectedProduct.product_name}</h1>
                            <div className={styles.modalPrice}>{selectedProduct.price || 'Pricing on Request'}</div>
                        </div>

                        <div className={styles.imageReveal}>
                            <img src={selectedProduct.azure_image_url} alt={selectedProduct.product_name} className={styles.largeImage} />
                        </div>

                        <div className={styles.dnaAnalysis}>
                            <h4>AI Style Match</h4>
                            <p>
                                This piece matches your **{topVibe}** vibe.
                                It complements the silhouettes and colors we've seen in your wardrobe.
                            </p>
                        </div>

                        <p className={styles.description}>
                            {selectedProduct.product_description || "A masterfully crafted piece designed for versatility and timeless appeal."}
                        </p>

                        <div className={styles.actionRow}>
                            <button
                                className={styles.buyNowBtn}
                                onClick={() => handleBuyNow(selectedProduct)}
                            >
                                View on Brand Site
                            </button>
                            <button
                                className={styles.addToClosetBtn}
                                onClick={() => handleAddToCloset(selectedProduct)}
                                disabled={addingToCloset}
                            >
                                {addingToCloset ? 'Adding...' : 'Add to Closet'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Redirection Overlay */}
            {redirecting && (
                <div className={styles.redirectOverlay}>
                    <div className={styles.redirectContent}>
                        <div className={styles.spinner}></div>
                        <p>Taking you to <strong>{redirecting}</strong>...</p>
                        <span>Securely connecting to brand boutique</span>
                    </div>
                </div>
            )}

            {products.length === 0 && (
                <div style={{ textAlign: 'center', padding: '100px 0', color: '#94a3b8' }}>
                    <h3>Checking for drops...</h3>
                </div>
            )}
        </main>
    );
}
