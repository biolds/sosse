"use client";

import Link from "next/link";
import { useCallback, useState, useEffect } from "react";
import { Button, Typography, message } from "antd";
import type { TableProps } from "antd";
import { FileTextOutlined, PlusOutlined } from "@ant-design/icons";
import axios from "axios";
import type { PaginatedResponse } from "@/app/types/restResponse";
import type { Collection } from "@/app/types/collection";
import CollectionDescription from "./components/CollectionDescription";
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
