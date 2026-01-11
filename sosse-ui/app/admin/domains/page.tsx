"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import { Button, Typography, Input, Space, Tag } from "antd";
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

interface Domain {
  id: number;
  domain: string;
  browse_mode: string;
  robots_status: string;
  robots_ua_hash: string;
  robots_allow: string;
  robots_disallow: string;
  ignore_robots: boolean;
}

const browseModeLabels: Record<string, string> = {
  detect: "Detect",
  selenium: "Chromium",
  firefox: "Firefox",
  requests: "Python Requests",
};

const robotsStatusLabels: Record<string, string> = {
  unknown: "Unknown",
  empty: "Empty",
  loaded: "Loaded",
};

export default function DomainsPage() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [loading, setLoading] = useState(true);
  const [tableParams, setTableParams] = useState<TableParams<Domain>>({
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

  const fetchDomains = useCallback(
    async (search?: string) => {
      try {
        setLoading(true);

        const response = await axios.get<PaginatedResponse<Domain>>(
          "/api/domain/",
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
        setDomains(response.data.results);
        setTotalCount(response.data.count);
      } catch (error) {
        console.error("Error fetching domains:", error);
      } finally {
        setLoading(false);
      }
    },
    [tableParams.pagination, tableParams.sortField, tableParams.sortOrder],
  );

  useEffect(() => {
    fetchDomains();
  }, [fetchDomains]);

  const handleSearch = (value: string) => {
    setSearchValue(value);
    fetchDomains(value);
  };

  const columns = [
    {
      title: "Domain",
      dataIndex: "domain",
      key: "domain",
      sorter: true,
    },
    {
      title: "Browse Mode",
      dataIndex: "browse_mode",
      key: "browse_mode",
      sorter: true,
      width: 150,
      render: (browse_mode: string) =>
        browseModeLabels[browse_mode] || browse_mode,
    },
    {
      title: "Robots.txt Status",
      dataIndex: "robots_status",
      key: "robots_status",
      sorter: true,
      width: 150,
      render: (robots_status: string) => {
        const color =
          robots_status === "loaded"
            ? "green"
            : robots_status === "empty"
              ? "orange"
              : "default";
        return (
          <Tag color={color}>
            {robotsStatusLabels[robots_status] || robots_status}
          </Tag>
        );
      },
    },
    {
      title: "Ignore Robots",
      dataIndex: "ignore_robots",
      key: "ignore_robots",
      sorter: true,
      width: 120,
      render: (ignore_robots: boolean) => (ignore_robots ? "Yes" : "No"),
    },
  ];

  const handleTableChange: TableProps<Domain>["onChange"] = (
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
      setDomains([]);
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
    fetchDomains(searchValue);
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
      confirmTitle: (count: number) => `Delete ${count} domain(s)`,
      confirmContent: (count: number) =>
        `Are you sure you want to delete ${count} domain(s)?`,
      successMessage: (count: number) =>
        `Successfully deleted ${count} domain(s)`,
      errorMessage: () => "Failed to delete domains",
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
          Domains
        </Title>
        <Space>
          <ActionDropdown
            actionItems={actionItems}
            selectedRowKeys={selectedRowKeys}
            totalCount={totalCount}
            selectAll={selectAll}
            apiEndpoint="/api/domain"
            searchValue={searchValue}
            itemName="domain"
            onActionComplete={handleActionComplete}
            actionProgress={actionProgress}
            onProgress={handleProgress}
            onCancelAction={handleCancelAction}
          />
          <Button type="primary" icon={<PlusOutlined />}>
            New Domain
          </Button>
        </Space>
      </div>
      <Input.Search
        placeholder="Search domains by name"
        prefix={<SearchOutlined />}
        style={{ marginBottom: "16px", maxWidth: "600px" }}
        onSearch={handleSearch}
        allowClear
        enterButton
      />
      <SelectTable
        columns={columns}
        dataSource={domains}
        loading={loading}
        totalCount={totalCount}
        tableParams={tableParams}
        onTableChange={handleTableChange}
        itemName="domain"
        selectedRowKeys={selectedRowKeys}
        selectAll={selectAll}
        onSelectionChange={handleSelectionChange}
      />
    </div>
  );
}
