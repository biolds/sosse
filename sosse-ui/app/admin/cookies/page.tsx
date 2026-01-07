"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import {
  Table,
  Button,
  Typography,
  Input,
  Space,
  Alert,
  Dropdown,
  Modal,
  Progress,
  App,
} from "antd";
import type { GetProp, TableProps, TableRowSelection } from "antd";
import type { SorterResult } from "antd/es/table/interface";
import { PlusOutlined, SearchOutlined, DownOutlined } from "@ant-design/icons";
import type { MenuProps } from "antd";
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

interface ActionConfig {
  key: string;
  label: string;
  danger?: boolean;
  confirmTitle: (count: number) => string;
  confirmContent: (count: number) => string;
  successMessage: (count: number) => string;
  errorMessage: () => string;
  progressMessage: () => string;
  onClick: () => void;
}

export default function CookiesPage() {
  const { modal, message } = App.useApp();
  const [cookies, setCookies] = useState<Cookie[]>([]);
  const [loading, setLoading] = useState(true);
  const [tableParams, setTableParams] = useState<TableParams>({
    pagination: {
      current: 1,
      pageSize: 10,
    },
  });
  const [totalCount, setTotalCount] = useState(0);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectAll, setSelectAll] = useState(false);
  const [searchValue, setSearchValue] = useState<string>("");
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
        message.error("Failed to load cookies");
        console.error("Error fetching cookies:", error);
      } finally {
        setLoading(false);
      }
    },
    [
      message,
      tableParams.pagination,
      tableParams.sortField,
      tableParams.sortOrder,
    ],
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

    if (pagination.pageSize !== tableParams.pagination?.pageSize) {
      setCookies([]);
    }
  };

  const handleSelectAllPages = () => {
    setSelectAll(true);
    message.success(`Selected all ${totalCount} cookies`);
  };

  const handleActionSelected = async (actionKey: string) => {
    if (selectedRowKeys.length === 0 && !selectAll) {
      message.warning("No cookies selected");
      return;
    }

    const actionConfig = actionItems.find((item) => item?.key === actionKey) as
      | ActionConfig
      | undefined;
    if (!actionConfig) return;

    const confirmModal = modal.confirm({
      title: actionConfig.confirmTitle(
        selectAll ? totalCount : selectedRowKeys.length,
      ),
      content: actionConfig.confirmContent(
        selectAll ? totalCount : selectedRowKeys.length,
      ),
      okText: actionConfig.label,
      okType: actionConfig.danger ? "danger" : "primary",
      onOk: async () => {
        confirmModal.destroy();
        if (selectAll) {
          await handleActionAllWithProgress(actionKey, actionConfig);
        } else {
          await handleActionBatch(
            actionKey,
            actionConfig,
            selectedRowKeys as number[],
          );
        }
      },
    });
  };

  const handleActionBatch = async (
    action: string,
    actionConfig: ActionConfig,
    ids: number[],
  ) => {
    try {
      await axios.post("/api/cookie/action/", {
        action,
        ids,
      });
      message.success(actionConfig.successMessage(ids.length));
      setSelectedRowKeys([]);
      setSelectAll(false);
      fetchCookies(searchValue);
    } catch (error) {
      message.error(actionConfig.errorMessage());
      console.error(`Error performing ${action} on cookies:`, error);
    }
  };

  const handleActionAllWithProgress = async (
    action: string,
    actionConfig: ActionConfig,
  ) => {
    cancelActionRef.current = false;
    setActionProgress({
      visible: true,
      current: 0,
      total: totalCount,
      message: actionConfig.progressMessage(),
    });

    try {
      const batchSize = 100;
      let offset = 0;
      let processedCount = 0;

      while (offset < totalCount && !cancelActionRef.current) {
        const response = await axios.get<PaginatedResponse<{ id: number }>>(
          "/api/cookie/",
          {
            params: {
              ...(searchValue ? { search: searchValue } : {}),
              ids_only: 1,
              offset: 0,
              limit: batchSize,
            },
          },
        );

        if (response.data.results.length === 0) break;

        const ids = response.data.results.map((cookie) => cookie.id);

        await axios.post("/api/cookie/action/", {
          action,
          ids,
        });

        processedCount += ids.length;
        offset += batchSize;

        setActionProgress((prev) => ({
          ...prev,
          current: processedCount,
        }));
      }

      setActionProgress({ visible: false, current: 0, total: 0, message: "" });

      if (cancelActionRef.current) {
        message.info(
          `Action cancelled. ${processedCount} cookie(s) were processed.`,
        );
      } else {
        message.success(actionConfig.successMessage(processedCount));
      }

      setSelectedRowKeys([]);
      setSelectAll(false);
      fetchCookies(searchValue);
    } catch (error) {
      setActionProgress({ visible: false, current: 0, total: 0, message: "" });
      message.error(actionConfig.errorMessage());
      console.error(`Error performing ${action} on cookies:`, error);
    }
  };

  const handleCancelAction = () => {
    console.log("canceled");
    cancelActionRef.current = true;
  };

  const rowSelection: TableRowSelection<Cookie> = {
    selectedRowKeys,
    onChange: (selectedKeys) => {
      setSelectedRowKeys(selectedKeys);
      setSelectAll(false);
    },
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
      onClick: () => handleActionSelected("delete"),
    },
  ];

  const menuItems: MenuProps["items"] = actionItems.map((action) => ({
    key: action.key,
    label: action.label,
    danger: action.danger,
    onClick: action.onClick,
  }));

  const hasSelection = selectedRowKeys.length > 0 || selectAll;

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
          <Dropdown
            menu={{ items: menuItems }}
            trigger={["click"]}
            disabled={!hasSelection}
          >
            <Button disabled={!hasSelection}>
              Actions <DownOutlined />
            </Button>
          </Dropdown>
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
      {selectedRowKeys.length > 0 && !selectAll ? (
        <Alert
          title={
            <Space>
              <span>{selectedRowKeys.length} selected</span>
              <Button type="link" size="small" onClick={handleSelectAllPages}>
                Select all {totalCount} cookies
              </Button>
            </Space>
          }
          type="info"
          style={{ marginBottom: "16px" }}
        />
      ) : selectAll ? (
        <Alert
          title={
            <Space>
              <span>All {totalCount} cookies selected</span>
              <Button
                type="link"
                size="small"
                onClick={() => {
                  setSelectAll(false);
                  setSelectedRowKeys([]);
                }}
              >
                Clear selection
              </Button>
            </Space>
          }
          type="info"
          style={{ marginBottom: "16px" }}
        />
      ) : null}

      <Table
        columns={columns}
        dataSource={cookies}
        rowKey="id"
        rowSelection={rowSelection}
        pagination={{
          ...tableParams.pagination,
          total: totalCount,
          showSizeChanger: true,
          showTotal: (total) =>
            `Total ${total} cookies${selectAll ? ` (all ${totalCount} selected)` : selectedRowKeys.length > 0 ? ` (${selectedRowKeys.length} selected)` : ""}`,
        }}
        loading={loading}
        onChange={handleTableChange}
      />

      <Modal
        title="Processing cookies"
        open={actionProgress.visible}
        footer={[
          <Button key="cancel" onClick={handleCancelAction}>
            Cancel
          </Button>,
        ]}
        closable={false}
      >
        <Progress
          percent={Math.round(
            (actionProgress.current / actionProgress.total) * 100,
          )}
          status="active"
        />
        <p style={{ marginTop: "16px", textAlign: "center" }}>
          {actionProgress.message}
        </p>
      </Modal>
    </div>
  );
}
