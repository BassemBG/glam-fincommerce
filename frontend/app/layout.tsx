import type { Metadata, Viewport } from "next";
import { Playfair_Display, Lora } from 'next/font/google';
import "./globals.css";
import LayoutShell from "@/components/LayoutShell";

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  weight: ['400', '500', '600']
});

const lora = Lora({
  subsets: ['latin'],
  variable: '--font-lora',
  weight: ['400', '500']
});

export const metadata: Metadata = {
  title: "AI Virtual Closet",
  description: "Your digital stylist and closet manager",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${playfair.variable} ${lora.variable}`}>
      <body>
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  );
}
