"use client";

import { useEffect, useState } from 'react';
import styles from './StyleDNA.module.css';
import { API } from '../lib/api';
import { authFetch } from '../lib/auth';

interface StyleDNAData {
    vibes: Record<string, number>;
    colors: string[];
    top_categories: { item: string; count: number }[];
    total_items: number;
}

export default function StyleDNA() {
    const [data, setData] = useState<StyleDNAData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDNA = async () => {
            try {
                const res = await authFetch(API.stylist.styleDna);
                if (res.ok) {
                    const dna = await res.json();
                    setData(dna);
                }
            } catch (err) {
                console.error("Failed to fetch Style DNA:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchDNA();
    }, []);

    if (loading) return (
        <div className={styles.loadingCard}>
            <div className={styles.shimmerLine} style={{ width: '40%' }}></div>
            <div className={styles.shimmerCircle}></div>
            <div className={styles.shimmerLine}></div>
            <div className={styles.shimmerLine} style={{ width: '60%' }}></div>
        </div>
    );

    if (!data) return null;

    const topVibes = Object.entries(data.vibes)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);

    // Calculate Radar Polygon Points
    const points = topVibes.map(([_, val], i) => {
        const angle = (i / topVibes.length) * 2 * Math.PI - Math.PI / 2;
        const r = 10 + (val / 100) * 80; // Scale to 10-90 range for nice padding
        const x = 100 + r * Math.cos(angle);
        const y = 100 + r * Math.sin(angle);
        return `${x},${y}`;
    }).join(' ');

    return (
        <div className={styles.card}>
            <div className={styles.premiumBadge}>GLAM AI IDENTITY</div>

            <div className={styles.header}>
                <div className={styles.headerInfo}>
                    <h3>Style Persona</h3>
                    <p>{data.total_items} precision mappings</p>
                </div>
                <div className={styles.dnaOrb}></div>
            </div>

            <div className={styles.mainVisual}>
                <div className={styles.radarContainer}>
                    <svg viewBox="0 0 200 200" className={styles.radarSvg}>
                        {/* Background Webs */}
                        {[0.2, 0.4, 0.6, 0.8, 1].map((step) => (
                            <circle key={step} cx="100" cy="100" r={step * 90} className={styles.radarPulse} />
                        ))}

                        {/* Axis Lines */}
                        {topVibes.map((_, i) => {
                            const angle = (i / topVibes.length) * 2 * Math.PI - Math.PI / 2;
                            return (
                                <line
                                    key={i}
                                    x1="100" y1="100"
                                    x2={100 + 90 * Math.cos(angle)}
                                    y2={100 + 90 * Math.sin(angle)}
                                    className={styles.radarAxis}
                                />
                            );
                        })}

                        {/* Style Polygon */}
                        <polygon points={points} className={styles.stylePolygon} />

                        {/* Point Glows */}
                        {topVibes.map(([_, val], i) => {
                            const angle = (i / topVibes.length) * 2 * Math.PI - Math.PI / 2;
                            const r = 10 + (val / 100) * 80;
                            return (
                                <circle
                                    key={i}
                                    cx={100 + r * Math.cos(angle)}
                                    cy={100 + r * Math.sin(angle)}
                                    r="3"
                                    className={styles.radarPoint}
                                />
                            );
                        })}
                    </svg>
                </div>

                <div className={styles.vibeLegend}>
                    {topVibes.map(([name, val], i) => (
                        <div key={name} className={styles.legendItem} style={{ '--index': i } as any}>
                            <span className={styles.vibeTitle}>{name}</span>
                            <div className={styles.vibeBarTrack}>
                                <div className={styles.vibeBarFill} style={{ width: `${val}%` }}></div>
                            </div>
                            <span className={styles.vibePercent}>{val}%</span>
                        </div>
                    ))}
                </div>
            </div>

            <div className={styles.paletteSection}>
                <div className={styles.paletteHeader}>
                    <span className={styles.subLabel}>Core Palette</span>
                    <span className={styles.paletteCount}>{data.colors.length} shades</span>
                </div>
                <div className={styles.paletteGrid}>
                    {data.colors.slice(0, 10).map((color, i) => (
                        <div key={i} className={styles.swatchWrapper}>
                            <div
                                className={styles.swatch}
                                style={{ backgroundColor: color.toLowerCase() }}
                            />
                            <span className={styles.swatchName}>{color}</span>
                        </div>
                    ))}
                </div>
            </div>

            <div className={styles.footer}>
                <div className={styles.syncPulse}></div>
                <span>Syncing live with Closet & Pinterest</span>
            </div>
        </div>
    );
}
