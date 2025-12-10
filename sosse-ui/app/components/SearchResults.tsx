import { List, Typography, Space, Tag, Card, Row, Col } from "antd";
import { LinkOutlined, CalendarOutlined } from "@ant-design/icons";

const { Text, Paragraph } = Typography;

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
}

interface SearchResultsProps {
  results: SearchResult[];
  viewMode: "list" | "card";
}

const formatDate = (dateString?: string) => {
  if (!dateString) return null;
  return new Date(dateString).toLocaleDateString();
};

export default function SearchResults({
  results,
  viewMode,
}: SearchResultsProps) {
  if (viewMode === "card") {
    return (
      <Row gutter={[16, 16]}>
        {results.map((item) => (
          <Col key={item.id} xs={24} sm={12} lg={8}>
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
                    style={{
                      height: "200px",
                      backgroundColor: "#f0f0f0",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Text type="secondary">No preview</Text>
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
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: "16px" }}
                    >
                      {item.title || "Untitled"}
                    </a>
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
                      <LinkOutlined /> {item.url}
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
                        style={{ marginBottom: "8px", marginTop: "8px", fontSize: "13px" }}
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
            <Space size="small">
              {item.favicon && !item.favicon.missing && (
                <img
                  src={`/favicon/${item.favicon.id}`}
                  alt="icon"
                  style={{ width: "16px", height: "16px" }}
                />
              )}
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ fontSize: "18px", fontWeight: "500" }}
              >
                {item.title || "Untitled"}
              </a>
            </Space>

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
      )}
    />
  );
}
