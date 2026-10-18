import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

// Base des URL absolues des images de partage (opengraph-image.png, twitter-image.png).
export const metadata: Metadata = { metadataBase: new URL("https://ezshell.vercel.app") };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
