"use client";

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import styles from './page.module.css';
import { API } from '../../lib/api';
import { authFetch, clearToken } from '../../lib/auth';
import { useAuthGuard } from '../../lib/useAuthGuard';

function SettingsContent() {
    const [user, setUser] = useState<any>(null);
    const [uploading, setUploading] = useState(false);
    const [showFullPhoto, setShowFullPhoto] = useState(false);
    const [pinterestConnected, setPinterestConnected] = useState<boolean | null>(null);
    const [pinterestLoading, setPinterestLoading] = useState(false);
    const [pinterestMessage, setPinterestMessage] = useState<string | null>(null);
    const [showPinterestInfo, setShowPinterestInfo] = useState(false);

    const [saveLoading, setSaveLoading] = useState(false);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

    const router = useRouter();
    const searchParams = useSearchParams();
    const token = useAuthGuard();

    useEffect(() => {
        if (!token) return;
        const fetchUser = async () => {
            try {
                const res = await authFetch(API.users.me);
                if (res.ok) {
                    const data = await res.json();
                    setUser(data);
                    // Refresh connection status once user is known
                    checkPinterestStatus();
                } else {
                    console.error("Failed to fetch user. Status:", res.status, res.statusText);
                    const errorData = await res.json().catch(() => null);
                    console.error("Error response:", errorData);
                }
            } catch (err) {
                console.error("Failed to fetch user:", err);
            }
        };
        fetchUser();
    }, [token]);

    useEffect(() => {
        if (!token) return;
        // Read query params for success/error from callback
        const statusParam = searchParams.get("pinterest");
        const messageParam = searchParams.get("message");
        if (statusParam === "success") {
            setPinterestConnected(true);
            setPinterestMessage("Pinterest connected successfully.");
        } else if (statusParam === "error") {
            setPinterestConnected(false);
            setPinterestMessage(messageParam || "Pinterest connection failed");
        }
    }, [token, searchParams]);

    const checkPinterestStatus = async () => {
        try {
            const res = await authFetch(API.pinterest.status);
            if (res.ok) {
                const data = await res.json();
                setPinterestConnected(Boolean(data.connected));
            } else {
                setPinterestConnected(false);
            }
        } catch (err) {
            console.error("Failed to check Pinterest status", err);
            setPinterestConnected(false);
        }
    };

    const handlePinterestConnect = async () => {
        if (pinterestLoading) return;
        try {
            setPinterestLoading(true);
            setPinterestMessage(null);

            const me = user ?? (await (await authFetch(API.users.me)).json());
            const userId = me?.id;
            if (!userId) throw new Error("Missing user id");

            sessionStorage.setItem("pinterest_user_id", userId);

            const oauthResponse = await fetch(API.pinterest.login);
            if (!oauthResponse.ok) throw new Error("Failed to start Pinterest OAuth");
            const { oauth_url } = await oauthResponse.json();

            window.location.href = oauth_url;
        } catch (err: any) {
            console.error("Pinterest connect failed", err);
            setPinterestMessage(err?.message || "Failed to connect Pinterest");
            setPinterestLoading(false);
        }
    };

    const [analysisResults, setAnalysisResults] = useState<any>(null);

    const handleSettingsUpdate = async (key: string, value: any) => {
        try {
            const res = await authFetch(API.users.settings, {
                method: 'PUT',
                body: JSON.stringify({ [key]: value })
            });
            if (res.ok) {
                setUser((prev: any) => ({ ...prev, [key]: value }));
            }
        } catch (err) {
            console.error("Failed to update settings:", err);
        }
    };


    const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setUploading(true);

        const formData = new FormData();
        formData.append('file', file);

        try {
            // TODO: check this if error happens: was fetch()
            const photoRes = await authFetch(API.users.bodyPhoto, {
                method: 'POST',
                body: formData
            });

            if (photoRes.ok) {
                const photoData = await photoRes.json();
                setUser((prev: any) => ({ ...prev, full_body_image: photoData.image_url }));

                // Then trigger the background analysis
                const analysisRes = await authFetch(API.users.analyzeProfile, {
                    method: 'POST',
                    body: formData
                });

                if (analysisRes.ok) {
                    const analysisData = await analysisRes.json();
                    setAnalysisResults(analysisData.analysis);
                }
            }
        } catch (err) {
            console.error("Upload or analysis failed:", err);
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
                            <p>Analyzing physical traits...</p>
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

                {analysisResults && (
                    <div className={styles.analysisResults}>
                        <div className={styles.analysisGrid}>
                            <div className={styles.resultItem}>
                                <span className={styles.resultLabel}>Morphology</span>
                                <span className={styles.resultValue}>{analysisResults.morphology}</span>
                            </div>
                            <div className={styles.resultItem}>
                                <span className={styles.resultLabel}>Skin Tone</span>
                                <span className={styles.resultValue}>{analysisResults.skin_color}</span>
                            </div>
                            <div className={styles.resultItem}>
                                <span className={styles.resultLabel}>Est. Height</span>
                                <span className={styles.resultValue}>{analysisResults.height}</span>
                            </div>
                            <div className={styles.resultItem}>
                                <span className={styles.resultLabel}>Est. Weight</span>
                                <span className={styles.resultValue}>{analysisResults.weight}</span>
                            </div>
                        </div>
                        {analysisResults.summary && (
                            <p className={styles.analysisSummary}>{analysisResults.summary}</p>
                        )}
                    </div>
                )}
            </section>

            <div className={styles.settingsGrid}>
                <div className={styles.settingItem}>
                    <div className={styles.settingInfo}>
                        <div className={styles.settingHeader}>
                            <svg className={styles.pinterestLogo} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <circle cx="12" cy="12" r="11" fill="#E60023" />
                                <path d="M8 6V18C8 18.5523 8.44772 19 9 19C9.55228 19 10 18.5523 10 18V15C10.7626 15.6196 11.7929 16 13 16C15.7614 16 18 13.7614 18 11C18 8.23858 15.7614 6 13 6C11.7929 6 10.7626 6.38035 10 7V6C10 5.44772 9.55228 5 9 5C8.44772 5 8 5.44772 8 6ZM13 8C14.6569 8 16 9.34315 16 11C16 12.6569 14.6569 14 13 14C11.3431 14 10 12.6569 10 11C10 9.34315 11.3431 8 13 8Z" fill="white" />
                            </svg>
                            <div className={styles.headerWithInfo}>
                                <h3>Pinterest</h3>
                                <div className={styles.infoIconWrapper} onMouseEnter={() => setShowPinterestInfo(true)} onMouseLeave={() => setShowPinterestInfo(false)}>
                                    <svg className={styles.infoIcon} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
                                        <path d="M12 16V12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                        <circle cx="12" cy="9" r="0.5" fill="currentColor" />
                                    </svg>
                                    {showPinterestInfo && (
                                        <div className={styles.infoTooltip}>
                                            Connect Pinterest to discover outfit inspiration, save style ideas, and get personalized recommendations based on your boards.
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                        <p className={styles.statusBadge} style={{ color: pinterestConnected ? "#16a34a" : "#94a3b8" }}>
                            {pinterestConnected ? "✓ Connected" : "Not connected"}
                        </p>
                        {pinterestMessage && <small style={{ color: pinterestConnected ? "#16a34a" : "#dc2626", marginTop: "4px", display: "block" }}>{pinterestMessage}</small>}
                    </div>
                    <button
                        className={`${styles.actionBtn} ${pinterestConnected ? styles.connected : ""}`}
                        onClick={handlePinterestConnect}
                        disabled={pinterestLoading || pinterestConnected === true}
                    >
                        {pinterestConnected ? "✓ Connected" : pinterestLoading ? "Connecting..." : "Connect"}
                    </button>
                </div>
                <div className={styles.settingItem}>
                    <div className={styles.settingInfo}>
                        <h3>Style Profile</h3>
                        <p>{user?.daily_style || 'Minimalist, Chic'}</p>
                    </div>
                    <button
                        className={styles.actionBtn}
                        onClick={() => router.push('/settings/profile')}
                    >
                        Edit
                    </button>
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
            {
                showFullPhoto && user?.full_body_image && (
                    <div className={styles.photoModal} onClick={() => setShowFullPhoto(false)}>
                        <div className={styles.modalContent} onClick={e => e.stopPropagation()}>
                            <button className={styles.closeModal} onClick={() => setShowFullPhoto(false)}>✕</button>
                            <img src={user.full_body_image} alt="Full Body" className={styles.fullPhoto} />
                        </div>
                    </div>
                )
            }
        </div >
    );
}

export default function MePage() {
    return (
        <Suspense fallback={<div className={styles.container}>Loading settings...</div>}>
            <SettingsContent />
        </Suspense>
    );
}
