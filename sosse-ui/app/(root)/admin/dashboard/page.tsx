"use client";

import Link from "next/link";
import Image from "next/image";
import { useState, useEffect } from "react";
import {
  Button,
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Typography,
  Spin,
  Tag,
  Space,
  Select,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  FileTextOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  RiseOutlined,
  CloudDownloadOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import axios from "axios";
import { useAppStore } from "@/app/hooks/useAppStore";

const { Title, Text } = Typography;

interface CrawlQueueDocument {
  id: number;
  url: string;
  title: string | null;
  favicon_url: string | null;
  crawl_next: string | null;
  crawl_next_human: string | null;
  crawl_last: string | null;
  crawl_last_human: string | null;
  retries: number;
  worker_no: number | null;
  is_pending: boolean;
  in_history: boolean;
}

interface CrawlQueueData {
  pause: boolean;
  queue: CrawlQueueDocument[];
  total_documents: number;
  queue_new_count: number;
  queue_recurring_count: number;
  queue_pending_count: number;
  now: string;
}

export default function DashboardPage() {
  const [queueData, setQueueData] = useState<CrawlQueueData | null>(null);
  const [loading, setLoading] = useState(true);
  const { crawlQueueRefreshInterval, setCrawlQueueRefreshInterval } =
    useAppStore();

  useEffect(() => {
    fetchCrawlQueue();
    const interval = setInterval(fetchCrawlQueue, crawlQueueRefreshInterval);
    return () => clearInterval(interval);
  }, [crawlQueueRefreshInterval]);

  const fetchCrawlQueue = async () => {
    try {
      const response = await axios.get<CrawlQueueData>("/api/crawl_queue/");
      setQueueData(response.data);
    } catch (error) {
      console.error("Failed to fetch crawl queue:", error);
    } finally {
      setLoading(false);
    }
  };

  const toggleCrawlers = async () => {
    if (!queueData) return;

    try {
      const action = queueData.pause ? "pause" : "resume";
      await axios.post("/api/crawl_queue/", { action });
      await fetchCrawlQueue();
    } catch (error) {
      console.error("Failed to toggle crawlers:", error);
    }
  };

  const getDocumentStatus = (
    doc: CrawlQueueDocument,
  ): {
    status: string;
    color: string;
    icon: React.ReactNode;
  } => {
    if (doc.worker_no !== null) {
      return {
        status: "In progress",
        color: "processing",
        icon: <SyncOutlined spin />,
      };
    }
    if (
      doc.crawl_last === null ||
      (doc.crawl_next && new Date(doc.crawl_next) < new Date())
    ) {
      return {
        status: "Pending",
        color: "warning",
        icon: <ClockCircleOutlined />,
      };
    }
    return {
      status: "Scheduled",
      color: "default",
      icon: <CheckCircleOutlined />,
    };
  };

  const columns: ColumnsType<CrawlQueueDocument> = [
    {
      title: "URL",
      dataIndex: "url",
      key: "url",
      ellipsis: true,
      render: (url: string, record) => {
        const linkUrl = `/archive/${record.url}`;
        return (
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "16px",
                height: "16px",
                flexShrink: 0,
              }}
            >
              {record.favicon_url && (
                <Image
                  src={record.favicon_url}
                  alt="icon"
                  style={{ width: "16px", height: "16px" }}
                  width={16}
                  height={16}
                  unoptimized
                />
              )}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              {record.title ? (
                <>
                  <Link href={linkUrl} style={{ display: "block" }}>
                    {record.title}
                  </Link>
                  <Text type="secondary" ellipsis style={{ fontSize: "12px" }}>
                    {url}
                  </Text>
                </>
              ) : (
                <Link href={linkUrl}>{url}</Link>
              )}
            </div>
          </div>
        );
      },
    },
    {
      title: "Status",
      key: "status",
      width: 150,
      render: (_, record) => {
        const { status, color, icon } = getDocumentStatus(record);
        return (
          <Tag color={color} icon={icon}>
            {status}
          </Tag>
        );
      },
    },
    {
      title: "Crawl Next",
      key: "crawl_next",
      width: 150,
      render: (_, record) => {
        if (record.worker_no !== null) {
          return <Text type="secondary">In progress</Text>;
        }
        if (
          record.crawl_last === null ||
          (record.crawl_next && new Date(record.crawl_next) < new Date())
        ) {
          return <Text type="warning">Pending</Text>;
        }
        return (
          <Text
            type="secondary"
            title={record.crawl_next || ""}
            style={{ opacity: record.in_history ? 0.4 : 1.0 }}
          >
            {record.crawl_next_human || "Never"}
          </Text>
        );
      },
    },
    {
      title: "Crawled Last",
      key: "crawl_last",
      width: 150,
      render: (_, record) => (
        <Text
          type="secondary"
          title={record.crawl_last || ""}
          style={{ opacity: record.is_pending ? 0.4 : 1.0 }}
        >
          {record.crawl_last_human || "Never"}
        </Text>
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "50px" }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        <Title level={2}>Dashboard</Title>
        <Space>
          <Link href="/admin/crawl">
            <Button type="primary" icon={<CloudDownloadOutlined />}>
              Crawl New URLs
            </Button>
          </Link>
          <Button
            variant="outlined"
            color={queueData?.pause ? "danger" : "green"}
            icon={
              queueData?.pause ? (
                <PauseCircleOutlined />
              ) : (
                <PlayCircleOutlined />
              )
            }
            onClick={toggleCrawlers}
          >
            {queueData?.pause ? "Pause Crawlers" : "Start Crawlers"}
          </Button>
        </Space>
      </div>
      <Row gutter={[16, 16]} style={{ marginBottom: "24px" }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Documents"
              value={queueData?.total_documents || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="New URLs"
              value={queueData?.queue_new_count || 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Pending URLs"
              value={queueData?.queue_pending_count || 0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Recurring URLs"
              value={queueData?.queue_recurring_count || 0}
              prefix={<RiseOutlined />}
            />
          </Card>
        </Col>
      </Row>
      <Card
        title="Crawl Queue"
        styles={{ body: { padding: 0 } }}
        extra={
          <Select
            value={crawlQueueRefreshInterval}
            onChange={setCrawlQueueRefreshInterval}
            style={{ width: 70 }}
            suffixIcon={<ReloadOutlined />}
            options={[
              { value: 5000, label: "5s" },
              { value: 10000, label: "10s" },
              { value: 20000, label: "20s" },
            ]}
          />
        }
      >
        <Table
          columns={columns}
          dataSource={queueData?.queue || []}
          rowKey="id"
          pagination={false}
          rowClassName={(record) => {
            if (record.worker_no !== null) return "ant-table-row-running";
            if (
              record.crawl_last === null ||
              (record.crawl_next && new Date(record.crawl_next) < new Date())
            ) {
              return "ant-table-row-pending";
            }
            return "";
          }}
        />
      </Card>
    </div>
  );
}
