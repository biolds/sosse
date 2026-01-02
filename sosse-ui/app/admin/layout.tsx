"use client";

import { Layout, Menu } from "antd";
import Link from "next/link";
import {
  ApiOutlined,
  DashboardOutlined,
  BarChartOutlined,
  FolderOutlined,
  TagsOutlined,
  CoffeeOutlined,
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
      key: "collection",
      icon: <FolderOutlined />,
      label: <Link href="/admin/collection">Collections</Link>,
    },
    {
      key: "tags",
      icon: <TagsOutlined />,
      label: <Link href="/admin/tags">Tags</Link>,
    },
    {
      key: "cookies",
      icon: <CoffeeOutlined />,
      label: <Link href="/admin/cookies">Cookies</Link>,
    },
    {
      key: "rest",
      icon: <ApiOutlined />,
      label: <Link href="/swagger/">Rest API</Link>,
    },
  ];

  return (
    <Layout style={{ minHeight: "calc(100vh - 134px)" }}>
      <Sider width={240} theme="light">
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
