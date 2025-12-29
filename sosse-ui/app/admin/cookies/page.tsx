"use client";

import { useState, useEffect } from "react";
import { Table, Button, Typography, Input, Spin, message } from "antd";
import { PlusOutlined, SearchOutlined } from "@ant-design/icons";
import axios from "axios";

const { Title } = Typography;

interface Cookie {
  id: number;
  domain: string;
  domain_cc: string | null;
  inc_subdomain: boolean;
  name: string;
  value: string;
  path: string;
  expires: string | null;
  secure: boolean;
  same_site: string;
  http_only: boolean;
}

interface CookieResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Cookie[];
}

export default function CookiesPage() {
  const [cookies, setCookies] = useState<Cookie[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCookies = async (search?: string) => {
    try {
      setLoading(true);
      const params = search ? { search } : {};
      const response = await axios.get<CookieResponse>("/api/cookie/", {
        params,
      });
      setCookies(response.data.results);
    } catch (error) {
      message.error("Failed to load cookies");
      console.error("Error fetching cookies:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCookies();
  }, []);

  const handleSearch = (value: string) => {
    fetchCookies(value);
  };

  const columns = [
    {
      title: "Domain",
      dataIndex: "domain",
      key: "domain",
    },
    {
      title: "Domain CC",
      dataIndex: "domain_cc",
      key: "domain_cc",
      width: 120,
    },
    {
      title: "Path",
      dataIndex: "path",
      key: "path",
      width: 100,
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
      render: (expires: string | null) =>
        expires ? new Date(expires).toLocaleString() : "-",
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
          Cookies
        </Title>
        <Button type="primary" icon={<PlusOutlined />}>
          New Cookie
        </Button>
      </div>
      <Input.Search
        placeholder="Search cookies by domain/path or enter URL (http://...)"
        prefix={<SearchOutlined />}
        style={{ marginBottom: "16px", maxWidth: "600px" }}
        onSearch={handleSearch}
        allowClear
        enterButton
      />
      <Spin spinning={loading}>
        <Table
          columns={columns}
          dataSource={cookies}
          rowKey="id"
          pagination={{
            pageSize: 50,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} cookies`,
          }}
        />
      </Spin>
    </div>
  );
}
