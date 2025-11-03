"use client";

import { Layout, Menu } from "antd";
import Link from "next/link";
import { AntdRegistry } from "@ant-design/nextjs-registry";

const { Header, Footer, Content } = Layout;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0 }}>
        <AntdRegistry>
          <Layout style={{ minHeight: "100vh" }}>
            <Header style={{ display: "flex", alignItems: "center" }}>
              <div style={{ color: "white", fontSize: "20px", marginRight: "40px", fontWeight: "bold" }}>
                Sosse
              </div>
              <Menu
                theme="dark"
                mode="horizontal"
                style={{ flex: 1, minWidth: 0 }}
                items={[
                  { key: "home", label: <Link href="/">Search</Link> },
                  { key: "archive", label: <Link href="/archive/http://saved.page.com">Archive</Link> },
                  { key: "help", label: <Link href="/help">Help</Link> },
                  { key: "admin", label: <Link href="/admin/dashboard">Admin</Link> },
                  { key: "login", label: <Link href="/login">Login</Link> },
                ]}
              />
            </Header>
            <Content style={{ padding: "24px" }}>{children}</Content>
            <Footer style={{ textAlign: "center" }}>
              Sosse ©{new Date().getFullYear()} - Archive Search Platform
            </Footer>
          </Layout>
        </AntdRegistry>
      </body>
    </html>
  );
}
