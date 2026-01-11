"use client";

import Link from "next/link";
import { useCallback, useState, useEffect } from "react";
import { Button, Typography, message } from "antd";
import type { TableProps } from "antd";
import {
  FileTextOutlined,
  PlusOutlined,
  BranchesOutlined,
  CalendarOutlined,
  CameraOutlined,
  GlobalOutlined,
  Html5Outlined,
  RetweetOutlined,
} from "@ant-design/icons";
import axios from "axios";
import type { PaginatedResponse } from "@/app/types/restResponse";
import type { Collection } from "@/app/types/collection";
import { humanDatetime, parseDurationToSeconds } from "@/app/utils/strings";
import SelectTable, {
  type TableParams,
} from "@/app/admin/components/SelectTable";

const { Title } = Typography;

export default function CollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [tableParams, setTableParams] = useState<TableParams<Collection>>({
    pagination: {
      current: 1,
      pageSize: 10,
    },
  });
  const [totalCount, setTotalCount] = useState(0);
  const [searchValue, setSearchValue] = useState<string>("");
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [selectAll, setSelectAll] = useState(false);

  const fetchCollections = useCallback(async () => {
    try {
      setLoading(true);

      const response = await axios.get<PaginatedResponse<Collection>>(
        "/api/collection/",
        {
          params: {
            ...(searchValue ? { search: searchValue } : {}),
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
      setCollections(response.data.results);
      setTotalCount(response.data.count);
    } catch (error) {
      message.error("Failed to load collections");
      console.error("Error fetching collections:", error);
    } finally {
      setLoading(false);
    }
  }, [
    searchValue,
    tableParams.pagination,
    tableParams.sortField,
    tableParams.sortOrder,
  ]);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  const handleSearch = (value: string) => {
    setSearchValue(value);
    setTableParams({
      ...tableParams,
      pagination: {
        ...tableParams.pagination,
        current: 1,
      },
    });
  };

  const getBrowserLabel = (collection: Collection) => {
    if (collection.default_browse_mode === "detect") {
      return `Chromium / Requests`;
    } else if (collection.default_browse_mode === "selenium") {
      return "Chromium";
    } else if (collection.default_browse_mode === "firefox") {
      return "Firefox";
    } else {
      return "Requests";
    }
  };

  const getRecursionLabel = (collection: Collection) => {
    if (collection.unlimited_regex_pg && collection.limited_regex_pg) {
      return `Unlimited / Depth ${collection.recursion_depth}`;
    } else if (collection.unlimited_regex_pg) {
      return "Unlimited";
    } else if (collection.limited_regex_pg) {
      return `Depth ${collection.recursion_depth}`;
    }
    return "None";
  };

  const getRecurrenceLabel = (collection: Collection) => {
    if (collection.recrawl_freq === "none") {
      return "Once";
    }
    if (collection.recrawl_freq === "constant" && collection.recrawl_dt_min) {
      return humanDatetime(parseDurationToSeconds(collection.recrawl_dt_min));
    }
    if (
      collection.recrawl_freq === "adaptive" &&
      collection.recrawl_dt_min &&
      collection.recrawl_dt_max
    ) {
      return `${humanDatetime(parseDurationToSeconds(collection.recrawl_dt_min))} ~ ${humanDatetime(parseDurationToSeconds(collection.recrawl_dt_max))}`;
    }
    return "-";
  };

  const columns = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      sorter: true,
    },
    {
      title: "Documents",
      dataIndex: "documents_count",
      key: "documents_count",
      width: 120,
      render: (count: number, collection: Collection) => (
        <Link href={`/?collection=${collection.id}`}>
          <FileTextOutlined style={{ marginRight: 4 }} />
          {count}
        </Link>
      ),
      sorter: true,
    },
    {
      title: "Recursion / Depth",
      key: "recursion",
      width: 180,
      render: (collection: Collection) => (
        <>
          <BranchesOutlined style={{ marginRight: 4 }} />
          {getRecursionLabel(collection)}
        </>
      ),
    },
    {
      title: "Browser",
      key: "browser",
      width: 150,
      render: (collection: Collection) => (
        <>
          <GlobalOutlined style={{ marginRight: 4 }} />
          {getBrowserLabel(collection)}
        </>
      ),
    },
    {
      title: "Recurrence",
      key: "recurrence",
      width: 150,
      render: (collection: Collection) => (
        <>
          <CalendarOutlined style={{ marginRight: 4 }} />
          {getRecurrenceLabel(collection)}
        </>
      ),
    },
    {
      title: "Archive Type",
      key: "archive",
      width: 200,
      render: (collection: Collection) => {
        const items = [];
        if (collection.snapshot_html) {
          items.push(
            <span key="html" style={{ marginRight: 8 }}>
              <Html5Outlined style={{ marginRight: 4 }} />
              HTML
            </span>,
          );
        }
        if (collection.take_screenshots) {
          items.push(
            <span key="screenshot" style={{ marginRight: 8 }}>
              <CameraOutlined style={{ marginRight: 4 }} />
              Screenshot
            </span>,
          );
        }
        if (collection.webhooks.length > 0) {
          items.push(
            <span key="webhook">
              <RetweetOutlined style={{ marginRight: 4 }} />
              Webhook{collection.webhooks.length > 1 ? "s" : ""}
            </span>,
          );
        }
        return items.length > 0 ? <>{items}</> : "-";
      },
    },
  ];

  const handleTableChange: TableProps<Collection>["onChange"] = (
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
      setCollections([]);
    }
  };

  const handleSelectionChange = (
    keys: React.Key[],
    selectAllPages: boolean,
  ) => {
    setSelectedRowKeys(keys);
    setSelectAll(selectAllPages);
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
          Collections
        </Title>
        <Button type="primary" icon={<PlusOutlined />}>
          New Collection
        </Button>
      </div>
      <SelectTable
        columns={columns}
        dataSource={collections}
        loading={loading}
        totalCount={totalCount}
        tableParams={tableParams}
        onTableChange={handleTableChange}
        itemName="collection"
        selectedRowKeys={selectedRowKeys}
        selectAll={selectAll}
        onSelectionChange={handleSelectionChange}
        searchValue={searchValue}
        onSearch={handleSearch}
        searchPlaceholder="Search collections by name"
      />
    </div>
  );
}
