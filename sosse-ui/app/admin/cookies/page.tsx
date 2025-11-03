"use client";

import { Table, Button, Space, Typography, Input } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from "@ant-design/icons";

const { Title } = Typography;

export default function CookiesPage() {
  const columns = [
    {
      title: "Domain",
      dataIndex: "domain",
      key: "domain",
    },
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Value",
      dataIndex: "value",
      key: "value",
      ellipsis: true,
    },
    {
      title: "Expires",
      dataIndex: "expires",
      key: "expires",
      width: 150,
    },
    {
      title: "Actions",
      key: "actions",
      width: 150,
      render: () => (
        <Space>
          <Button icon={<EditOutlined />} size="small">Edit</Button>
          <Button icon={<DeleteOutlined />} size="small" danger>Delete</Button>
        </Space>
      ),
    },
  ];

  const data = [
    { key: "1", domain: "example.com", name: "session_id", value: "abc123xyz789", expires: "2024-12-31" },
    { key: "2", domain: "test.com", name: "auth_token", value: "def456uvw012", expires: "2024-11-30" },
    { key: "3", domain: "sample.org", name: "user_pref", value: "ghi789rst345", expires: "2025-01-15" },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <Title level={2} style={{ margin: 0 }}>Cookies</Title>
        <Button type="primary" icon={<PlusOutlined />}>
          New Cookie
        </Button>
      </div>
      <Input
        placeholder="Search cookies..."
        prefix={<SearchOutlined />}
        style={{ marginBottom: "16px", maxWidth: "400px" }}
      />
      <Table columns={columns} dataSource={data} />
    </div>
  );
}
