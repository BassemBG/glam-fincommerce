"use client";

import { usePathname } from "next/navigation";
import BottomNav from "./BottomNav";
import FloatingStylist from "./FloatingStylist";

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuth = pathname.startsWith("/auth");
  const isOnboarding = pathname === "/onboarding";

  return (
    <>
      <main className="container" style={(isAuth || isOnboarding) ? { padding: 0, maxWidth: "100%" } : {}}>
        {children}
      </main>
      {!isAuth && !isOnboarding && (
        <>
          <FloatingStylist />
          <BottomNav />
        </>
      )}
    </>
  );
}
