"use client";

import { useCallback, useState, useEffect } from "react";
import { Table, Button, Typography, Input, message } from "antd";
import type { GetProp, TableProps } from "antd";
import type { SorterResult } from "antd/es/table/interface";
import { PlusOutlined, SearchOutlined } from "@ant-design/icons";
import axios from "axios";
import type { PaginatedResponse } from "@/app/types/restResponse";

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

type TablePaginationConfig = Exclude<
  GetProp<TableProps, "pagination">,
  boolean
>;

interface TableParams {
  pagination?: TablePaginationConfig;
  sortField?: SorterResult<Cookie>["field"];
  sortOrder?: SorterResult<Cookie>["order"];
  filters?: Parameters<GetProp<TableProps, "onChange">>[1];
}

export default function CookiesPage() {
  const [cookies, setCookies] = useState<Cookie[]>([]);
  const [loading, setLoading] = useState(true);
  const [tableParams, setTableParams] = useState<TableParams>({
    pagination: {
      current: 1,
      pageSize: 10,
    },
  });
  const [totalCount, setTotalCount] = useState(0);

  const fetchCookies = useCallback(
    async (search?: string) => {
      try {
        setLoading(true);

        const response = await axios.get<PaginatedResponse<Cookie>>(
          "/api/cookie/",
          {
            params: {
              ...(search ? { search } : {}),
              ...(tableParams.pagination
                ? {
                    offset:
                      ((tableParams.pagination?.current || 0) - 1) *
                      (tableParams.pagination?.pageSize || 10),
                    limit: tableParams.pagination?.pageSize || 10,
                  }
                : {}),
              ...(tableParams.sortField
                ? {
                    ordering:
                      (tableParams.sortOrder === "ascend" ? "" : "-") +
                      tableParams.sortField,
                  }
                : {}),
            },
          },
        );
        setCookies(response.data.results);
        setTotalCount(response.data.count);
      } catch (error) {
        message.error("Failed to load cookies");
        console.error("Error fetching cookies:", error);
      } finally {
        setLoading(false);
      }
    },
    [tableParams.pagination, tableParams.sortField, tableParams.sortOrder],
  );

  useEffect(() => {
    fetchCookies();
  }, [fetchCookies]);

  const handleSearch = (value: string) => {
    fetchCookies(value);
  };

  const columns = [
    {
      title: "Domain",
      dataIndex: "domain",
      key: "domain",
      sorter: true,
    },
    {
      title: "Domain CC",
      dataIndex: "domain_cc",
      key: "domain_cc",
      sorter: true,
      width: 120,
    },
    {
      title: "Path",
      dataIndex: "path",
      key: "path",
      sorter: true,
      width: 100,
    },
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
    },
    {
      title: "Value",
      dataIndex: "value",
      key: "value",
      ellipsis: true,
      sorter: true,
    },
    {
      title: "Expires",
      dataIndex: "expires",
      key: "expires",
      sorter: true,
      width: 150,
      render: (expires: string | null) =>
        expires ? new Date(expires).toLocaleString() : "-",
    },
  ];

  const handleTableChange: TableProps<Cookie>["onChange"] = (
    pagination,
    filters,
    sorter,
  ) => {
    setTableParams({
      pagination,
      filters,
      sortOrder: Array.isArray(sorter) ? undefined : sorter.order,
      sortField: Array.isArray(sorter) ? undefined : sorter.field,
    });

    if (pagination.pageSize !== tableParams.pagination?.pageSize) {
      setCookies([]);
    }
  };

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
      <Table
        columns={columns}
        dataSource={cookies}
        rowKey="id"
        pagination={{
          ...tableParams.pagination,
          total: totalCount,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} cookies`,
        }}
        loading={loading}
        onChange={handleTableChange}
      />
    </div>
  );
}
