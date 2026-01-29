"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getRole, getToken } from "./auth";

type GuardOptions = {
  role?: "user" | "brand";
  redirectTo?: string;
};

export function useAuthGuard(options: GuardOptions = {}) {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const role = options.role ?? "user";
  const redirectTo = options.redirectTo ?? (role === "brand" ? "/auth/brand/login" : "/auth/login");

  useEffect(() => {
    const t = getToken();
    const storedRole = getRole();
    if (!t) {
      router.replace(redirectTo);
      return;
    }

    if (storedRole && storedRole !== role) {
      const mismatchRedirect = storedRole === "brand" ? "/advisor/brands" : "/";
      router.replace(mismatchRedirect);
      return;
    }

    setToken(t);
  }, [router, redirectTo, role]);

  return token;
}
