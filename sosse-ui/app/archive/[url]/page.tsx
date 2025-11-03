"use client";

import { Card, Tabs, Typography, Descriptions } from "antd";
import { use } from "react";

const { Title, Paragraph, Text } = Typography;

export default function ArchivePage({ params }: { params: Promise<{ url: string }> }) {
  const { url } = use(params);
  const decodedUrl = decodeURIComponent(url);

  const tabItems = [
    {
      key: "text",
      label: "Text",
      children: (
        <div style={{ padding: "20px", background: "#f5f5f5", minHeight: "400px" }}>
          <Paragraph>
            This is the extracted text content from the archived page.
            Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
          </Paragraph>
          <Paragraph>
            Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
            Nisi ut aliquip ex ea commodo consequat.
          </Paragraph>
        </div>
      ),
    },
    {
      key: "html",
      label: "HTML",
      children: (
        <div style={{ padding: "20px", background: "#f5f5f5", minHeight: "400px" }}>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "monospace" }}>
            {`<!DOCTYPE html>
<html>
<head>
  <title>Archived Page</title>
</head>
<body>
  <h1>Sample Archived Content</h1>
  <p>This is the HTML view of the archived page.</p>
</body>
</html>`}
          </pre>
        </div>
      ),
    },
    {
      key: "screenshot",
      label: "Screenshot",
      children: (
        <div style={{ padding: "20px", background: "#f5f5f5", minHeight: "400px", textAlign: "center" }}>
          <div style={{ border: "2px dashed #d9d9d9", padding: "60px", borderRadius: "4px" }}>
            <Text type="secondary">Screenshot placeholder</Text>
            <br />
            <Text type="secondary" style={{ fontSize: "12px" }}>
              Archived screenshot would be displayed here
            </Text>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
      <Title level={2}>Archived Page: {decodedUrl}</Title>
      <Card style={{ marginBottom: "24px" }}>
        <Descriptions title="Metadata" bordered column={2}>
          <Descriptions.Item label="URL">{decodedUrl}</Descriptions.Item>
          <Descriptions.Item label="Archived Date">2024-01-15 14:32:10</Descriptions.Item>
          <Descriptions.Item label="Source">Web Crawler</Descriptions.Item>
          <Descriptions.Item label="Status Code">200</Descriptions.Item>
        </Descriptions>
      </Card>
      <Card>
        <Tabs defaultActiveKey="text" items={tabItems} />
      </Card>
    </div>
  );
}
