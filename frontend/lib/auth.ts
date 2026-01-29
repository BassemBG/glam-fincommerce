"use client";

const TOKEN_KEY = "vc_access_token";
const ROLE_KEY = "vc_role";

export const saveToken = (token: string, role: "user" | "brand" = "user") => {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(ROLE_KEY, role);
};

export const clearToken = () => {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
};

export const getToken = () => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
};

export const getRole = () => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ROLE_KEY) as "user" | "brand" | null;
};

export const authFetch = async (input: RequestInfo | URL, init: RequestInit = {}) => {
  try {
    const token = getToken();
    const headers = new Headers(init.headers || {});
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const response = await fetch(input, { ...init, headers });
    return response;
  } catch (error) {
    console.error("authFetch error:", error);
    throw error;
  }
};

export const isAuthed = () => !!getToken();
