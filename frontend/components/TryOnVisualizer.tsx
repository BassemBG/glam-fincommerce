"use client";

import { useState, useEffect } from 'react';
import styles from './TryOnVisualizer.module.css';

interface TryOnVisualizerProps {
    bodyImage: string;
    items: { image_url: string; body_region: string }[];
    onClose: () => void;
    tryonImageUrl?: string;
    onSave?: () => void;
}

const TryOnVisualizer = ({ bodyImage, items, onClose, tryonImageUrl, onSave }: TryOnVisualizerProps) => {
    const [step, setStep] = useState<'scanning' | 'ready'>('scanning');

    useEffect(() => {
        const timer = setTimeout(() => setStep('ready'), 2500);
        return () => clearTimeout(timer);
    }, []);

    // Simple layout logic based on body regions (Fallback if no AI image yet)
    const getStyleForRegion = (region: string) => {
        switch (region) {
            case 'top': return { top: '25%', left: '50%', transform: 'translateX(-50%)', width: '40%' };
            case 'bottom': return { top: '50%', left: '50%', transform: 'translateX(-50%)', width: '45%' };
            case 'feet': return { bottom: '5%', left: '50%', transform: 'translateX(-50%)', width: '25%' };
            case 'head': return { top: '5%', left: '50%', transform: 'translateX(-50%)', width: '20%' };
            case 'full_body': return { top: '20%', left: '50%', transform: 'translateX(-50%)', width: '50%', height: '60%' };
            default: return { display: 'none' };
        }
    };

    return (
        <div className={styles.overlay}>
            <div className={styles.container}>
                <button className={styles.closeBtn} onClick={onClose}>✕</button>

                <div className={styles.canvasWrapper}>
                    {/* Background Body Photo */}
                    <img src={bodyImage} alt="User Body" className={styles.basePhoto} />

                    {step === 'scanning' && <div className={styles.scanLine} />}

                    {step === 'ready' && (
                        <div className={styles.clothingLayer}>
                            {tryonImageUrl ? (
                                // Show the real AI-generated result
                                <img
                                    src={tryonImageUrl.startsWith('http')
                                        ? tryonImageUrl
                                        : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${tryonImageUrl}`
                                    }
                                    alt="AI Result"
                                    className={`${styles.garment} ${styles.aiResult}`}
                                    style={{
                                        top: 0,
                                        left: 0,
                                        width: '100%',
                                        height: '100%',
                                        objectFit: 'cover',
                                        zIndex: 100
                                    }}
                                />
                            ) : (
                                // Fallback: Layer individual pieces
                                items.map((item, i) => (
                                    <img
                                        key={i}
                                        src={item.image_url}
                                        alt="garment"
                                        className={styles.garment}
                                        style={getStyleForRegion(item.body_region) as any}
                                    />
                                ))
                            )}
                        </div>
                    )}
                </div>

                <div className={styles.controls}>
                    <h2>{step === 'scanning' ? 'Virtual Morphology Scan...' : 'The New You'}</h2>
                    <p className="text-muted">
                        {step === 'scanning'
                            ? 'Aligning your closet pieces with your body type...'
                            : tryonImageUrl
                                ? 'Your personalized AI look is ready. Save it to your gallery!'
                                : 'This is an AI-assisted visualization of the proposed outfit.'}
                    </p>
                    {step === 'ready' && tryonImageUrl && onSave && (
                        <button className={styles.saveBtn} onClick={onSave}>
                            Save to Outfits
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TryOnVisualizer;
