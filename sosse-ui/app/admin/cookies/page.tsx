"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import { Button, Typography, Input, Space } from "antd";
import type { TableProps } from "antd";
import { PlusOutlined, SearchOutlined } from "@ant-design/icons";
import axios from "axios";
import type { PaginatedResponse } from "@/app/types/restResponse";
import SelectTable, {
  type TableParams,
} from "@/app/admin/components/SelectTable";
import ActionDropdown, {
  type ActionConfig,
} from "@/app/admin/components/ActionDropdown";

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

export default function CookiesPage() {
  const [cookies, setCookies] = useState<Cookie[]>([]);
  const [loading, setLoading] = useState(true);
  const [tableParams, setTableParams] = useState<TableParams<Cookie>>({
    pagination: {
      current: 1,
      pageSize: 10,
    },
  });
  const [totalCount, setTotalCount] = useState(0);
  const [searchValue, setSearchValue] = useState<string>("");
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectAll, setSelectAll] = useState(false);
  const [actionProgress, setActionProgress] = useState<{
    visible: boolean;
    current: number;
    total: number;
    message: string;
  }>({ visible: false, current: 0, total: 0, message: "" });
  const cancelActionRef = useRef(false);

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
    setSearchValue(value);
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

    if (
      pagination &&
      pagination.pageSize !== tableParams.pagination?.pageSize
    ) {
      setCookies([]);
    }
  };

  const handleSelectionChange = (
    keys: React.Key[],
    selectAllPages: boolean,
  ) => {
    setSelectedRowKeys(keys);
    setSelectAll(selectAllPages);
  };

  const handleActionComplete = () => {
    setSelectedRowKeys([]);
    setSelectAll(false);
    fetchCookies(searchValue);
  };

  const handleProgress = (
    visible: boolean,
    current: number,
    total: number,
    message: string,
  ) => {
    setActionProgress({ visible, current, total, message });
  };

  const handleCancelAction = () => {
    cancelActionRef.current = true;
  };

  const actionItems: ActionConfig[] = [
    {
      key: "delete",
      label: "Delete",
      danger: true,
      confirmTitle: (count: number) => `Delete ${count} cookie(s)`,
      confirmContent: (count: number) =>
        `Are you sure you want to delete ${count} cookie(s)?`,
      successMessage: (count: number) =>
        `Successfully deleted ${count} cookie(s)`,
      errorMessage: () => "Failed to delete cookies",
      progressMessage: () => "Deletion in progress...",
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
        <Space>
          <ActionDropdown
            actionItems={actionItems}
            selectedRowKeys={selectedRowKeys}
            totalCount={totalCount}
            selectAll={selectAll}
            apiEndpoint="/api/cookie"
            searchValue={searchValue}
            itemName="cookie"
            onActionComplete={handleActionComplete}
            actionProgress={actionProgress}
            onProgress={handleProgress}
            onCancelAction={handleCancelAction}
          />
          <Button type="primary" icon={<PlusOutlined />}>
            New Cookie
          </Button>
        </Space>
      </div>
      <Input.Search
        placeholder="Search cookies by domain/path or enter URL (http://...)"
        prefix={<SearchOutlined />}
        style={{ marginBottom: "16px", maxWidth: "600px" }}
        onSearch={handleSearch}
        allowClear
        enterButton
      />
      <SelectTable
        columns={columns}
        dataSource={cookies}
        loading={loading}
        totalCount={totalCount}
        tableParams={tableParams}
        onTableChange={handleTableChange}
        itemName="cookie"
        selectedRowKeys={selectedRowKeys}
        selectAll={selectAll}
        onSelectionChange={handleSelectionChange}
      />
    </div>
  );
}
