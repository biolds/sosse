"use client";

import React from "react";
import Link from "next/link";
import { Layout, Menu, Button } from "antd";
import {
  MoonOutlined,
  SunOutlined,
  UserOutlined,
  LogoutOutlined,
  LoginOutlined,
} from "@ant-design/icons";
import { useAppStore } from "@/app/hooks/useAppStore";

const { Header } = Layout;

type SosseHeaderProps = {
  style?: React.CSSProperties;
};

const SosseHeader: React.FC<SosseHeaderProps> = ({ style }) => {
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
    <Header style={{ ...style, display: "flex", alignItems: "center" }}>
      <div
        style={{
          color: "white",
          fontSize: "20px",
          marginRight: "40px",
          fontWeight: "bold",
        }}
      >
        <Link href="/">Sosse</Link>
      </div>
      <Menu
        theme="dark"
        mode="horizontal"
        style={{ flex: 1, minWidth: 0 }}
        items={[
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
  );
};

export default React.memo(SosseHeader);
