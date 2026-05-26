import type { Metadata } from "next";
import { Lora, Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import NarrativeStream from "@/components/pemali/NarrativeStream";

const lora = Lora({
  variable: "--font-lora",
  subsets: ["latin"],
  weight: ["400", "500"],
  style: ["normal", "italic"],
  display: "swap",
});

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PEMALI | AI Agentic Geo Auditor",
  description: "Platform Ekologi Modular Agentic berbasis AI",
  icons: {
    icon: "/images/logo-tab.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${lora.variable} ${geistSans.variable} ${geistMono.variable} antialiased bg-[var(--pemali-bg)] text-[var(--pemali-text-primary)] min-h-screen flex flex-col font-sans`}>
        <NarrativeStream />
        {children}
      </body>
    </html>
  );
}
