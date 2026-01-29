"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API } from "@/lib/api";

export default function PinterestCallbackPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Get URL parameters
        if (typeof window === "undefined") return;

        const params = new URLSearchParams(window.location.search);
        const code = params.get("code");
        const state = params.get("state");

        console.log("📌 Pinterest callback received");
        console.log("Code:", code?.substring(0, 20) + "...");
        console.log("State:", state?.substring(0, 20) + "...");

        if (!code) {
          throw new Error("No authorization code received from Pinterest");
        }

        // Get user_id from sessionStorage (stored before redirect)
        const userId = sessionStorage.getItem("pinterest_user_id");
        if (!userId) {
          throw new Error("User session lost. Please try connecting again.");
        }

        console.log("User ID from session:", userId);

        // Build callback URL
        const callbackUrl = new URL(`${API.base}/auth/pinterest/callback`, window.location.origin);
        callbackUrl.searchParams.append("code", code);
        callbackUrl.searchParams.append("state", state || "");
        callbackUrl.searchParams.append("user_id", userId);

        console.log("Calling backend:", callbackUrl.toString());

        // Get token from localStorage
        const token = localStorage.getItem("vc_access_token");
        const headers: any = {
          "Content-Type": "application/json",
        };

        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        console.log("Sending request to backend...");

        const response = await fetch(callbackUrl.toString(), {
          method: "GET",
          headers,
        });

        console.log("Response status:", response.status);

        if (!response.ok) {
          let errorMessage = "Failed to connect Pinterest";
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.message || errorMessage;
          } catch (e) {
            const text = await response.text();
            errorMessage = text || errorMessage;
          }
          throw new Error(errorMessage);
        }

        const data = await response.json();
        console.log("✅ Backend response:", data);

        // Clear sessionStorage
        sessionStorage.removeItem("pinterest_user_id");

        // Redirect back to onboarding with success
        console.log("Redirecting back to onboarding...");
        
        setTimeout(() => {
          const redirectUrl = `/settings?pinterest=success`;
          console.log("Going to:", redirectUrl);
          router.push(redirectUrl);
        }, 2000);
      } catch (error) {
        console.error("❌ Pinterest callback error:", error);
        
        // Check if it's a network/connection error
        let errorMessage = error instanceof Error ? error.message : "Unknown error";
        
        if (error instanceof TypeError && (errorMessage.includes("fetch") || errorMessage.includes("network"))) {
          errorMessage = "Unable to connect to Pinterest. Please check your internet connection and try again.";
        } else if (errorMessage.includes("timed out") || errorMessage.includes("timeout") || errorMessage.includes("Max retries")) {
          errorMessage = "Connection timeout. Please check your internet connection and try again.";
        }
        
        setError(errorMessage);
        setLoading(false);

        // Redirect to onboarding with error after a delay
        setTimeout(() => {
          router.push(`/settings?pinterest=error&message=${encodeURIComponent(errorMessage)}`);
        }, 3000);
      }
    };

    handleCallback();
  }, [router]);

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", backgroundColor: "#f5f5f5" }}>
      <div style={{ textAlign: "center", backgroundColor: "white", padding: "40px", borderRadius: "12px", boxShadow: "0 2px 8px rgba(0,0,0,0.1)", maxWidth: "500px" }}>
        {loading && !error ? (
          <>
            <h1>Connecting to Pinterest...</h1>
            <p>Please wait while we sync your Pinterest data.</p>
            <div style={{ marginTop: "20px" }}>
              <div style={{
                width: "40px",
                height: "40px",
                margin: "0 auto",
                border: "4px solid #f0f0f0",
                borderTop: "4px solid #E60023",
                borderRadius: "50%",
                animation: "spin 1s linear infinite"
              }}></div>
            </div>
            <style>{`
              @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
              }
            `}</style>
          </>
        ) : (
          <>
            <h1>⚠️ Connection Error</h1>
            <p style={{ color: "#d32f2f", marginTop: "10px" }}>{error}</p>
            <p style={{ color: "#666", marginTop: "15px" }}>Redirecting back to onboarding...</p>
          </>
        )}
      </div>
    </div>
  );
}

