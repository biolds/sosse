import Link from "next/link";
import React from "react";
import { List, Typography, Space, Tag, Card, Row, Col } from "antd";
import { CalendarOutlined, FileTextOutlined } from "@ant-design/icons";
import { ArchiveIcon, SourceIcon } from "./ArchiveIcons";

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
  linkMode: "source" | "archive";
}

const formatDate = (dateString?: string) => {
  if (!dateString) return null;
  return new Date(dateString).toLocaleDateString();
};

const SearchResults = ({ results, viewMode, linkMode }: SearchResultsProps) => {
  const getResultLink = (item: SearchResult) => {
    if (linkMode === "archive") {
      return `/archive/${item.url}`;
    }
    return item.url;
  };
  if (viewMode === "card") {
    return (
      <Row gutter={[16, 16]}>
        {results.map((item) => (
          <Col key={item.id} xs={24} sm={12} lg={8}>
            <Link
              href={getResultLink(item)}
              target={linkMode === "source" ? "_blank" : undefined}
              rel={linkMode === "source" ? "noopener noreferrer" : undefined}
              style={{ textDecoration: "none", color: "inherit" }}
            >
              <Card
                hoverable
                cover={
                  item.preview ? (
                    <img
                      alt="preview"
                      src={item.preview}
                      style={{ height: "200px", objectFit: "cover" }}
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
                      {item.favicon && !item.favicon.missing && (
                        <img
                          src={`/favicon/${item.favicon.id}`}
                          alt="icon"
                          style={{ width: "16px", height: "16px" }}
                        />
                      )}
                      <span style={{ fontSize: "16px" }}>
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
                        {linkMode === "source" ? (
                          <SourceIcon />
                        ) : (
                          <ArchiveIcon />
                        )}{" "}
                        {item.url}
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
            </Link>
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
        <Link
          href={getResultLink(item)}
          target={linkMode === "source" ? "_blank" : undefined}
          rel={linkMode === "source" ? "noopener noreferrer" : undefined}
          style={{ textDecoration: "none", color: "inherit" }}
        >
          <List.Item
            key={item.id}
            className="search-result-item"
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
              <Space size="small">
                {item.favicon && !item.favicon.missing && (
                  <img
                    src={`/favicon/${item.favicon.id}`}
                    alt="icon"
                    style={{ width: "16px", height: "16px" }}
                  />
                )}
                <span style={{ fontSize: "18px", fontWeight: "500" }}>
                  {item.title || "Untitled"}
                </span>
              </Space>

              <Space size="small" wrap>
                <Text type="secondary" style={{ fontSize: "12px" }}>
                  {linkMode === "source" ? <SourceIcon /> : <ArchiveIcon />}{" "}
                  {item.url}
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
        </Link>
      )}
    />
  );
};

export default React.memo(SearchResults);
