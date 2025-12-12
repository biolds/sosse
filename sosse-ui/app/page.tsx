"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Input,
  Button,
  Typography,
  Spin,
  message,
  Segmented,
  Pagination,
} from "antd";
import {
  SearchOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons";
import axios from "axios";
import SearchResults, { SearchResult } from "./components/SearchResults";
import AdvancedSearch from "./components/AdvancedSearch";
import { useAppStore } from "./useAppStore";
import { ArchiveIcon, SourceIcon } from "./components/ArchiveIcons";

const { Title, Text } = Typography;
const { Search } = Input;

interface SearchResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: SearchResult[];
}

const HomePage = () => {
  const {
    linkMode,
    toggleLinkMode,
    viewMode,
    setViewMode,
    searchFilters,
    updateSearchFilters,
    loadCollections,
  } = useAppStore();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(
    typeof window !== "undefined" ? window.sosseConfig?.pageSize || 10 : 10,
  );
  const [advancedExpanded, setAdvancedExpanded] = useState(false);
  const [draftFilters, setDraftFilters] = useState(searchFilters);

  useEffect(() => {
    loadCollections();
  }, [loadCollections]);

  const performSearch = async (
    value: string,
    page: number = 1,
    customPageSize?: number,
  ) => {
    const queryTerm = value.trim();
    const hasAdvancedFilters =
      searchFilters.adv_params && searchFilters.adv_params.length > 0;

    if (!queryTerm && !hasAdvancedFilters) {
      return;
    }

    setLoading(true);
    setSubmittedQuery(queryTerm);
    setCurrentPage(page);

    const effectivePageSize = customPageSize || pageSize;
    const offset = (page - 1) * effectivePageSize;

    try {
      const requestBody: {
        query: string;
        lang: string;
        sort: string;
        include_hidden: boolean;
        collection?: number;
        adv_params?: typeof searchFilters.adv_params;
      } = {
        query: queryTerm,
        lang: searchFilters.lang || "en",
        sort: searchFilters.sort,
        include_hidden: searchFilters.include_hidden,
      };

      if (searchFilters.collection) {
        requestBody.collection = searchFilters.collection;
      }

      if (searchFilters.adv_params.length > 0) {
        requestBody.adv_params = searchFilters.adv_params;
      }

      const response = await axios.post<SearchResponse>(
        `/api/search/?limit=${effectivePageSize}&offset=${offset}`,
        requestBody,
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

  useEffect(() => {
    const q = searchParams.get("q");
    if (q && q.trim()) {
      setInputValue(q);
      performSearch(q);
    }
  }, [searchParams]);

  const handleSearch = (value: string) => {
    const queryTerm = value.trim();
    const hasAdvancedFilters = draftFilters.adv_params.length > 0;

    if (!queryTerm && !hasAdvancedFilters) {
      message.warning("Please enter a search query or add filters");
      return;
    }

    updateSearchFilters(draftFilters);
    performSearch(queryTerm);

    const params = new URLSearchParams();
    if (queryTerm) {
      params.set("q", queryTerm);
    }
    router.push(`/?${params.toString()}`);
  };

  const handlePageChange = (page: number, newPageSize: number) => {
    const q = searchParams.get("q") || "";
    if (newPageSize !== pageSize) {
      setPageSize(newPageSize);
      performSearch(q, 1, newPageSize);
    } else {
      performSearch(q, page);
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
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onSearch={handleSearch}
        loading={loading}
        autoFocus
      />

      <AdvancedSearch
        expanded={advancedExpanded}
        setExpanded={setAdvancedExpanded}
        draftFilters={draftFilters}
        setDraftFilters={setDraftFilters}
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
              &quot;{submittedQuery}&quot;
            </Text>

            <div style={{ display: "flex", gap: "12px" }}>
              <Button
                icon={linkMode === "source" ? <SourceIcon /> : <ArchiveIcon />}
                onClick={toggleLinkMode}
              >
                {linkMode === "source" ? "Source" : "Archive"}
              </Button>

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
          </div>

          <SearchResults
            results={searchResults}
            viewMode={viewMode}
            linkMode={linkMode}
          />

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

      {!loading && submittedQuery && searchResults.length === 0 && (
        <div style={{ textAlign: "center", marginTop: "60px" }}>
          <Text type="secondary">
            No results found for &quot;{submittedQuery}&quot;
          </Text>
        </div>
      )}
    </div>
  );
};

export default React.memo(HomePage);
