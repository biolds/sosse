"use client";

import Link from "next/link";
import { useCallback, useState, useEffect } from "react";
import { Table, Button, Typography, Input, message } from "antd";
import type { GetProp, TableProps } from "antd";
import type { SorterResult } from "antd/es/table/interface";
import {
  FileTextOutlined,
  PlusOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import axios from "axios";
import type { PaginatedResponse } from "@/app/types/restResponse";
import type { Collection } from "@/app/types/collection";
import CollectionDescription from "./components/CollectionDescription";

const { Title } = Typography;

type TablePaginationConfig = Exclude<
  GetProp<TableProps, "pagination">,
  boolean
>;

interface TableParams {
  pagination?: TablePaginationConfig;
  sortField?: SorterResult<Collection>["field"];
  sortOrder?: SorterResult<Collection>["order"];
  filters?: Parameters<GetProp<TableProps, "onChange">>[1];
}

export default function CollectionsPage() {
  const [cookies, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [tableParams, setTableParams] = useState<TableParams>({
    pagination: {
      current: 1,
      pageSize: 10,
    },
  });
  const [totalCount, setTotalCount] = useState(0);

  const fetchCollections = useCallback(
    async (search?: string) => {
      try {
        setLoading(true);

        const response = await axios.get<PaginatedResponse<Collection>>(
          "/api/collection/",
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
        setCollections(response.data.results);
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
    fetchCollections();
  }, [fetchCollections]);

  const handleSearch = (value: string) => {
    fetchCollections(value);
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
      render: (count: number, collection: Collection) => (
        <Link href={`/?collection=${collection.id}`}>
          <FileTextOutlined style={{ marginRight: 4 }} />
          {count}
        </Link>
      ),
      sorter: true,
    },
    {
      title: "Descritption",
      key: "description",
      render: (collection: Collection) => (
        <CollectionDescription collection={collection} />
      ),
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

    if (pagination.pageSize !== tableParams.pagination?.pageSize) {
      setCollections([]);
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
          Collections
        </Title>
        <Button type="primary" icon={<PlusOutlined />}>
          New Collection
        </Button>
      </div>
      <Input.Search
        placeholder="Search collections by name or enter URL (http://...)"
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
