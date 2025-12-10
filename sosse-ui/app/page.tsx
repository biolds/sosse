"use client";

import { useState } from "react";
import { Input, Button, List, Typography, Space, Tag, Spin, message } from "antd";
import { SearchOutlined, LinkOutlined, CalendarOutlined } from "@ant-design/icons";
import axios from "axios";

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

interface SearchResult {
  id: number;
  url: string;
  title: string;
  content?: string;
  score?: number;
  crawl_last?: string;
  lang_iso_639_1?: string;
  tags?: Array<{ id: number; name: string }>;
  preview?: string;
}

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

  const handleSearch = async (value: string) => {
    if (!value.trim()) {
      message.warning("Please enter a search query");
      return;
    }

    setLoading(true);
    setSearchQuery(value);

    try {
      const response = await axios.post<SearchResponse>("/api/search/", {
        query: value,
        lang: "en",
        sort: "-rank",
        include_hidden: false,
      });

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

  const formatDate = (dateString?: string) => {
    if (!dateString) return null;
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", paddingTop: "40px" }}>
      <Title level={1} style={{ textAlign: "center", marginBottom: "40px" }}>
        Search Archived Pages
      </Title>

      <Search
        placeholder="Enter search query..."
        enterButton={<Button type="primary" icon={<SearchOutlined />}>Search</Button>}
        size="large"
        onSearch={handleSearch}
        loading={loading}
      />

      {loading && (
        <div style={{ textAlign: "center", marginTop: "60px" }}>
          <Spin size="large" />
        </div>
      )}

      {!loading && searchResults.length > 0 && (
        <>
          <div style={{ marginTop: "20px", marginBottom: "10px" }}>
            <Text type="secondary">
              Found {totalResults} result{totalResults !== 1 ? "s" : ""} for &quot;{searchQuery}&quot;
            </Text>
          </div>

          <List
            itemLayout="vertical"
            size="large"
            dataSource={searchResults}
            renderItem={(item) => (
              <List.Item
                key={item.id}
                extra={
                  item.preview && (
                    <img
                      width={200}
                      alt="preview"
                      src={item.preview}
                      style={{ objectFit: "cover", borderRadius: "4px" }}
                    />
                  )
                }
              >
                <Space direction="vertical" size="small" style={{ width: "100%" }}>
                  <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: "18px", fontWeight: "500" }}>
                    {item.title || "Untitled"}
                  </a>

                  <Space size="small" wrap>
                    <Text type="secondary" style={{ fontSize: "12px" }}>
                      <LinkOutlined /> {item.url}
                    </Text>
                    {item.crawl_last && (
                      <Text type="secondary" style={{ fontSize: "12px" }}>
                        <CalendarOutlined /> {formatDate(item.crawl_last)}
                      </Text>
                    )}
                    {item.score && (
                      <Text type="secondary" style={{ fontSize: "12px" }}>
                        Score: {item.score.toFixed(2)}
                      </Text>
                    )}
                  </Space>

                  {item.content && (
                    <Paragraph ellipsis={{ rows: 2, expandable: false }} style={{ marginBottom: "8px" }}>
                      {item.content.substring(0, 300)}...
                    </Paragraph>
                  )}

                  {item.tags && item.tags.length > 0 && (
                    <Space size="small" wrap>
                      {item.tags.map((tag) => (
                        <Tag key={tag.id}>{tag.name}</Tag>
                      ))}
                    </Space>
                  )}
                </Space>
              </List.Item>
            )}
          />
        </>
      )}

      {!loading && searchQuery && searchResults.length === 0 && (
        <div style={{ textAlign: "center", marginTop: "60px" }}>
          <Text type="secondary">No results found for &quot;{searchQuery}&quot;</Text>
        </div>
      )}
    </div>
  );
}
