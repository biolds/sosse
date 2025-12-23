"use client";

import { ConfigProvider, theme, App } from "antd";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { useAppStore } from "@/app/hooks/useAppStore";
import AuthGuard from "@/app/AuthGuard";
import "@/lib/axios";
import "@/app/globals.css";
import FloatLayout from "./components/FloatLayout";

export default function ArchiveLayout({
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
            <App style={{ height: "100vh" }}>
              <AuthGuard>
                <FloatLayout>{children}</FloatLayout>
              </AuthGuard>
            </App>
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  );
}
