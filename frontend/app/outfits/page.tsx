"use client";

import { useState, useEffect } from 'react';
import styles from './page.module.css';
import TryOnVisualizer from '../../components/TryOnVisualizer';
import { API } from '../../lib/api';

export default function OutfitsPage() {
    const [selectedOutfit, setSelectedOutfit] = useState<any>(null);
    const [outfits, setOutfits] = useState<any[]>([]);
    const [userPhoto, setUserPhoto] = useState<string | null>(null);
    const [showTryOn, setShowTryOn] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [outfitsRes, userRes] = await Promise.all([
                    fetch(API.outfits.list),
                    fetch(API.users.me)
                ]);

                if (outfitsRes.ok) setOutfits(await outfitsRes.json());
                if (userRes.ok) {
                    const userData = await userRes.json();
                    setUserPhoto(userData.full_body_image);
                }
            } catch (err) {
                console.error("Failed to fetch data:", err);
            }
        };
        fetchData();
    }, []);

    const handleTryOn = (outfit: any) => {
        setSelectedOutfit(outfit);
        setShowTryOn(true);
    };

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <h1>Saved Outfits</h1>
                <p className="text-muted">Personalized looks curated for you.</p>
            </header>

            <div className={styles.outfitList}>
                {outfits.length > 0 ? outfits.map((outfit) => (
                    <div key={outfit.id} className={styles.outfitCard}>
                        <div className={styles.outfitHeader}>
                            <div className={styles.outfitInfo}>
                                <h2>{outfit.name || 'AI Curation'}</h2>
                                <span className={styles.vibeTag}>{outfit.vibe} • {outfit.occasion}</span>
                            </div>
                            <div className={styles.scoreBadge}>
                                <span className={styles.scoreValue}>{outfit.score}</span>
                                <span className={styles.scoreLabel}>AI Match</span>
                            </div>
                        </div>
                        <div className={styles.previewGrid}>
                            {/* In a real app, we'd fetch item images here. For now, we'll show count */}
                            <div className={styles.gridPlaceholder}>
                                <span>{outfit.items.length} Pieces</span>
                            </div>
                        </div>
                        <div className={styles.actionRow}>
                            <button
                                className={styles.viewBtn}
                                onClick={() => setSelectedOutfit(outfit)}
                            >
                                Details
                            </button>
                            {userPhoto && (
                                <button
                                    className={styles.tryOnBtn}
                                    onClick={() => handleTryOn(outfit)}
                                >
                                    Try On
                                </button>
                            )}
                        </div>
                    </div>
                )) : (
                    <div className={styles.emptyState}>
                        <p>No outfits saved yet. Ask Ava for inspiration!</p>
                    </div>
                )}
            </div>

            {selectedOutfit && !showTryOn && (
                <div className={styles.overlay} onClick={() => setSelectedOutfit(null)}>
                    <div className={styles.detailCard} onClick={e => e.stopPropagation()}>
                        <button className={styles.closeBtn} onClick={() => setSelectedOutfit(null)}>✕</button>

                        <div className={styles.detailHeader}>
                            <span className={styles.vibeTag}>{selectedOutfit.vibe}</span>
                            <h1>{selectedOutfit.name || 'AI Curation'}</h1>
                            <div className={styles.scoreRow}>
                                <span className={styles.finalScore}>{selectedOutfit.score}</span>
                                <p className="text-muted">AI Stylist Score</p>
                            </div>
                        </div>

                        <div className={styles.detailBody}>
                            <section className={styles.section}>
                                <h3>Stylist Notes</h3>
                                <p className={styles.reasoning}>{selectedOutfit.reasoning}</p>
                            </section>
                        </div>

                        <div className={styles.actionRow}>
                            <button className={styles.primaryBtn} onClick={() => setSelectedOutfit(null)}>
                                Close
                            </button>
                            {userPhoto && (
                                <button className={styles.tryOnBtnLarge} onClick={() => setShowTryOn(true)}>
                                    Virtual Try-On
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {showTryOn && userPhoto && selectedOutfit && (
                <TryOnVisualizer
                    bodyImage={userPhoto}
                    items={selectedOutfit.items.map((it: any) => ({
                        image_url: it.image_url || 'https://images.unsplash.com/photo-1564584217132-2271feaeb3c5?w=200',
                        body_region: it.body_region || 'top'
                    }))}
                    onClose={() => {
                        setShowTryOn(false);
                        setSelectedOutfit(null);
                    }}
                />
            )}
        </div>
    );
}
