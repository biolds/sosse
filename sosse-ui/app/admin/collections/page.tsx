"use client";

import { Table, Button, Space, Typography, Input } from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from "@ant-design/icons";

const { Title } = Typography;

export default function CollectionsPage() {
  const columns = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
    },
    {
      title: "Pages",
      dataIndex: "pages",
      key: "pages",
      width: 100,
    },
    {
      title: "Created",
      dataIndex: "created",
      key: "created",
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
    { key: "1", name: "Research", description: "Academic research papers", pages: 1243, created: "2024-01-15" },
    { key: "2", name: "News", description: "News articles archive", pages: 5621, created: "2024-02-20" },
    { key: "3", name: "Documentation", description: "Technical documentation", pages: 892, created: "2024-03-10" },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <Title level={2} style={{ margin: 0 }}>Collections</Title>
        <Button type="primary" icon={<PlusOutlined />}>
          New Collection
        </Button>
      </div>
      <Input
        placeholder="Search collections..."
        prefix={<SearchOutlined />}
        style={{ marginBottom: "16px", maxWidth: "400px" }}
      />
      <Table columns={columns} dataSource={data} />
    </div>
  );
}
