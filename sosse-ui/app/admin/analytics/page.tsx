"use client";

import { Card, Row, Col, Statistic, Typography } from "antd";
import { ArrowUpOutlined, ArrowDownOutlined } from "@ant-design/icons";

const { Title, Text } = Typography;

export default function AnalyticsPage() {
  return (
    <div>
      <Title level={2}>Analytics</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="Total Searches"
              value={45621}
              valueStyle={{ color: "#3f8600" }}
              prefix={<ArrowUpOutlined />}
              suffix="(+12%)"
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="Pages Crawled (30d)"
              value={8932}
              valueStyle={{ color: "#3f8600" }}
              prefix={<ArrowUpOutlined />}
              suffix="(+8%)"
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="Failed Crawls"
              value={152}
              valueStyle={{ color: "#cf1322" }}
              prefix={<ArrowDownOutlined />}
              suffix="(-3%)"
            />
          </Card>
        </Col>
      </Row>
      <Card title="Search Trends" style={{ marginBottom: "16px" }}>
        <div
          style={{
            height: "300px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#f5f5f5",
          }}
        >
          <Text type="secondary">
            Chart placeholder - Search volume over time
          </Text>
        </div>
      </Card>
      <Card title="Top Queries">
        <div
          style={{
            height: "200px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#f5f5f5",
          }}
        >
          <Text type="secondary">
            Chart placeholder - Most popular search queries
          </Text>
        </div>
      </Card>
    </div>
  );
}
