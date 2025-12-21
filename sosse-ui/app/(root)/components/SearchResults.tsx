"use client";

import Image from "next/image";
import React from "react";
import { List, Typography, Space, Card, Row, Col } from "antd";
import { CalendarOutlined, FileTextOutlined } from "@ant-design/icons";
import type { Tag } from "@/app/types/tag";
import TagComponent from "@/app/components/tag";
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
  tag_list?: Tag[];
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
                style={{ height: "100%" }}
                cover={
                  item.preview ? (
                    <div
                      style={{
                        height: "200px",
                        overflow: "hidden",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        backgroundColor: "var(--card-bg)",
                      }}
                    >
                      <Image
                        alt="preview"
                        src={item.preview}
                        width={0}
                        height={0}
                        sizes="100vw"
                        unoptimized
                        style={{
                          width: "auto",
                          height: "auto",
                          maxHeight: "200px",
                          maxWidth: "100%",
                          objectFit: "contain",
                        }}
                        loading="lazy"
                      />
                    </div>
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
                      orientation="vertical"
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

                      {item.tag_list && item.tag_list.length > 0 && (
                        <Space size="small" wrap>
                          {item.tag_list.map((tag) => (
                            <TagComponent key={tag.id} tag={tag} />
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
                <div
                  style={{
                    maxHeight: "100px",
                    maxWidth: "200px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Image
                    width={0}
                    height={0}
                    sizes="200px"
                    alt="preview"
                    src={item.preview}
                    style={{
                      borderRadius: "4px",
                      width: "auto",
                      height: "auto",
                      maxHeight: "100px",
                      maxWidth: "200px",
                      objectFit: "contain",
                    }}
                    loading="lazy"
                    unoptimized
                  />
                </div>
              )
            }
          >
            <Space
              orientation="vertical"
              size="small"
              style={{ width: "100%" }}
            >
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

              {item.tag_list && item.tag_list.length > 0 && (
                <Space size="small" wrap>
                  {item.tag_list.map((tag) => (
                    <TagComponent key={tag.id} tag={tag} />
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
