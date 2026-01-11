"use client";

import { Button, Space, Alert, Table, Input } from "antd";
import type { TableProps, TableRowSelection } from "antd";
import type { GetProp } from "antd";
import type { SorterResult } from "antd/es/table/interface";
import { SearchOutlined } from "@ant-design/icons";

type TablePaginationConfig = Exclude<
  GetProp<TableProps, "pagination">,
  boolean
>;

export interface TableParams<T> {
  pagination?: TablePaginationConfig;
  sortField?: SorterResult<T>["field"];
  sortOrder?: SorterResult<T>["order"];
  filters?: Parameters<GetProp<TableProps, "onChange">>[1];
}

interface SelectTableProps<T> {
  columns: TableProps<T>["columns"];
  dataSource: T[];
  loading: boolean;
  totalCount: number;
  tableParams: TableParams<T>;
  onTableChange: TableProps<T>["onChange"];
  rowKey?: string;
  itemName?: string;
  selectedRowKeys: React.Key[];
  selectAll: boolean;
  onSelectionChange: (keys: React.Key[], selectAll: boolean) => void;
  searchValue?: string;
  onSearch?: (value: string) => void;
  searchPlaceholder?: string;
}

export default function SelectTable<T extends { id: number }>({
  columns,
  dataSource,
  loading,
  totalCount,
  tableParams,
  onTableChange,
  rowKey = "id",
  itemName = "item",
  selectedRowKeys,
  selectAll,
  onSelectionChange,
  searchValue = "",
  onSearch,
  searchPlaceholder = "Search...",
}: SelectTableProps<T>) {
  const handleSelectAllPages = () => {
    onSelectionChange(selectedRowKeys, true);
  };

  const rowSelection: TableRowSelection<T> = {
    selectedRowKeys,
    onChange: (selectedKeys) => {
      onSelectionChange(selectedKeys, false);
    },
  };

  return (
    <>
      {onSearch && (
        <Input.Search
          placeholder={searchPlaceholder}
          prefix={<SearchOutlined />}
          style={{ marginBottom: "16px", maxWidth: "600px" }}
          onSearch={onSearch}
          value={searchValue}
          onChange={(e) => onSearch(e.target.value)}
          allowClear
          enterButton
        />
      )}

      {selectedRowKeys.length > 0 && !selectAll ? (
        <Alert
          title={
            <Space>
              <span>{selectedRowKeys.length} selected</span>
              <Button type="link" size="small" onClick={handleSelectAllPages}>
                Select all {totalCount} {itemName}s
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
              <span>
                All {totalCount} {itemName}s selected
              </span>
              <Button
                type="link"
                size="small"
                onClick={() => onSelectionChange([], false)}
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
        dataSource={dataSource}
        rowKey={rowKey}
        rowSelection={rowSelection}
        pagination={{
          ...tableParams.pagination,
          total: totalCount,
          showSizeChanger: true,
          showTotal: (total) =>
            `Total ${total} ${itemName}s${selectAll ? ` (all ${totalCount} selected)` : selectedRowKeys.length > 0 ? ` (${selectedRowKeys.length} selected)` : ""}`,
        }}
        loading={loading}
        onChange={onTableChange}
      />
    </>
  );
}
