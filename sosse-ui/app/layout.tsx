"use client";

import "@ant-design/v5-patch-for-react-19";
import { Layout, Menu, Button, ConfigProvider, theme, App } from "antd";
import Link from "next/link";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { useAppStore } from "./useAppStore";
import {
  MoonOutlined,
  SunOutlined,
  UserOutlined,
  LogoutOutlined,
  LoginOutlined,
} from "@ant-design/icons";
import AuthGuard from "./AuthGuard";
import "../lib/axios";
import "./globals.css";

const { Header, Footer, Content } = Layout;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isDarkMode, toggleDarkMode, username, logout } = useAppStore();

  const handleLogout = async () => {
    await logout();
    // Force a full page reload to reset all state
    window.location.href = "/";
  };

  const authMenuItem = username
    ? {
        key: "user-menu",
        label: (
          <span>
            <UserOutlined /> {username}
          </span>
        ),
        children: [
          {
            key: "logout",
            label: (
              <span onClick={handleLogout}>
                <LogoutOutlined /> Logout
              </span>
            ),
          },
        ],
      }
    : {
        key: "login",
        label: (
          <Link href="/login">
            <LoginOutlined /> Login
          </Link>
        ),
      };

  return (
    <html lang="en">
      <head>
        <script src="/config.js" async></script>
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
                  <Header style={{ display: "flex", alignItems: "center" }}>
                    <div
                      style={{
                        color: "white",
                        fontSize: "20px",
                        marginRight: "40px",
                        fontWeight: "bold",
                      }}
                    >
                      Sosse
                    </div>
                    <Menu
                      theme="dark"
                      mode="horizontal"
                      style={{ flex: 1, minWidth: 0 }}
                      items={[
                        { key: "home", label: <Link href="/">Search</Link> },
                        {
                          key: "archive",
                          label: (
                            <Link href="/archive/http://saved.page.com">
                              Archive
                            </Link>
                          ),
                        },
                        { key: "help", label: <Link href="/help">Help</Link> },
                        {
                          key: "admin",
                          label: <Link href="/admin/dashboard">Admin</Link>,
                        },
                        authMenuItem,
                      ]}
                    />
                    <Button
                      type="text"
                      icon={isDarkMode ? <SunOutlined /> : <MoonOutlined />}
                      onClick={toggleDarkMode}
                      style={{ marginLeft: "20px", color: "white" }}
                    />
                  </Header>
                  <Content style={{ padding: "24px" }}>{children}</Content>
                  <Footer style={{ textAlign: "center" }}>
                    Sosse ©{new Date().getFullYear()} - Archive Search Platform
                  </Footer>
                </Layout>
              </AuthGuard>
            </App>
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  );
}
