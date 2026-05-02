import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "RSCdata - 金融人才档案库",
  description: "基于中证协(SAC)与中基协(AMAC)数据的专业检索平台，助力上市公司IR团队高效建立投资者档案。",
  icons: {
    icon: "https://www.roadshowchina.cn/w/images/logo-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body suppressHydrationWarning className={`${inter.variable} font-sans antialiased bg-[#FAFAFA] text-slate-900 selection:bg-slate-200 selection:text-slate-900`}>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:bg-white focus:text-slate-900 focus:border focus:border-slate-200 focus:px-4 focus:py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
        >
          跳到主内容
        </a>
        <Navbar />
        <main id="main-content" className="pt-16 scroll-mt-16">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
