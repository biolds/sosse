"use client";

import { Table, Button, Space, Typography, Tag, Input } from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
} from "@ant-design/icons";

const { Title } = Typography;

export default function TagsPage() {
  const columns = [
    {
      title: "Tag",
      dataIndex: "tag",
      key: "tag",
      render: (text: string, record: { color?: string }) => (
        <Tag color={record.color}>{text}</Tag>
      ),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
    },
    {
      title: "Usage Count",
      dataIndex: "count",
      key: "count",
      width: 150,
    },
    {
      title: "Actions",
      key: "actions",
      width: 150,
      render: () => (
        <Space>
          <Button icon={<EditOutlined />} size="small">
            Edit
          </Button>
          <Button icon={<DeleteOutlined />} size="small" danger>
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  const data = [
    {
      key: "1",
      tag: "Technology",
      description: "Tech-related content",
      count: 2341,
      color: "blue",
    },
    {
      key: "2",
      tag: "Science",
      description: "Scientific articles",
      count: 1892,
      color: "green",
    },
    {
      key: "3",
      tag: "Business",
      description: "Business and finance",
      count: 1543,
      color: "orange",
    },
    {
      key: "4",
      tag: "Education",
      description: "Educational resources",
      count: 982,
      color: "purple",
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        <Title level={2} style={{ margin: 0 }}>
          Tags
        </Title>
        <Button type="primary" icon={<PlusOutlined />}>
          New Tag
        </Button>
      </div>
      <Input
        placeholder="Search tags..."
        prefix={<SearchOutlined />}
        style={{ marginBottom: "16px", maxWidth: "400px" }}
      />
      <Table columns={columns} dataSource={data} />
    </div>
  );
}
