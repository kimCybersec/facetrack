import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import { ScanFace, Camera, Users, Radio } from "lucide-react";
import { Providers } from "./providers";
import "./globals.css";

const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display", weight: ["500", "700"] });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "FaceTrack — Gate Access Control",
  description: "AI-powered facial recognition access control for campus gates.",
};

const navItems = [
  { href: "/gate-monitor", label: "Gate Monitor", icon: Radio },
  { href: "/cameras", label: "Cameras", icon: Camera },
  { href: "/students", label: "Students", icon: Users },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body className="bg-[#0a0d12] text-[#e8ecef] font-body antialiased">
        <Providers>
          <div className="flex min-h-screen">
            <aside className="w-60 shrink-0 border-r border-[#1e252d] bg-[#0d1116] flex flex-col">
              <div className="flex items-center gap-2 px-5 py-5 border-b border-[#1e252d]">
                <ScanFace className="h-6 w-6 text-[#3ecf8e]" strokeWidth={1.75} />
                <span className="font-display font-bold text-lg tracking-tight">FaceTrack</span>
              </div>
              <nav className="flex-1 px-3 py-4 space-y-1">
                {navItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm text-[#a7b0b8] hover:text-[#e8ecef] hover:bg-[#161b21] transition-colors"
                  >
                    <item.icon className="h-4 w-4" strokeWidth={1.75} />
                    {item.label}
                  </Link>
                ))}
              </nav>
              <div className="px-5 py-4 border-t border-[#1e252d] text-[11px] text-[#5c6570] font-mono">
                <div className="flex items-center gap-1.5">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#3ecf8e] opacity-75" />
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#3ecf8e]" />
                  </span>
                  SYSTEM ONLINE
                </div>
              </div>
            </aside>
            <main className="flex-1 min-w-0">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
