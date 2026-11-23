import type { Metadata } from "next";
import type { ReactNode } from "react";
import localFont from "next/font/local";
import InteractiveBackground from "./InteractiveBackground";
import ThemeToggle from "./ThemeToggle";
import "./globals.css";

// Polices auto-hébergées via Fontsource : le build ne dépend plus de fonts.googleapis.com.
const spaceGrotesk = localFont({
  src: "../node_modules/@fontsource-variable/space-grotesk/files/space-grotesk-latin-wght-normal.woff2",
  variable: "--font-heading",
  display: "swap",
  weight: "300 700",
});

const inter = localFont({
  src: "../node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2",
  variable: "--font-sans",
  display: "swap",
  weight: "100 900",
});

const jetbrainsMono = localFont({
  src: [
    { path: "../node_modules/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-400-normal.woff2", weight: "400", style: "normal" },
    { path: "../node_modules/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-500-normal.woff2", weight: "500", style: "normal" },
    { path: "../node_modules/@fontsource/jetbrains-mono/files/jetbrains-mono-latin-600-normal.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-mono",
  display: "swap",
});

// Base des URL absolues des images de partage (opengraph-image.png, twitter-image.png).
export const metadata: Metadata = {
  metadataBase: new URL("https://ezshell.vercel.app"),
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "32x32" },
    ],
    apple: "/apple-icon.png",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning className={`${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("ezshell-theme");if(t!=="light"&&t!=="dark"){t=matchMedia("(prefers-color-scheme: light)").matches?"light":"dark"}document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="dark"}})();`,
          }}
        />
      </head>
      <body>
        <InteractiveBackground />
        {children}
        <ThemeToggle />
      </body>
    </html>
  );
}
