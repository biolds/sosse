"use client";

import { memo, useMemo, useCallback, useState, useEffect, useRef } from "react";
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
import { useAppStore, type SearchTab } from "@/app/hooks/useAppStore";
import type { AdvancedFilter, SearchFilters } from "@/app/types/search";
import type { PaginatedResponse } from "@/app/types/restResponse";
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

const HomePage = () => {
  const {
    linkMode,
    toggleLinkMode,
    viewMode,
    setViewMode,
    homeViewMode,
    activeTab,
    setActiveTab,
    loadCollections,
  } = useAppStore();
  const { message } = App.useApp();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(
    typeof window !== "undefined" ? window.sosseConfig?.pageSize || 10 : 10,
  );
  const [tabViewMode, setTabViewMode] = useState<"list" | "card">("card");
  const advancedSearchRef = useRef<AdvancedSearchRef>(null);

  useEffect(() => {
    loadCollections();
  }, [loadCollections]);

  const parseUrlToFilters = useCallback((): {
    query: string;
    filters: SearchFilters;
  } => {
    const q = searchParams.get("q") || "";
    const doc_lang = searchParams.get("doc_lang") || "";
    const collection = searchParams.get("collection");
    const sort = searchParams.get("s") || "-rank";
    const include_hidden = searchParams.get("i") === "on";

    const advFilters: AdvancedFilter[] = [];
    const filterNumbers = new Set<string>();

    searchParams.forEach((value, key) => {
      const match = key.match(/^(ft|ff|fo|fv|fc)(\d+)$/);
      if (match) {
        filterNumbers.add(match[2]);
      }
    });

    Array.from(filterNumbers)
      .sort()
      .forEach((num) => {
        const type = searchParams.get(`ft${num}`);
        const field = searchParams.get(`ff${num}`);
        const operator = searchParams.get(`fo${num}`);
        const term = searchParams.get(`fv${num}`);
        const case_sensitive = searchParams.get(`fc${num}`) === "on";

        if (type && field && operator && term) {
          advFilters.push({
            id: `filter-${Date.now()}-${num}`,
            type: type as "inc" | "exc",
            field,
            operator: operator as "contain" | "equal" | "regexp",
            term,
            case_sensitive,
          });
        }
      });

    const robotstxtParam = searchParams.get("robotstxt_rejected");
    const hasErrorParam = searchParams.get("has_error");

    // Validate and convert robotstxt_rejected
    let robotstxtRejected: "include" | "exclude" | "only" = "exclude";
    if (
      robotstxtParam === "include" ||
      robotstxtParam === "only" ||
      robotstxtParam === "exclude"
    ) {
      robotstxtRejected = robotstxtParam;
    }

    // Validate and convert has_error
    let hasError: "include" | "exclude" | "only" = "include";
    if (
      hasErrorParam === "include" ||
      hasErrorParam === "only" ||
      hasErrorParam === "exclude"
    ) {
      hasError = hasErrorParam;
    }

    return {
      query: q,
      filters: {
        lang: doc_lang,
        collection: collection ? parseInt(collection, 10) : undefined,
        include_hidden,
        sort,
        adv_params: advFilters,
        robotstxt_rejected: robotstxtRejected,
        has_error: hasError,
      },
    };
  }, [searchParams]);

  const buildUrl = (query: string, filters: SearchFilters): string => {
    const params = new URLSearchParams();
    if (query) {
      params.set("q", query);
    }
    if (filters.lang) {
      params.set("doc_lang", filters.lang);
    }
    if (filters.collection) {
      params.set("collection", filters.collection.toString());
    }
    if (filters.sort && filters.sort !== "-rank") {
      params.set("s", filters.sort);
    }
    if (filters.include_hidden) {
      params.set("i", "on");
    }
    if (
      filters.robotstxt_rejected &&
      filters.robotstxt_rejected !== "exclude"
    ) {
      params.set("robotstxt_rejected", filters.robotstxt_rejected);
    }
    if (filters.has_error && filters.has_error !== "include") {
      params.set("has_error", filters.has_error);
    }
    filters.adv_params.forEach((filter, index) => {
      const num = index.toString();
      params.set(`ft${num}`, filter.type);
      params.set(`ff${num}`, filter.field);
      params.set(`fo${num}`, filter.operator);
      params.set(`fv${num}`, filter.term);
      if (filter.case_sensitive) {
        params.set(`fc${num}`, "on");
      }
    });

    return params.toString() ? `/?${params.toString()}` : "/";
  };

  const performSearch = async (
    query: string,
    filters: SearchFilters,
    tab: SearchTab,
    page: number = 1,
    customPageSize?: number,
  ) => {
    const hasAdvancedFilters =
      filters.adv_params.length > 0 ||
      filters.collection ||
      (filters.robotstxt_rejected &&
        filters.robotstxt_rejected !== "exclude") ||
      (filters.has_error && filters.has_error !== "include");

    if (tab !== "home" && !query && !hasAdvancedFilters) {
      return;
    }

    setLoading(true);
    setCurrentPage(page);

    const effectivePageSize = customPageSize || pageSize;
    const offset = (page - 1) * effectivePageSize;

    try {
      const tabFilters = getTabFilters(tab, filters.adv_params);

      const requestBody: {
        query: string;
        lang?: string;
        sort: string;
        include_hidden: boolean;
        collection?: number;
        adv_params?: AdvancedFilter[];
        show_on_homepage?: boolean;
        robotstxt_rejected?: boolean;
        has_error?: boolean;
      } = {
        query,
        sort: filters.sort,
        include_hidden: filters.include_hidden,
      };

      if (filters.lang) {
        requestBody.lang = filters.lang;
      }

      if (filters.collection) {
        requestBody.collection = filters.collection;
      }

      if (
        filters.robotstxt_rejected &&
        filters.robotstxt_rejected !== "include"
      ) {
        if (filters.robotstxt_rejected === "only") {
          requestBody.robotstxt_rejected = true;
        } else if (filters.robotstxt_rejected === "exclude") {
          requestBody.robotstxt_rejected = false;
        }
      }

      if (filters.has_error && filters.has_error !== "include") {
        if (filters.has_error === "only") {
          requestBody.has_error = true;
        } else if (filters.has_error === "exclude") {
          requestBody.has_error = false;
        }
      }

      if (tabFilters.length > 0) {
        requestBody.adv_params = tabFilters;
      }

      if (tab === "home") {
        requestBody.show_on_homepage = true;
      }

      const response = await axios.post<PaginatedResponse<SearchResult>>(
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

  const { query: currentQuery, filters: currentFilters } = useMemo(
    () => parseUrlToFilters(),
    [parseUrlToFilters],
  );

  useEffect(() => {
    const hasSearchQuery =
      currentQuery.trim() !== "" ||
      currentFilters.adv_params.length > 0 ||
      currentFilters.collection ||
      (currentFilters.robotstxt_rejected &&
        currentFilters.robotstxt_rejected !== "exclude") ||
      (currentFilters.has_error && currentFilters.has_error !== "include");
    const tab = getActiveTab(hasSearchQuery, "search");

    setActiveTab(tab);
    setInputValue(currentQuery);
    performSearch(currentQuery, currentFilters, tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleSearch = (value: string) => {
    const queryTerm = value.trim();

    if (currentFilters.adv_params.length > 0 && advancedSearchRef.current) {
      const isValid = advancedSearchRef.current.validateFilters();
      if (!isValid) {
        message.error("Please fill in all required filter fields");
        return;
      }
    }

    setInputValue(queryTerm);
    router.push(buildUrl(queryTerm, currentFilters));
  };

  const handleFiltersChange = (filters: SearchFilters) => {
    router.push(buildUrl(currentQuery, filters));
  };

  const handlePageChange = (page: number, newPageSize: number) => {
    if (newPageSize !== pageSize) {
      setPageSize(newPageSize);
      performSearch(currentQuery, currentFilters, activeTab, 1, newPageSize);
    } else {
      performSearch(currentQuery, currentFilters, activeTab, page);
    }
  };

  const handleTabChange = (tab: SearchTab) => {
    setActiveTab(tab);

    if (tab === "home") {
      setTabViewMode(homeViewMode);
    } else {
      setTabViewMode(viewMode);
    }

    performSearch(currentQuery, currentFilters, tab);
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
    router.push("/");
  };

  const hasSearchQuery =
    currentQuery.trim() !== "" ||
    currentFilters.adv_params.length > 0 ||
    currentFilters.collection ||
    (currentFilters.robotstxt_rejected &&
      currentFilters.robotstxt_rejected !== "exclude") ||
    (currentFilters.has_error && currentFilters.has_error !== "include");

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
          filters={currentFilters}
          setFilters={handleFiltersChange}
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
                {activeTab !== "home" &&
                  `
                  Found ${totalResults} result${totalResults !== 1 ? "s" : ""}
                  ${currentQuery && ' for "' + currentQuery + '"'}
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

        {!loading && searchResults.length === 0 && (
          <div style={{ textAlign: "center", marginTop: "60px" }}>
            <Text type="secondary">
              {activeTab === "home"
                ? "No featured documents available"
                : `No results found for "${currentQuery}"`}
            </Text>
          </div>
        )}
      </div>
    </Content>
  );
};

export default memo(HomePage);
