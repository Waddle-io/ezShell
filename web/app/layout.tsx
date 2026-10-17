import type { ReactNode } from "react";

export const metadata = { title: "ezShell", description: "Un terminal intelligent qui explique vos erreurs." };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: "4rem auto", maxWidth: 640, padding: "0 1rem" }}>
        {children}
      </body>
    </html>
  );
}
