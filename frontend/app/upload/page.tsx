"use client";

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import { API } from '../../lib/api';
import { authFetch } from '../../lib/auth';
import { useAuthGuard } from '../../lib/useAuthGuard';

export default function UploadPage() {
    const router = useRouter();
    const fileRef = useRef<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [status, setStatus] = useState<'idle' | 'uploading' | 'analyzing' | 'done' | 'error'>('idle');
    const [analysis, setAnalysis] = useState<any>(null);
    const [errorMsg, setErrorMsg] = useState<string>('');
    const token = useAuthGuard();

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selected = e.target.files[0];
            fileRef.current = selected;
            setPreview(URL.createObjectURL(selected));
            setStatus('idle');
            setErrorMsg('');
        }
    };

    const handleUpload = async () => {
        if (!fileRef.current) return;

        setStatus('uploading');

        try {
            // Create form data
            const formData = new FormData();
            formData.append('file', fileRef.current);

            setStatus('analyzing');

            // Call the real backend API
            //TODO: check this if problem occurs: was just fetch()
            const response = await authFetch(API.clothing.ingest, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const data = await response.json();

            console.log("Ingestion response:", data);
            console.log("Duplicate status:", data.qdrant_result?.status);

            // Extract analysis from new response structure
            setAnalysis({
                category: data.clothing?.category || 'Clothing',
                sub_category: data.clothing?.sub_category || 'Item',
                body_region: data.clothing?.body_region || 'top',
                vibe: data.clothing?.vibe || 'Casual',
                colors: data.clothing?.colors || [],
                description: data.clothing?.description || 'A versatile piece for your wardrobe.',
                styling_tips: data.clothing?.styling_tips || 'Style it your way!',
                image_url: data.image_url,
                mask_url: data.image_url, // No mask in new pipeline yet
                brand: data.brand?.detected_brand,
                price: data.price
            });
            setStatus('done');

        } catch (err: any) {
            console.error('Upload error:', err);
            setErrorMsg(err.message || 'Something went wrong. Please try again.');
            setStatus('error');
        }
    };

    const handleReset = () => {
        setPreview(null);
        fileRef.current = null;
        setStatus('idle');
        setAnalysis(null);
        setErrorMsg('');
    };

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <h1>New Item</h1>
                <p className="text-muted">Analyze and add to your digital wardrobe.</p>
            </header>

            {!preview ? (
                <label className={styles.dropzone}>
                    <input type="file" accept="image/*" onChange={handleFileChange} hidden />
                    <div className={styles.dropzoneContent}>
                        <div className={styles.icon}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" /></svg>
                        </div>
                        <span>Choose a Photo</span>
                        <p>Take a snap or pick from gallery</p>
                    </div>
                </label>
            ) : (
                <div className={styles.previewSection}>
                    <div className={styles.previewWrapper}>
                        <img src={analysis?.mask_url || preview} alt="Upload Preview" />
                        {status === 'analyzing' && <div className={styles.scanner} />}
                    </div>

                    {status === 'idle' && (
                        <div className={styles.actionRow}>
                            <button className={styles.primaryBtn} onClick={handleUpload}>
                                Analyze & Save Item
                            </button>
                            <button className={styles.ghostBtn} onClick={handleReset}>
                                Replace
                            </button>
                        </div>
                    )}

                    {(status === 'uploading' || status === 'analyzing') && (
                        <div className={styles.loadingBox}>
                            <div className={styles.spinner} />
                            <span>{status === 'uploading' ? 'Uploading...' : 'AI is analyzing your piece...'}</span>
                        </div>
                    )}

                    {status === 'error' && (
                        <div className={styles.errorBox}>
                            <p>{errorMsg}</p>
                            <button className={styles.ghostBtn} onClick={handleReset}>
                                Try Again
                            </button>
                        </div>
                    )}

                    {status === 'done' && analysis && (
                        <div className={styles.resultCard}>
                            <div className={styles.tags}>
                                <span className={styles.tag}>{analysis.body_region.replace('_', ' ')}</span>
                                <span className={styles.tag}>{analysis.vibe}</span>
                                {analysis.brand && <span className={styles.tag} style={{ background: '#000', color: '#fff' }}>{analysis.brand}</span>}
                            </div>

                            <h3>{analysis.sub_category}</h3>
                            {analysis.price && (
                                <p className={styles.priceTag}>${analysis.price} (Estimated)</p>
                            )}
                            <p>{analysis.description}</p>
                            {analysis.styling_tips && (
                                <p className={styles.stylingTip}>💡 {analysis.styling_tips}</p>
                            )}
                            <div className={styles.doneActions}>
                                <button className={styles.primaryBtn} onClick={() => router.push('/')}>
                                    View in Closet
                                </button>
                                <button className={styles.ghostBtn} onClick={handleReset}>
                                    Add Another
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
