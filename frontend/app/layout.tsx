import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import Link from "next/link";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "LLM Chatbot",
  description: "Multi-provider LLM chatbot with inference logging",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <div className="flex h-screen flex-col">
          <header className="flex items-center gap-6 border-b px-6 py-3 shrink-0">
            <span className="font-semibold text-sm">LLM Chatbot</span>
            <nav className="flex gap-4 text-sm text-muted-foreground">
              <Link href="/conversations" className="hover:text-foreground transition-colors">
                Conversations
              </Link>
              <Link href="/dashboard" className="hover:text-foreground transition-colors">
                Dashboard
              </Link>
            </nav>
          </header>
          <main className="flex-1 min-h-0">{children}</main>
        </div>
      </body>
    </html>
  );
}
