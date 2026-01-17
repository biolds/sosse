"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  App,
  Form,
  Input,
  InputNumber,
  Button,
  Select,
  Switch,
  Typography,
  Space,
  Spin,
  Tabs,
  Card,
  Statistic,
  Row,
  Col,
} from "antd";
import {
  SaveOutlined,
  ArrowLeftOutlined,
  BranchesOutlined,
  DeleteOutlined,
  SettingOutlined,
  CameraOutlined,
  ReloadOutlined,
  LockOutlined,
  FileTextOutlined,
  RobotOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import axios from "axios";
import HumanDate from "@/app/components/HumanDate";

const { Title } = Typography;
const { TextArea } = Input;

interface CollectionFormData {
  name: string;
  unlimited_regex?: string;
  limited_regex?: string;
  excluded_regex?: string;
  recursion_depth: number;
  keep_params: boolean;
  mimetype_regex: string;
  hide_documents?: boolean;
  snapshot_html: boolean;
  thumbnail_mode: string;
  take_screenshots?: boolean;
  remove_nav_elements: string;
  recrawl_freq: string;
  hash_mode: string;
  recrawl_condition: string;
  auth_login_url_re?: string;
  auth_form_selector?: string;
  documents_count?: number;
  robotstxt_rejected?: number;
  crawl_first?: string;
  crawl_last?: string;
  crawl_next?: string;
  errors?: number;
}

interface CollectionFormProps {
  collectionId?: string | number;
  isNew?: boolean;
}

/* -------------------- Choices -------------------- */

const recrawlFreqOptions = [
  { value: "none", label: "Once" },
  { value: "constant", label: "Constant time" },
  { value: "adaptive", label: "Adaptive" },
];

const hashModeOptions = [
  { value: "raw", label: "Raw content" },
  { value: "no_numbers", label: "Normalize numbers" },
];

const recrawlConditionOptions = [
  { value: "change", label: "On change only" },
  { value: "always", label: "Always" },
  { value: "manual", label: "On change or manual trigger" },
];

const removeNavOptions = [
  { value: "idx", label: "From index" },
  { value: "scr", label: "Index + screenshots" },
  { value: "yes", label: "Index + screens + HTML" },
  { value: "no", label: "No" },
];

const thumbnailModeOptions = [
  { value: "preview", label: "Metadata preview" },
  { value: "prevscreen", label: "Preview or screenshot" },
  { value: "screenshot", label: "Screenshot" },
  { value: "none", label: "None" },
];

/* -------------------- Component -------------------- */

export default function CollectionForm({
  collectionId,
  isNew = false,
}: CollectionFormProps) {
  const { message, modal } = App.useApp();
  const router = useRouter();
  const [form] = Form.useForm();
  const recursionDepth = Form.useWatch("recursion_depth", form);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [statistics, setStatistics] = useState<{
    documents_count?: number;
    robotstxt_rejected?: number;
    crawl_first?: string;
    crawl_last?: string;
    crawl_next?: string;
    errors?: number;
  }>({});

  const fetchCollection = useCallback(async () => {
    if (isNew || !collectionId) return;

    try {
      setLoading(true);
      const { data } = await axios.get(`/api/collection/${collectionId}/`);
      form.setFieldsValue(data);
      setStatistics({
        documents_count: data.documents_count,
        robotstxt_rejected: data.robotstxt_rejected,
        crawl_first: data.crawl_first,
        crawl_last: data.crawl_last,
        crawl_next: data.crawl_next,
        errors: data.errors,
      });
    } catch {
      message.error("Failed to load collection");
      router.push("/admin/collections");
    } finally {
      setLoading(false);
    }
  }, [collectionId, isNew, form, message, router]);

  useEffect(() => {
    fetchCollection();
  }, [fetchCollection]);

  const handleSubmit = async (values: CollectionFormData) => {
    try {
      setSubmitting(true);
      if (isNew) {
        await axios.post("/api/collection/", values);
        message.success("Collection created");
      } else {
        await axios.put(`/api/collection/${collectionId}/`, values);
        message.success("Collection updated");
      }
      router.push("/admin/collections");
    } catch {
      message.error("Failed to save collection");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = () => {
    if (!collectionId || isNew) return;

    modal.confirm({
      title: "Delete collection",
      content: "This action is irreversible.",
      okType: "danger",
      onOk: async () => {
        try {
          setDeleting(true);
          await axios.delete(`/api/collection/${collectionId}/`);
          message.success("Collection deleted");
          router.push("/admin/collections");
        } catch {
          message.error("Failed to delete collection");
        } finally {
          setDeleting(false);
        }
      },
    });
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 64 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Space align="center" style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()} />
        <Title level={2} style={{ margin: 0 }}>
          {isNew ? "New Collection" : "Edit Collection"}
        </Title>
      </Space>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        style={{ maxWidth: 900 }}
        initialValues={{
          recrawl_freq: "adaptive",
          recrawl_condition: "manual",
          hash_mode: "no_numbers",
          recursion_depth: 1,
          keep_params: true,
          snapshot_html: true,
          thumbnail_mode: "preview",
          remove_nav_elements: "idx",
        }}
      >
        <Tabs
          type="card"
          items={[
            {
              key: "general",
              label: (
                <>
                  <SettingOutlined /> General
                </>
              ),
              children: (
                <>
                  <Form.Item
                    label="Name"
                    name="name"
                    rules={[{ required: true }]}
                  >
                    <Input />
                  </Form.Item>

                  {!isNew && (
                    <>
                      <Form.Item label="Statistics">
                        <Card>
                          <Row gutter={16}>
                            <Col span={8}>
                              <Link
                                href={`/?collection=${collectionId}`}
                                style={{ textDecoration: "none" }}
                              >
                                <Statistic
                                  title="Documents"
                                  value={statistics.documents_count}
                                  prefix={<FileTextOutlined />}
                                  valueStyle={{ color: "#1890ff" }}
                                />
                              </Link>
                            </Col>
                            <Col span={8}>
                              <Link
                                href={`/?collection=${collectionId}&robotstxt_rejected=only`}
                                style={{ textDecoration: "none" }}
                              >
                                <Statistic
                                  title="Robots.txt rejected"
                                  value={statistics.robotstxt_rejected}
                                  prefix={<RobotOutlined />}
                                  valueStyle={{
                                    color:
                                      statistics.robotstxt_rejected &&
                                      statistics.robotstxt_rejected > 0
                                        ? "#faad14"
                                        : undefined,
                                  }}
                                />
                              </Link>
                            </Col>
                            <Col span={8}>
                              <Link
                                href={`/?collection=${collectionId}&has_error=only`}
                                style={{ textDecoration: "none" }}
                              >
                                <Statistic
                                  title="Errors"
                                  value={statistics.errors}
                                  prefix={<ExclamationCircleOutlined />}
                                  valueStyle={{
                                    color:
                                      statistics.errors && statistics.errors > 0
                                        ? "#ff4d4f"
                                        : undefined,
                                  }}
                                />
                              </Link>
                            </Col>
                          </Row>
                          <Row gutter={16} style={{ marginTop: 16 }}>
                            <Col span={8}>
                              <div>
                                <span
                                  style={{
                                    color: "var(--ant-color-text-description)",
                                    fontSize:
                                      "var(--ant-statistic-title-font-size)",
                                  }}
                                >
                                  <ClockCircleOutlined
                                    style={{ marginRight: "8px" }}
                                  />
                                  Crawled first
                                </span>
                                <div
                                  style={{ fontSize: "24px", fontWeight: 600 }}
                                >
                                  {statistics.crawl_first
                                    ? new Date(
                                        statistics.crawl_first,
                                      ).toLocaleString()
                                    : "-"}
                                </div>
                              </div>
                            </Col>
                            <Col span={8}>
                              <div>
                                <span
                                  style={{
                                    color: "var(--ant-color-text-description)",
                                    fontSize:
                                      "var(--ant-statistic-title-font-size)",
                                  }}
                                >
                                  <ClockCircleOutlined
                                    style={{ marginRight: "8px" }}
                                  />
                                  Crawled last
                                </span>
                                <div
                                  style={{ fontSize: "24px", fontWeight: 600 }}
                                >
                                  <HumanDate date={statistics.crawl_last} />
                                </div>
                              </div>
                            </Col>
                            <Col span={8}>
                              <div>
                                <span
                                  style={{
                                    color: "var(--ant-color-text-description)",
                                    fontSize:
                                      "var(--ant-statistic-title-font-size)",
                                  }}
                                >
                                  <ClockCircleOutlined
                                    style={{ marginRight: "8px" }}
                                  />
                                  Crawl next
                                </span>
                                <div
                                  style={{ fontSize: "24px", fontWeight: 600 }}
                                >
                                  <HumanDate date={statistics.crawl_next} />
                                </div>
                              </div>
                            </Col>
                          </Row>
                        </Card>
                      </Form.Item>
                    </>
                  )}

                  <Form.Item
                    label="Hide documents from search"
                    name="hide_documents"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                </>
              ),
            },
            {
              key: "urls",
              label: (
                <>
                  <BranchesOutlined /> Recursion
                </>
              ),
              children: (
                <>
                  <Form.Item
                    label="Unlimited depth URL regex"
                    name="unlimited_regex"
                    help="Leave empty to disable unlimited depth crawling"
                  >
                    <TextArea
                      rows={4}
                      placeholder={`# Enter one regex per line
^https://example.com/.*$`}
                    />
                  </Form.Item>
                  <Form.Item
                    label="Limited depth URL regex"
                    name="limited_regex"
                    help="Leave empty to disable limited depth crawling"
                  >
                    <TextArea
                      rows={4}
                      placeholder={`# Enter one regex per line
^https://example.com/.*$`}
                      disabled={recursionDepth === 0}
                    />
                  </Form.Item>
                  <Form.Item
                    label="Limited recursion depth"
                    name="recursion_depth"
                  >
                    <InputNumber min={0} />
                  </Form.Item>
                  <Form.Item
                    label="Excluded URL regex"
                    name="excluded_regex"
                    help="Leave empty to not exclude any URLs"
                  >
                    <TextArea
                      rows={4}
                      placeholder={`# Enter one regex per line
^https://example.com/.*$`}
                    />
                  </Form.Item>
                  <Form.Item
                    label="Document MIME type regex"
                    name="mimetype_regex"
                    help="Only index documents with MIME types matching this regex"
                    rules={[{ required: true }]}
                  >
                    <Input />
                  </Form.Item>
                  <Form.Item
                    label="Index URL parameters"
                    name="keep_params"
                    valuePropName="checked"
                    help="URL with different parameters will be treated as different pages (e.g., ?ref=twitter)"
                  >
                    <Switch />
                  </Form.Item>
                </>
              ),
            },
            {
              key: "archive",
              label: (
                <>
                  <CameraOutlined /> Archive
                </>
              ),
              children: (
                <>
                  <Form.Item
                    label="Archive HTML & assets"
                    name="snapshot_html"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item label="Thumbnail mode" name="thumbnail_mode">
                    <Select options={thumbnailModeOptions} />
                  </Form.Item>

                  <Form.Item
                    label="Take screenshots"
                    name="take_screenshots"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>

                  <Form.Item
                    label="Remove navigation elements"
                    name="remove_nav_elements"
                  >
                    <Select options={removeNavOptions} />
                  </Form.Item>
                </>
              ),
            },
            {
              key: "recrawl",
              label: (
                <>
                  <ReloadOutlined /> Recrawl
                </>
              ),
              children: (
                <>
                  <Form.Item label="Crawl frequency" name="recrawl_freq">
                    <Select options={recrawlFreqOptions} />
                  </Form.Item>

                  <Form.Item label="Change detection" name="hash_mode">
                    <Select options={hashModeOptions} />
                  </Form.Item>

                  <Form.Item label="Condition" name="recrawl_condition">
                    <Select options={recrawlConditionOptions} />
                  </Form.Item>
                </>
              ),
            },
            {
              key: "auth",
              label: (
                <>
                  <LockOutlined /> Authentication
                </>
              ),
              children: (
                <>
                  <Form.Item label="Login URL regex" name="auth_login_url_re">
                    <Input />
                  </Form.Item>

                  <Form.Item
                    label="Authentication form selector"
                    name="auth_form_selector"
                  >
                    <Input />
                  </Form.Item>
                </>
              ),
            },
          ]}
        />

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={submitting}
            >
              Save
            </Button>

            {!isNew && (
              <Button
                danger
                icon={<DeleteOutlined />}
                loading={deleting}
                onClick={handleDelete}
              >
                Delete
              </Button>
            )}
          </Space>
        </Form.Item>
      </Form>
    </div>
  );
}
