"use client";

import Image from "next/image";
import React from "react";
import { List, Typography, Space, Tag, Card, Row, Col } from "antd";
import { CalendarOutlined, FileTextOutlined } from "@ant-design/icons";
import { AnimatedLinkModeIcon } from "./ArchiveIcons";
import SearchResultLink from "./SearchResultLink";
import "./SearchResults.css";

const { Text } = Typography;

export interface SearchResult {
  id: number;
  url: string;
  title: string;
  content?: string;
  score?: number;
  crawl_last?: string;
  lang_iso_639_1?: string;
  tags?: Array<{ id: number; name: string }>;
  preview?: string;
  favicon?: {
    id: number;
    missing: boolean;
  };
  headline?: string;
  collection?: number;
}

interface SearchResultsProps {
  results: SearchResult[];
  viewMode: "list" | "card";
}

const formatDate = (dateString?: string) => {
  if (!dateString) return null;
  return new Date(dateString).toLocaleDateString();
};

const SearchResults = ({ results, viewMode }: SearchResultsProps) => {
  if (viewMode === "card") {
    return (
      <Row gutter={[12, 12]}>
        {results.map((item) => (
          <Col key={item.id} xs={24} sm={12} lg={6} xxl={4}>
            <SearchResultLink href={item.url}>
              <Card
                hoverable
                cover={
                  item.preview ? (
                    <Image
                      alt="preview"
                      src={item.preview}
                      width={200}
                      height={120}
                      unoptimized
                      style={{ objectFit: "cover" }}
                      loading="lazy"
                    />
                  ) : (
                    <div
                      className="card-no-preview"
                      style={{
                        height: "200px",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "12px",
                      }}
                    >
                      <FileTextOutlined
                        style={{ fontSize: "48px", opacity: 0.3 }}
                      />
                    </div>
                  )
                }
              >
                <Card.Meta
                  title={
                    <Space size="small">
                      <span
                        style={{
                          fontSize: "16px",
                          display: "flex",
                          alignItems: "center",
                        }}
                      >
                        {item.favicon && !item.favicon.missing && (
                          <Image
                            src={`/favicon/${item.favicon.id}`}
                            alt="icon"
                            width={16}
                            height={16}
                            style={{
                              display: "inline-block",
                              marginRight: "4px",
                            }}
                            unoptimized
                          />
                        )}
                        {item.title || "Untitled"}
                      </span>
                    </Space>
                  }
                  description={
                    <Space
                      direction="vertical"
                      size="small"
                      style={{ width: "100%" }}
                    >
                      <Text
                        type="secondary"
                        style={{ fontSize: "12px" }}
                        ellipsis
                      >
                        <AnimatedLinkModeIcon /> {item.url}
                      </Text>

                      <Space size="small" wrap>
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

                      {item.headline && (
                        <div
                          style={{
                            marginBottom: "8px",
                            marginTop: "8px",
                            fontSize: "13px",
                          }}
                          dangerouslySetInnerHTML={{ __html: item.headline }}
                        />
                      )}

                      {item.tags && item.tags.length > 0 && (
                        <Space size="small" wrap>
                          {item.tags.map((tag) => (
                            <Tag key={tag.id} style={{ fontSize: "11px" }}>
                              {tag.name}
                            </Tag>
                          ))}
                        </Space>
                      )}
                    </Space>
                  }
                />
              </Card>
            </SearchResultLink>
          </Col>
        ))}
      </Row>
    );
  }

  return (
    <List
      itemLayout="vertical"
      size="large"
      dataSource={results}
      renderItem={(item) => (
        <SearchResultLink href={item.url}>
          <List.Item
            key={item.id}
            className="search-result-item"
            extra={
              item.preview && (
                <Image
                  height={120}
                  width={200}
                  alt="preview"
                  src={item.preview}
                  style={{ borderRadius: "4px", objectFit: "cover" }}
                  loading="lazy"
                  unoptimized
                />
              )
            }
          >
            <Space direction="vertical" size="small" style={{ width: "100%" }}>
              <Space size="small">
                {item.favicon && !item.favicon.missing && (
                  <Image
                    src={`/favicon/${item.favicon.id}`}
                    alt="icon"
                    width={16}
                    height={16}
                    loading="lazy"
                    unoptimized
                  />
                )}
                <span style={{ fontSize: "18px", fontWeight: "500" }}>
                  {item.title || "Untitled"}
                </span>
              </Space>

              <Space size="small" wrap>
                <Text type="secondary" style={{ fontSize: "12px" }}>
                  <AnimatedLinkModeIcon /> {item.url}
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

              {item.headline && (
                <div
                  style={{ marginBottom: "8px" }}
                  dangerouslySetInnerHTML={{ __html: item.headline }}
                />
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
        </SearchResultLink>
      )}
    />
  );
};

export default React.memo(SearchResults);
