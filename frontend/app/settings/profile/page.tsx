"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./profile.module.css";
import { API } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { useAuthGuard } from "@/lib/useAuthGuard";
import {
    DAILY_STYLES,
    COLOR_OPTIONS,
    FIT_OPTIONS,
    PRICE_OPTIONS,
    BUYING_PRIORITIES,
    GENDER_OPTIONS
} from "@/lib/constants";

export default function ProfileEditorPage() {
    const router = useRouter();
    const token = useAuthGuard();
    const [loading, setLoading] = useState(true);
    const [saveLoading, setSaveLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const [formData, setFormData] = useState({
        gender: "",
        age: "",
        education: "",
        country: "",
        daily_style: "",
        clothing_description: "",
        styled_combinations: "",
        color_preferences: [] as string[],
        fit_preference: "",
        price_comfort: "",
        buying_priorities: [] as string[],
        min_budget: "",
        max_budget: "",
        wallet_balance: "",
    });

    useEffect(() => {
        if (!token) return;

        const fetchProfile = async () => {
            try {
                const res = await authFetch(API.users.me);
                if (res.ok) {
                    const data = await res.json();
                    setFormData({
                        gender: data.gender || "",
                        age: data.age?.toString() || "",
                        education: data.education || "",
                        country: data.country || "",
                        daily_style: data.daily_style || "",
                        clothing_description: data.clothing_description || "",
                        styled_combinations: data.styled_combinations || "",
                        color_preferences: data.color_preferences || [],
                        fit_preference: data.fit_preference || "",
                        price_comfort: data.price_comfort || "",
                        buying_priorities: data.buying_priorities || [],
                        min_budget: data.min_budget?.toString() || "",
                        max_budget: data.max_budget?.toString() || "",
                        wallet_balance: data.wallet_balance?.toString() || "0.0",
                    });
                }
            } catch (err) {
                console.error("Failed to fetch profile", err);
                setError("Could not load your profile data.");
            } finally {
                setLoading(false);
            }
        };

        fetchProfile();
    }, [token]);

    const handleToggle = (list: string[], item: string, max: number = 99) => {
        if (list.includes(item)) {
            return list.filter(i => i !== item);
        } else if (list.length < max) {
            return [...list, item];
        }
        return list;
    };

    const handleSave = async () => {
        setSaveLoading(true);
        setError(null);
        setSuccess(false);

        try {
            const res = await authFetch(API.users.settings, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...formData,
                    age: formData.age ? parseInt(formData.age) : null,
                    min_budget: formData.min_budget ? parseFloat(formData.min_budget) : null,
                    max_budget: formData.max_budget ? parseFloat(formData.max_budget) : null,
                    wallet_balance: formData.wallet_balance ? parseFloat(formData.wallet_balance) : 0.0,
                }),
            });

            if (res.ok) {
                setSuccess(true);
                setTimeout(() => router.push("/settings"), 1500);
            } else {
                throw new Error("Failed to update profile");
            }
        } catch (err: any) {
            setError(err.message || "Something went wrong while saving.");
        } finally {
            setSaveLoading(false);
        }
    };

    if (!token || loading) {
        return (
            <div className={styles.shell}>
                <div className={styles.header}>
                    <h1>Loading...</h1>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.shell}>
            <div className={styles.header}>
                <button className={styles.backLink} onClick={() => router.push("/settings")}>
                    ← Back to Settings
                </button>
                <h1>Style Profile Editor</h1>
                <p>Refine your fashion identity and global search preferences.</p>
            </div>

            <div className={styles.editorContent}>
                {/* Identity Section */}
                <div className={styles.card}>
                    <div className={styles.step}>
                        <h2>👤 Identity & Location</h2>
                        <div className={styles.formGroup}>
                            <label>Gender</label>
                            <div className={styles.gridOptions}>
                                {GENDER_OPTIONS.map((g) => (
                                    <button
                                        key={g}
                                        className={`${styles.option} ${formData.gender === g ? styles.selected : ""}`}
                                        onClick={() => setFormData({ ...formData, gender: g })}
                                    >
                                        {g}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className={styles.row}>
                            <div className={styles.formGroup}>
                                <label>Age</label>
                                <input
                                    type="number"
                                    value={formData.age}
                                    onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                                />
                            </div>
                            <div className={styles.formGroup}>
                                <label>Country</label>
                                <input
                                    type="text"
                                    value={formData.country}
                                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                                    placeholder="e.g. France"
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Style Section */}
                <div className={styles.card}>
                    <div className={styles.step}>
                        <h2>✨ Your Vibe</h2>
                        <div className={styles.formGroup}>
                            <label>Daily Style</label>
                            <div className={styles.gridOptions}>
                                {DAILY_STYLES.map((s) => (
                                    <button
                                        key={s}
                                        className={`${styles.option} ${formData.daily_style === s ? styles.selected : ""}`}
                                        onClick={() => setFormData({ ...formData, daily_style: s })}
                                    >
                                        {s}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className={styles.formGroup}>
                            <label>Color Preferences</label>
                            <div className={styles.checkboxGroup}>
                                {COLOR_OPTIONS.map((c) => (
                                    <label key={c.value} className={styles.checkboxLabel}>
                                        <input
                                            type="checkbox"
                                            checked={formData.color_preferences.includes(c.value)}
                                            onChange={() => setFormData({
                                                ...formData,
                                                color_preferences: handleToggle(formData.color_preferences, c.value)
                                            })}
                                        />
                                        <span className={styles.checkboxText}>{c.label}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Financials Section */}
                <div className={styles.card}>
                    <div className={styles.step}>
                        <h2>💸 Financial Preferences</h2>
                        <div className={styles.formGroup}>
                            <label>Current Wallet Balance</label>
                            <input
                                type="number"
                                value={formData.wallet_balance}
                                onChange={(e) => setFormData({ ...formData, wallet_balance: e.target.value })}
                                placeholder="e.g. 1000"
                            />
                        </div>

                        <div className={styles.formGroup} style={{ marginTop: '20px' }}>
                            <label>Monthly Budget Range</label>
                            <div className={styles.budgetInputs}>
                                <div className={styles.formGroup}>
                                    <label className={styles.subLabel}>Min</label>
                                    <input
                                        type="number"
                                        value={formData.min_budget}
                                        onChange={(e) => setFormData({ ...formData, min_budget: e.target.value })}
                                    />
                                </div>
                                <div className={styles.formGroup}>
                                    <label className={styles.subLabel}>Max</label>
                                    <input
                                        type="number"
                                        value={formData.max_budget}
                                        onChange={(e) => setFormData({ ...formData, max_budget: e.target.value })}
                                    />
                                </div>
                            </div>
                        </div>

                        <div className={styles.formGroup}>
                            <label>Price Focus</label>
                            <div className={styles.radioGroup}>
                                {PRICE_OPTIONS.map((p) => (
                                    <label key={p} className={styles.radioLabel}>
                                        <input
                                            type="radio"
                                            checked={formData.price_comfort === p}
                                            onChange={() => setFormData({ ...formData, price_comfort: p })}
                                        />
                                        <span className={styles.radioText}>{p}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Details Section */}
                <div className={styles.card}>
                    <div className={styles.step}>
                        <h2>📝 Styling Details</h2>
                        <div className={styles.formGroup}>
                            <label>Wardrobe Description</label>
                            <textarea
                                value={formData.clothing_description}
                                onChange={(e) => setFormData({ ...formData, clothing_description: e.target.value })}
                                rows={3}
                            />
                        </div>
                        <div className={styles.formGroup}>
                            <label>Favorite Combinations</label>
                            <textarea
                                value={formData.styled_combinations}
                                onChange={(e) => setFormData({ ...formData, styled_combinations: e.target.value })}
                                rows={3}
                            />
                        </div>
                    </div>
                </div>

                {error && <div className={styles.error}>{error}</div>}
                {success && <div className={styles.success}>Profile updated successfully! Redirecting...</div>}

                <div className={styles.footer}>
                    <button className={styles.secondaryBtn} onClick={() => router.push("/settings")}>
                        Cancel
                    </button>
                    <button className={styles.primaryBtn} onClick={handleSave} disabled={saveLoading}>
                        {saveLoading ? "Saving..." : "Save Changes"}
                    </button>
                </div>
            </div>
        </div>
    );
}
