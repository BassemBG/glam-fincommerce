"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./onboarding.module.css";
import { API } from "@/lib/api";
import { authFetch } from "@/lib/auth";
import { useAuthGuard } from "@/lib/useAuthGuard";

const DAILY_STYLES = ["Modern Chic", "Sport", "Classic", "Bohemian", "Minimalist", "Edgy", "Preppy"];
const COLOR_OPTIONS = [
  { label: "Black / White / Grey", value: "bw-grey" },
  { label: "Neutral (Beige, Brown, Cream)", value: "neutral" },
  { label: "Dark Colors", value: "dark" },
  { label: "Bright Colors", value: "bright" },
  { label: "Pastels", value: "pastels" },
];
const FIT_OPTIONS = ["Tight / Fitted", "Regular", "Loose / Oversized", "Depends on the item"];
const PRICE_OPTIONS = ["Low (Budget First)", "Medium (Quality over Price)", "High (I Invest)", "Depends on the Item"];
const BUYING_PRIORITIES = [
  "Comfort",
  "Style",
  "Price",
  "Brand",
  "Quality / Durability",
  "Trendiness",
];

export default function OnboardingPage() {
  const router = useRouter();
  const token = useAuthGuard();
  const [checkedCompletion, setCheckedCompletion] = useState(false);
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    age: "",
    education: "",
    daily_style: "",
    clothing_description: "",
    styled_combinations: "",
    color_preferences: [] as string[],
    fit_preference: "",
    price_comfort: "",
    buying_priorities: [] as string[],
  });

  const [pinterestLoading, setPinterestLoading] = useState(false);
  const [pinterestConnected, setPinterestConnected] = useState(false);

  const handleNext = () => {
    if (step < 6) {
      setStep(step + 1);
      setError(null);
    }
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  const handlePinterestConnect = async () => {
    setPinterestLoading(true);
    setError(null);
    try {
      // Get user_id from token or from API
      const response = await authFetch(`${API.base}/users/me`);
      const userData = await response.json();
      const userId = userData.id;

      // Store user_id in sessionStorage for callback
      if (typeof window !== "undefined") {
        sessionStorage.setItem("pinterest_user_id", userId);
      }

      // Get OAuth URL from backend
      const oauthResponse = await fetch(`${API.base}/auth/pinterest/login`);
      const oauthData = await oauthResponse.json();

      // Redirect to Pinterest OAuth
      if (typeof window !== "undefined") {
        window.location.href = oauthData.oauth_url;
      }
    } catch (err: any) {
      setError(err.message || "Failed to connect to Pinterest");
      setPinterestLoading(false);
    }
  };

  const handleColorToggle = (value: string) => {
    setFormData((prev) => ({
      ...prev,
      color_preferences: prev.color_preferences.includes(value)
        ? prev.color_preferences.filter((c) => c !== value)
        : [...prev.color_preferences, value],
    }));
  };

  const handlePriorityToggle = (priority: string) => {
    setFormData((prev) => ({
      ...prev,
      buying_priorities: prev.buying_priorities.includes(priority)
        ? prev.buying_priorities.filter((p) => p !== priority)
        : prev.buying_priorities.length < 2
        ? [...prev.buying_priorities, priority]
        : prev.buying_priorities,
    }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(API.users.onboarding, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          age: formData.age ? parseInt(formData.age) : null,
          education: formData.education || null,
          daily_style: formData.daily_style || null,
          clothing_description: formData.clothing_description || null,
          styled_combinations: formData.styled_combinations || null,
          color_preferences: formData.color_preferences,
          fit_preference: formData.fit_preference || null,
          price_comfort: formData.price_comfort || null,
          buying_priorities: formData.buying_priorities,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to save profile");
      }

      // Onboarding completed; clear one-shot flag
      if (typeof window !== 'undefined') {
        localStorage.removeItem('needsOnboarding');
      }
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const stepClass = `step-${step}`;
  const progress = (step / 6) * 100;

  // Check early: if NO localStorage flag, redirect immediately
  useEffect(() => {
    if (!token) return;
    
    // First, check if user is even supposed to be on this page
    const flag = typeof window !== 'undefined' ? localStorage.getItem('needsOnboarding') : null;
    if (flag !== '1') {
      // No flag = direct access or returning after onboarding. Redirect to home.
      router.replace("/");
      return;
    }
    
    // If we have the flag, verify onboarding status on server
    const verify = async () => {
      try {
        const res = await authFetch(API.users.me);
        if (res.ok) {
          const user = await res.json();
          
          // If already completed, redirect to home
          if (user.onboarding_completed) {
            router.replace("/");
            return;
          }
        }
      } catch (err) {
        console.error("Failed to check onboarding status", err);
      } finally {
        setCheckedCompletion(true);
      }
    };

    verify();
  }, [token, router]);

  // Wait for token to load AND verification to complete
  if (!token || !checkedCompletion) {
    return null;
  }

  return (
    <div className={styles.shell}>
      {/* Progress bar */}
      <div className={styles.progressBar}>
        <div className={styles.progressFill} style={{ width: `${progress}%` }}></div>
      </div>

      {/* Hero text */}
      <div className={styles.header}>
        <h1>Let's Get to Know You</h1>
        <p>Answer a few quick questions to unlock personalized styling</p>
      </div>

      {/* Step 1: Profile Basics */}
      {step === 1 && (
        <div className={`${styles.card} ${styles[stepClass]}`}>
          <div className={styles.step}>
            <h2>👤 Tell Us About Yourself</h2>
            <div className={styles.formGroup}>
              <label>Age (optional)</label>
              <input
                type="number"
                min="13"
                max="120"
                value={formData.age}
                onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                placeholder="25"
              />
            </div>
            <div className={styles.formGroup}>
              <label>Where do you study / work? (optional)</label>
              <input
                type="text"
                value={formData.education}
                onChange={(e) => setFormData({ ...formData, education: e.target.value })}
                placeholder="e.g., Stanford University"
              />
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Daily Style */}
      {step === 2 && (
        <div className={`${styles.card} ${styles[stepClass]}`}>
          <div className={styles.step}>
            <h2>✨ Your Daily Style</h2>
            <p className={styles.subtitle}>Pick the vibe that resonates with you</p>
            <div className={styles.gridOptions}>
              {DAILY_STYLES.map((style) => (
                <button
                  key={style}
                  className={`${styles.option} ${formData.daily_style === style ? styles.selected : ""}`}
                  onClick={() => setFormData({ ...formData, daily_style: style })}
                >
                  {style}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Colors */}
      {step === 3 && (
        <div className={`${styles.card} ${styles[stepClass]}`}>
          <div className={styles.step}>
            <h2>🎨 Colors You Feel Good In</h2>
            <p className={styles.subtitle}>Select all that apply</p>
            <div className={styles.checkboxGroup}>
              {COLOR_OPTIONS.map((color) => (
                <label key={color.value} className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={formData.color_preferences.includes(color.value)}
                    onChange={() => handleColorToggle(color.value)}
                  />
                  <span className={styles.checkboxText}>{color.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Fit Preference */}
      {step === 4 && (
        <div className={`${styles.card} ${styles[stepClass]}`}>
          <div className={styles.step}>
            <h2>👕 How Do You Like to Fit?</h2>
            <p className={styles.subtitle}>Your silhouette preference</p>
            <div className={styles.radioGroup}>
              {FIT_OPTIONS.map((fit) => (
                <label key={fit} className={styles.radioLabel}>
                  <input
                    type="radio"
                    name="fit"
                    value={fit}
                    checked={formData.fit_preference === fit}
                    onChange={(e) => setFormData({ ...formData, fit_preference: e.target.value })}
                  />
                  <span className={styles.radioText}>{fit}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 5: Price Comfort */}
      {step === 5 && (
        <div className={`${styles.card} ${styles[stepClass]}`}>
          <div className={styles.step}>
            <h2>💸 Price Comfort Zone</h2>
            <p className={styles.subtitle}>What feels like "normal" spending for you?</p>
            <div className={styles.radioGroup}>
              {PRICE_OPTIONS.map((price) => (
                <label key={price} className={styles.radioLabel}>
                  <input
                    type="radio"
                    name="price"
                    value={price}
                    checked={formData.price_comfort === price}
                    onChange={(e) => setFormData({ ...formData, price_comfort: e.target.value })}
                  />
                  <span className={styles.radioText}>{price}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Step 6: Buying Priorities + Clothing Description */}
      {step === 6 && (
        <div className={`${styles.card} ${styles[stepClass]}`}>
          <div className={styles.step}>
            <h2>❤️ What Matters Most?</h2>
            <p className={styles.subtitle}>Pick up to 2 priorities</p>
            <div className={styles.gridOptions}>
              {BUYING_PRIORITIES.map((priority) => (
                <button
                  key={priority}
                  className={`${styles.option} ${
                    formData.buying_priorities.includes(priority) ? styles.selected : ""
                  }`}
                  onClick={() => handlePriorityToggle(priority)}
                >
                  {priority}
                </button>
              ))}
            </div>

            <div className={styles.formGroup} style={{ marginTop: "32px" }}>
              <label>Describe your current wardrobe (optional)</label>
              <textarea
                value={formData.clothing_description}
                onChange={(e) => setFormData({ ...formData, clothing_description: e.target.value })}
                placeholder="e.g., Mostly casual basics, love vintage pieces, prefer earth tones..."
                rows={3}
              />
            </div>

            <div className={styles.formGroup}>
              <label>Your favorite styled combinations (optional)</label>
              <textarea
                value={formData.styled_combinations}
                onChange={(e) => setFormData({ ...formData, styled_combinations: e.target.value })}
                placeholder="e.g., White tee + vintage jeans + sneakers, black blazer + gold jewelry..."
                rows={3}
              />
            </div>
          </div>
        </div>
      )}

      {error && <div className={styles.error}>{error}</div>}

      {/* Navigation */}
      <div className={styles.footer}>
        <button className={styles.secondaryBtn} onClick={handleBack} disabled={step === 1}>
          Back
        </button>
        {step < 6 ? (
          <button className={styles.primaryBtn} onClick={handleNext}>
            Next
          </button>
        ) : (
          <button className={styles.primaryBtn} onClick={handleSubmit} disabled={loading}>
            {loading ? "Saving..." : "Finish"}
          </button>
        )}
      </div>

      {/* Step indicator */}
      <div className={styles.stepIndicator}>
        Step {step} of 6
      </div>
    </div>
  );
}
