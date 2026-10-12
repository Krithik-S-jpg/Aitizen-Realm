import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aitizen Observatory · Your world, in view",
  description: "A private observatory for the lives, discoveries and stories of Aitizen Realm.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
