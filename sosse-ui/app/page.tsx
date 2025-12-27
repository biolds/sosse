"use client";

import React, { useState, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  App,
  Button,
  Input,
  Layout,
  Typography,
  Spin,
  Segmented,
  Pagination,
} from "antd";
import {
  SearchOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
} from "@ant-design/icons";
import axios from "axios";
import {
  useAppStore,
  type AdvancedFilter,
  type SearchTab,
} from "@/app/hooks/useAppStore";
import SearchResults, { SearchResult } from "./components/SearchResults";
import AdvancedSearch, {
  type AdvancedSearchRef,
} from "./components/AdvancedSearch";
import { ArchiveIcon, SourceIcon } from "./components/ArchiveIcons";
import SearchTabs from "./components/SearchTabs";
import { getTabFilters, getActiveTab } from "./utils/searchTabUtils";

const { Text } = Typography;
const { Search } = Input;
const { Content } = Layout;

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
    homeViewMode,
    activeTab,
    setActiveTab,
    searchFilters,
    updateSearchFilters,
    loadCollections,
  } = useAppStore();
  const { message } = App.useApp();
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
  const [tabViewMode, setTabViewMode] = useState<"list" | "card">("card");
  const advancedSearchRef = useRef<AdvancedSearchRef>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    loadCollections();
  }, [loadCollections]);

  const performSearch = async (
    value: string | null,
    page: number = 1,
    customPageSize?: number,
    filters = searchFilters,
    tab: SearchTab = activeTab,
  ) => {
    const queryTerm = (value && value.trim()) || "";
    const hasAdvancedFilters =
      filters.adv_params && filters.adv_params.length > 0;

    // For home tab, allow search without query
    if (tab !== "home" && !queryTerm && !hasAdvancedFilters) {
      return;
    }

    setLoading(true);
    setSubmittedQuery(queryTerm);
    setCurrentPage(page);

    const effectivePageSize = customPageSize || pageSize;
    const offset = (page - 1) * effectivePageSize;

    try {
      // Apply tab-specific filters
      const tabFilters = getTabFilters(tab, filters.adv_params);

      const requestBody: {
        query: string;
        lang?: string;
        sort: string;
        include_hidden: boolean;
        collection?: number;
        adv_params?: AdvancedFilter[];
        show_on_homepage?: boolean;
      } = {
        query: queryTerm,
        sort: filters.sort,
        include_hidden: filters.include_hidden,
      };

      if (filters.lang) {
        requestBody.lang = filters.lang;
      }

      if (filters.collection) {
        requestBody.collection = filters.collection;
      }

      if (tabFilters.length > 0) {
        requestBody.adv_params = tabFilters;
      }

      // For home tab, add show_on_homepage filter
      if (tab === "home") {
        requestBody.show_on_homepage = true;
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
    if (isInitialized) return;

    const q = searchParams.get("q");
    const doc_lang = searchParams.get("doc_lang");
    const collection = searchParams.get("collection");
    const sort = searchParams.get("s");
    const include_hidden = searchParams.get("i") === "on";

    // Load filters from URL
    const filters: AdvancedFilter[] = [];
    const filterNumbers = new Set<string>();

    // Find all filter numbers in URL params
    searchParams.forEach((value, key) => {
      const match = key.match(/^(ft|ff|fo|fv|fc)(\d+)$/);
      if (match) {
        filterNumbers.add(match[2]);
      }
    });

    // Build filter objects
    Array.from(filterNumbers)
      .sort()
      .forEach((num) => {
        const type = searchParams.get(`ft${num}`);
        const field = searchParams.get(`ff${num}`);
        const operator = searchParams.get(`fo${num}`);
        const term = searchParams.get(`fv${num}`);
        const case_sensitive = searchParams.get(`fc${num}`) === "on";

        if (type && field && operator && term) {
          filters.push({
            id: `filter-${Date.now()}-${num}`,
            type: type as "inc" | "exc",
            field,
            operator: operator as "contain" | "equal" | "regexp",
            term,
            case_sensitive,
          });
        }
      });

    const hasSearchQuery = (q && q.trim() !== "") || filters.length > 0;
    const newTab = getActiveTab(hasSearchQuery, "search");

    // Set tab immediately before any render
    setActiveTab(newTab);

    // Update filters first
    const newFilters = { ...searchFilters };
    if (filters.length > 0) {
      newFilters.adv_params = filters;
    }
    if (doc_lang !== null) {
      newFilters.lang = doc_lang;
    }
    if (collection) {
      newFilters.collection = parseInt(collection, 10);
    }
    if (sort) {
      newFilters.sort = sort;
    }
    if (include_hidden) {
      newFilters.include_hidden = true;
    }

    if (
      filters.length > 0 ||
      doc_lang ||
      collection ||
      sort ||
      include_hidden
    ) {
      updateSearchFilters(newFilters);
    }

    if (hasSearchQuery) {
      setInputValue(q || "");
      performSearch(q, 1, undefined, newFilters, newTab);
    } else {
      // Load homepage content
      performSearch("", 1, undefined, newFilters, newTab);
    }

    setIsInitialized(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (value: string) => {
    const queryTerm = value.trim();
    const hasAdvancedFilters = searchFilters.adv_params.length > 0;

    if (hasAdvancedFilters && advancedSearchRef.current) {
      const isValid = advancedSearchRef.current.validateFilters();
      if (!isValid) {
        message.error("Please fill in all required filter fields");
        return;
      }
    }

    const newTab = "search";
    setActiveTab(newTab);
    performSearch(queryTerm, 1, undefined, searchFilters, newTab);

    // Build URL with filters
    const params = new URLSearchParams();
    if (queryTerm) {
      params.set("q", queryTerm);
    }
    if (searchFilters.lang) {
      params.set("doc_lang", searchFilters.lang);
    }
    if (searchFilters.collection) {
      params.set("collection", searchFilters.collection.toString());
    }
    if (searchFilters.sort && searchFilters.sort !== "-rank") {
      params.set("s", searchFilters.sort);
    }
    if (searchFilters.include_hidden) {
      params.set("i", "on");
    }
    searchFilters.adv_params.forEach((filter, index) => {
      const num = index.toString();
      params.set(`ft${num}`, filter.type);
      params.set(`ff${num}`, filter.field);
      params.set(`fo${num}`, filter.operator);
      params.set(`fv${num}`, filter.term);
      if (filter.case_sensitive) {
        params.set(`fc${num}`, "on");
      }
    });

    const url = params.toString() ? `/?${params.toString()}` : "/";
    router.push(url);
  };

  useEffect(() => {
    if (!isInitialized) return; // Skip during initialization

    const hasSearchQuery =
      submittedQuery.trim() !== "" || searchFilters.adv_params.length > 0;

    if (!hasSearchQuery && activeTab !== "home") {
      // Auto-switch to Home tab when search query/filters are cleared
      setActiveTab("home");
      performSearch("", 1, undefined, searchFilters, "home");
      router.push("/"); // Clear URL params
      return;
    }

    const hasAdvancedFilters = searchFilters.adv_params.length > 0;

    if (hasAdvancedFilters && advancedSearchRef.current) {
      const isValid = advancedSearchRef.current.validateFilters();
      if (!isValid) {
        return;
      }
    }

    const newTab = getActiveTab(
      submittedQuery.trim() !== "" || hasAdvancedFilters,
      activeTab,
    );
    setActiveTab(newTab);
    performSearch(
      submittedQuery || inputValue,
      1,
      undefined,
      searchFilters,
      newTab,
    );

    // Update URL with current filters
    const params = new URLSearchParams();
    const query = submittedQuery || inputValue;
    if (query) {
      params.set("q", query);
    }
    if (searchFilters.lang) {
      params.set("doc_lang", searchFilters.lang);
    }
    if (searchFilters.collection) {
      params.set("collection", searchFilters.collection.toString());
    }
    if (searchFilters.sort && searchFilters.sort !== "-rank") {
      params.set("s", searchFilters.sort);
    }
    if (searchFilters.include_hidden) {
      params.set("i", "on");
    }
    searchFilters.adv_params.forEach((filter, index) => {
      const num = index.toString();
      params.set(`ft${num}`, filter.type);
      params.set(`ff${num}`, filter.field);
      params.set(`fo${num}`, filter.operator);
      params.set(`fv${num}`, filter.term);
      if (filter.case_sensitive) {
        params.set(`fc${num}`, "on");
      }
    });

    const url = params.toString() ? `/?${params.toString()}` : "/";
    router.push(url);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchFilters]);

  const handlePageChange = (page: number, newPageSize: number) => {
    const q = searchParams.get("q") || "";
    if (newPageSize !== pageSize) {
      setPageSize(newPageSize);
      performSearch(q, 1, newPageSize, searchFilters, activeTab);
    } else {
      performSearch(q, page, undefined, searchFilters, activeTab);
    }
  };

  const handleTabChange = (tab: SearchTab) => {
    setActiveTab(tab);

    // Switch view mode based on tab
    if (tab === "home") {
      setTabViewMode(homeViewMode);
    } else {
      setTabViewMode(viewMode);
    }

    // Perform search with new tab filters
    const query = submittedQuery || inputValue;
    performSearch(query, 1, undefined, searchFilters, tab);
  };

  const handleViewModeChange = (mode: "list" | "card") => {
    if (activeTab === "home") {
      setTabViewMode(mode);
    } else {
      setViewMode(mode);
      setTabViewMode(mode);
    }
  };

  const handleClearSearch = () => {
    setInputValue("");
    setSubmittedQuery("");
    if (searchFilters.adv_params.length === 0) {
      // No filters, switch to home
      setActiveTab("home");
      performSearch("", 1, undefined, searchFilters, "home");
      router.push("/");
    }
  };

  const hasSearchQuery =
    (submittedQuery && submittedQuery.trim() !== "") ||
    searchFilters.adv_params.length > 0;

  const currentViewMode = activeTab === "home" ? tabViewMode : viewMode;

  return (
    <Content style={{ padding: "4px" }}>
      <div
        style={{ maxWidth: "1200px", margin: "0px auto", paddingTop: "40px" }}
      >
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
          onClear={handleClearSearch}
          loading={loading}
          autoFocus
          allowClear
        />

        <AdvancedSearch
          ref={advancedSearchRef}
          filters={searchFilters}
          setFilters={updateSearchFilters}
        />

        <SearchTabs
          activeTab={activeTab}
          onTabChange={handleTabChange}
          hasSearchQuery={hasSearchQuery}
        />

        {loading && (
          <div style={{ textAlign: "center", marginTop: "60px" }}>
            <Spin size="large" />
          </div>
        )}

        {!loading && isInitialized && searchResults.length > 0 && (
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
                {activeTab !== "home" &&
                  `
                  Found ${totalResults} result${totalResults !== 1 ? "s" : ""}
                  ${submittedQuery && ' for "' + submittedQuery + '"'}
              `}
              </Text>

              <div style={{ display: "flex", gap: "12px" }}>
                <Button
                  icon={
                    linkMode === "source" ? <SourceIcon /> : <ArchiveIcon />
                  }
                  onClick={toggleLinkMode}
                >
                  {linkMode === "source" ? "Source" : "Archive"}
                </Button>

                <Segmented
                  value={currentViewMode}
                  onChange={(value) =>
                    handleViewModeChange(value as "list" | "card")
                  }
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
              viewMode={currentViewMode}
              isHomeTab={activeTab === "home"}
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

        {!loading && isInitialized && searchResults.length === 0 && (
          <div style={{ textAlign: "center", marginTop: "60px" }}>
            <Text type="secondary">
              {activeTab === "home"
                ? "No featured documents available"
                : `No results found for "${submittedQuery}"`}
            </Text>
          </div>
        )}
      </div>
    </Content>
  );
};

export default React.memo(HomePage);
