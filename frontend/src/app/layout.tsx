import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import Script from "next/script";
import { Suspense } from "react";

import { LanguageToggle } from "@/components/common/LanguageToggle";
import { ThemeToggle } from "@/components/common/ThemeToggle";
import { SearchBar } from "@/components/search/SearchBar";

import "./globals.css";

// Applies persisted/OS theme synchronously before React hydrates, so users
// don't see a flash of light mode when they have the dark preference.
const THEME_INIT = `
(function(){try{
  var s = localStorage.getItem('biograph.theme');
  var t = s === 'light' || s === 'dark'
    ? s
    : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.classList.toggle('dark', t === 'dark');
  document.documentElement.style.colorScheme = t;
}catch(_){}})();
`;

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "BioGraph",
  description: "Biopharma knowledge compilation — drugs, targets, companies, stories.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <Script id="theme-init" strategy="beforeInteractive">
          {THEME_INIT}
        </Script>
      </head>
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-20 flex items-center gap-6 border-b border-zinc-200 bg-white/90 px-6 py-3 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/90">
          <Link href="/" className="text-base font-semibold tracking-tight">
            BioGraph
          </Link>
          <Suspense fallback={<div className="h-9 w-full max-w-md" />}>
            <SearchBar />
          </Suspense>
          <div className="ml-auto flex items-center gap-3">
            <Suspense fallback={null}>
              <LanguageToggle />
            </Suspense>
            <ThemeToggle />
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
