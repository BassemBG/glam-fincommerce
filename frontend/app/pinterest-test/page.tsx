"use client";

import { useState, useEffect } from "react";
import { API } from "@/lib/api";
import { getToken } from "@/lib/auth";

export default function PinterestTestPage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isClient, setIsClient] = useState(false);
  const [debugInfo, setDebugInfo] = useState<any>(null);

  useEffect(() => {
    setIsClient(true);
    // Set debug info only on client
    setDebugInfo({
      authenticated: getToken() ? "Yes" : "No",
      sessionStorage: typeof window !== "undefined" ? (sessionStorage.getItem("pinterest_user_id") || "Not set") : "N/A",
      token: getToken() ? getToken()?.substring(0, 20) + "..." : "Not set",
    });
  }, []);

  const testOAuthUrl = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API.base}/auth/pinterest/login`);
      const data = await response.json();
      setResult(data);
      console.log("OAuth URL Response:", data);
    } catch (err: any) {
      setError(err.message);
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  const testUserMe = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = getToken();
      if (!token) {
        setError("Not authenticated. Please log in first.");
        return;
      }

      const response = await fetch(`${API.base}/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error(`Status ${response.status}`);

      const data = await response.json();
      setResult(data);
      console.log("User Data:", data);
    } catch (err: any) {
      setError(err.message);
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  const startPinterestFlow = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = getToken();
      if (!token) {
        setError("Not authenticated. Please log in first.");
        return;
      }

      // Get user data
      const userResponse = await fetch(`${API.base}/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!userResponse.ok) throw new Error("Failed to get user");

      const user = await userResponse.json();
      console.log("User:", user);

      // Store user_id in sessionStorage
      sessionStorage.setItem("pinterest_user_id", user.id);
      console.log("Stored pinterest_user_id:", user.id);

      // Get OAuth URL
      const oauthResponse = await fetch(`${API.base}/auth/pinterest/login`);
      const oauthData = await oauthResponse.json();
      console.log("OAuth URL:", oauthData.oauth_url);

      setResult({
        message: "Redirecting to Pinterest...",
        oauth_url: oauthData.oauth_url,
        user_id: user.id,
      });

      // Redirect
      setTimeout(() => {
        window.location.href = oauthData.oauth_url;
      }, 2000);
    } catch (err: any) {
      setError(err.message);
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!isClient) {
    return (
      <div style={{ maxWidth: "800px", margin: "0 auto", padding: "20px" }}>
        <h1>Pinterest Integration Test</h1>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "20px" }}>
      <h1>Pinterest Integration Test</h1>

      <div style={{ marginBottom: "20px" }}>
        <button
          onClick={testOAuthUrl}
          disabled={loading}
          style={{
            padding: "10px 20px",
            marginRight: "10px",
            backgroundColor: "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Loading..." : "Test OAuth URL"}
        </button>

        <button
          onClick={testUserMe}
          disabled={loading}
          style={{
            padding: "10px 20px",
            marginRight: "10px",
            backgroundColor: "#28a745",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Loading..." : "Test User API"}
        </button>

        <button
          onClick={startPinterestFlow}
          disabled={loading}
          style={{
            padding: "10px 20px",
            backgroundColor: "#E60023",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Loading..." : "Start Pinterest Flow"}
        </button>
      </div>

      {error && (
        <div style={{ color: "red", padding: "10px", backgroundColor: "#ffe0e0", borderRadius: "4px", marginBottom: "20px" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div
          style={{
            padding: "15px",
            backgroundColor: "#f5f5f5",
            borderRadius: "4px",
            marginTop: "20px",
          }}
        >
          <h3>Result:</h3>
          <pre style={{ overflow: "auto", maxHeight: "400px" }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}

      <div style={{ marginTop: "30px", fontSize: "14px", color: "#666" }}>
        <h3>Debug Info:</h3>
        <p>
          <strong>API Base:</strong> {API.base}
        </p>
        <p>
          <strong>Authenticated:</strong> {debugInfo?.authenticated || "Loading..."}
        </p>
        <p>
          <strong>SessionStorage pinterest_user_id:</strong> {debugInfo?.sessionStorage || "Loading..."}
        </p>
        <p>
          <strong>LocalStorage Token:</strong> {debugInfo?.token || "Loading..."}
        </p>
      </div>
    </div>
  );
}
