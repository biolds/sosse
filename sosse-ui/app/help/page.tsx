"use client";

import { Card, List, Typography } from "antd";
import { LinkOutlined } from "@ant-design/icons";

const { Title, Paragraph } = Typography;

export default function HelpPage() {
  const resources = [
    { title: "Getting Started Guide", url: "#" },
    { title: "API Documentation", url: "#" },
    { title: "Search Syntax Reference", url: "#" },
    { title: "Crawling Best Practices", url: "#" },
    { title: "Community Forum", url: "#" },
  ];

  return (
    <div style={{ maxWidth: "900px", margin: "0 auto" }}>
      <Title level={1}>Help & Resources</Title>
      <Card style={{ marginBottom: "24px" }}>
        <Title level={3}>About Sosse</Title>
        <Paragraph>
          Sosse is a software platform that lets users search, view, and manage archived web pages.
          It provides both a public-facing search interface and an admin panel for managing crawls,
          collections, tags, and analytics.
        </Paragraph>
      </Card>
      <Card title="Documentation & Resources">
        <List
          dataSource={resources}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                avatar={<LinkOutlined />}
                title={<a href={item.url}>{item.title}</a>}
              />
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
}
