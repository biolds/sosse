"use client";

import { Layout, ConfigProvider, theme, App } from "antd";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { useAppStore } from "@/app/hooks/useAppStore";
import AuthGuard from "@/app/AuthGuard";
import Header from "@/app/components/Header";
import Footer from "@/app/components/Footer";
import "@/lib/axios";
import "@/app/globals.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isDarkMode } = useAppStore();

  return (
    <html lang="en">
      <head>
        {/* eslint-disable-next-line @next/next/no-sync-scripts */}
        <script src="/config.js"></script>
      </head>
      <body style={{ margin: 0 }} className={isDarkMode ? "dark-mode" : ""}>
        <AntdRegistry>
          <ConfigProvider
            theme={{
              algorithm: isDarkMode
                ? theme.darkAlgorithm
                : theme.defaultAlgorithm,
            }}
          >
            <App>
              <AuthGuard>
                <Layout style={{ minHeight: "100vh" }}>
                  <Header />
                  {children}
                  <Footer />
                </Layout>
              </AuthGuard>
            </App>
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  );
}
