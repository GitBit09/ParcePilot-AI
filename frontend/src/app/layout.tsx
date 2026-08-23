import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AuthProvider } from "@/lib/auth-context";
import "@/styles/globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "ParcelPilot AI | Smart Logistics Support",
  description:
    "AI-powered support agent for ParcelPilot — instant answers, policy lookups, and real-time operations insights.",
  keywords: ["logistics", "AI support", "ParcelPilot", "shipping"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
