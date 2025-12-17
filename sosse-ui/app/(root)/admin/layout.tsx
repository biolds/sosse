"use client";

import { Layout, Menu } from "antd";
import Link from "next/link";
import {
  DashboardOutlined,
  BarChartOutlined,
  FolderOutlined,
  TagsOutlined,
  AppstoreOutlined,
} from "@ant-design/icons";

const { Sider, Content } = Layout;

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const menuItems = [
    {
      key: "dashboard",
      icon: <DashboardOutlined />,
      label: <Link href="/admin/dashboard">Dashboard</Link>,
    },
    {
      key: "analytics",
      icon: <BarChartOutlined />,
      label: <Link href="/admin/analytics">Analytics</Link>,
    },
    {
      key: "collections",
      icon: <FolderOutlined />,
      label: <Link href="/admin/collections">Collections</Link>,
    },
    {
      key: "tags",
      icon: <TagsOutlined />,
      label: <Link href="/admin/tags">Tags</Link>,
    },
    {
      key: "cookies",
      icon: <AppstoreOutlined />,
      label: <Link href="/admin/cookies">Cookies</Link>,
    },
  ];

  return (
    <Layout style={{ minHeight: "calc(100vh - 134px)" }}>
      <Sider width={240} theme="light">
        <div style={{ padding: "16px", fontSize: "18px", fontWeight: "bold" }}>
          Admin Panel
        </div>
        <Menu
          mode="inline"
          defaultSelectedKeys={["dashboard"]}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Content style={{ margin: "24px" }}>{children}</Content>
      </Layout>
    </Layout>
  );
}
