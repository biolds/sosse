"use client";

import { Card, Row, Col, Statistic, List, Typography } from "antd";
import {
  FileTextOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  RiseOutlined,
} from "@ant-design/icons";

const { Title } = Typography;

export default function DashboardPage() {
  const recentActivity = [
    "Crawl completed: example.com",
    "New collection created: Research",
    "Tag added: Technology",
    "Analytics report generated",
  ];

  return (
    <div>
      <Title level={2}>Dashboard</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Pages"
              value={12543}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Crawls"
              value={8}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Storage Used"
              value={245}
              suffix="GB"
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Daily Searches"
              value={1523}
              prefix={<RiseOutlined />}
            />
          </Card>
        </Col>
      </Row>
      <Card title="Recent Activity">
        <List
          dataSource={recentActivity}
          renderItem={(item) => <List.Item>{item}</List.Item>}
        />
      </Card>
    </div>
  );
}
