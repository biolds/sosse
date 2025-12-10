"use client";

import { useState } from "react";
import { Input, Button, Typography, Spin, message, Segmented, Pagination } from "antd";
import {
  SearchOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons";
import axios from "axios";
import SearchResults, { SearchResult } from "./components/SearchResults";

const { Title, Text } = Typography;
const { Search } = Input;

interface SearchResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: SearchResult[];
}

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [viewMode, setViewMode] = useState<"list" | "card">("list");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(
    typeof window !== "undefined" ? window.sosseConfig?.pageSize || 10 : 10
  );

  const handleSearch = async (value: string, page: number = 1, customPageSize?: number) => {
    if (!value.trim()) {
      message.warning("Please enter a search query");
      return;
    }

    setLoading(true);
    setSearchQuery(value);
    setCurrentPage(page);

    const effectivePageSize = customPageSize || pageSize;
    const offset = (page - 1) * effectivePageSize;

    try {
      const response = await axios.post<SearchResponse>(
        `/api/search/?limit=${effectivePageSize}&offset=${offset}`,
        {
          query: value,
          lang: "en",
          sort: "-rank",
          include_hidden: false,
        }
      );

      setSearchResults(response.data.results);
      setTotalResults(response.data.count);
    } catch (error) {
      console.error("Search error:", error);
      message.error("Failed to perform search. Please try again.");
      setSearchResults([]);
      setTotalResults(0);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (page: number, newPageSize: number) => {
    if (newPageSize !== pageSize) {
      setPageSize(newPageSize);
      handleSearch(searchQuery, 1, newPageSize);
    } else {
      handleSearch(searchQuery, page);
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", paddingTop: "40px" }}>
      <Title level={1} style={{ textAlign: "center", marginBottom: "40px" }}>
        Search Archived Pages
      </Title>

      <Search
        placeholder="Enter search query..."
        enterButton={
          <Button type="primary" icon={<SearchOutlined />}>
            Search
          </Button>
        }
        size="large"
        onSearch={handleSearch}
        loading={loading}
        autoFocus
      />

      {loading && (
        <div style={{ textAlign: "center", marginTop: "60px" }}>
          <Spin size="large" />
        </div>
      )}

      {!loading && searchResults.length > 0 && (
        <>
          <div
            style={{
              marginTop: "20px",
              marginBottom: "20px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Text type="secondary">
              Found {totalResults} result{totalResults !== 1 ? "s" : ""} for
              &quot;{searchQuery}&quot;
            </Text>

            <Segmented
              value={viewMode}
              onChange={(value) => setViewMode(value as "list" | "card")}
              options={[
                {
                  value: "list",
                  icon: <UnorderedListOutlined />,
                },
                {
                  value: "card",
                  icon: <AppstoreOutlined />,
                },
              ]}
            />
          </div>

          <SearchResults results={searchResults} viewMode={viewMode} />

          {totalResults > pageSize && (
            <div style={{ marginTop: "40px", textAlign: "center" }}>
              <Pagination
                current={currentPage}
                total={totalResults}
                pageSize={pageSize}
                onChange={handlePageChange}
                showSizeChanger
                showTotal={(total) => `Total ${total} results`}
                pageSizeOptions={[10, 20, 50, 100]}
              />
            </div>
          )}
        </>
      )}

      {!loading && searchQuery && searchResults.length === 0 && (
        <div style={{ textAlign: "center", marginTop: "60px" }}>
          <Text type="secondary">
            No results found for &quot;{searchQuery}&quot;
          </Text>
        </div>
      )}
    </div>
  );
}
