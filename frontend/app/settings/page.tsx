"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import styles from './page.module.css';
import { API } from '../../lib/api';
import { authFetch, clearToken } from '../../lib/auth';
import { useAuthGuard } from '../../lib/useAuthGuard';

export default function MePage() {
    const [user, setUser] = useState<any>(null);
    const [uploading, setUploading] = useState(false);
    const [showFullPhoto, setShowFullPhoto] = useState(false);
    const router = useRouter();
    const token = useAuthGuard();

    useEffect(() => {
        if (!token) return;
        const fetchUser = async () => {
            try {
                const res = await authFetch(API.users.me);
                if (res.ok) {
                    const data = await res.json();
                    setUser(data);
                }
            } catch (err) {
                console.error("Failed to fetch user:", err);
            }
        };
        fetchUser();
    }, [token]);

    const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await authFetch(API.users.bodyPhoto, {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                setUser((prev: any) => ({ ...prev, full_body_image: data.image_url }));
            }
        } catch (err) {
            console.error("Upload failed:", err);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <h1>Profile & Body</h1>
                <p className="text-muted">Manage your virtual stylist profile.</p>
            </header>

            <div className={styles.profileSection}>
                <div className={styles.avatar}>{user?.full_name?.charAt(0) || 'U'}</div>
                <div className={styles.userInfo}>
                    <h2>{user?.full_name || 'Basse'}</h2>
                    <p className="text-muted">{user?.email || 'basse@example.com'}</p>
                </div>
            </div>

            <section className={styles.twinSection}>
                <div className={styles.sectionHeader}>
                    <h3>Your Virtual Twin</h3>
                    <p>Upload a full-body photo for AI outfit visualization.</p>
                </div>

                <div className={styles.twinUploadCard}>
                    {uploading ? (
                        <div className={styles.previewContainer}>
                            <div className={styles.spinner}></div>
                            <p>Analyzing morphology...</p>
                        </div>
                    ) : user?.full_body_image ? (
                        <div className={styles.previewContainer}>
                            <img
                                src={user.full_body_image}
                                alt="Virtual Twin"
                                className={styles.twinPreview}
                                onClick={() => setShowFullPhoto(true)}
                            />
                            <div className={styles.photoActions}>
                                <button
                                    className={styles.viewFullBtn}
                                    onClick={() => setShowFullPhoto(true)}
                                >
                                    View Full
                                </button>
                                <label className={styles.changeBtn}>
                                    Replace
                                    <input type="file" onChange={handlePhotoUpload} hidden accept="image/*" />
                                </label>
                            </div>
                        </div>
                    ) : (
                        <label className={styles.uploadLabel}>
                            <input
                                type="file"
                                accept="image/*"
                                className={styles.hiddenInput}
                                onChange={handlePhotoUpload}
                            />
                            <div className={styles.uploadPlaceholder}>
                                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>
                                <span>Add Body Photo</span>
                                <p>Ensure you are standing in a neutral pose</p>
                            </div>
                        </label>
                    )}
                </div>
            </section>

            <div className={styles.settingsGrid}>
                <div className={styles.settingItem}>
                    <div className={styles.settingInfo}>
                        <h3>Style Profile</h3>
                        <p>Minimalist, Chic, Streetwear</p>
                    </div>
                    <button className={styles.actionBtn}>Edit</button>
                </div>
            </div>

            <button
                className={styles.logoutBtn}
                onClick={() => {
                    clearToken();
                    router.replace('/auth/login');
                }}
            >
                Sign Out
            </button>

            {/* Full Photo Modal */}
            {showFullPhoto && user?.full_body_image && (
                <div className={styles.photoModal} onClick={() => setShowFullPhoto(false)}>
                    <div className={styles.modalContent} onClick={e => e.stopPropagation()}>
                        <button className={styles.closeModal} onClick={() => setShowFullPhoto(false)}>✕</button>
                        <img src={user.full_body_image} alt="Full Body" className={styles.fullPhoto} />
                    </div>
                </div>
            )}
        </div>
    );
}
