"use client";

import { useCallback, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  App,
  Form,
  Input,
  Button,
  Select,
  Switch,
  Typography,
  Space,
  Spin,
} from "antd";
import {
  SaveOutlined,
  ArrowLeftOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import axios from "axios";

const { Title } = Typography;
const { TextArea } = Input;

interface DomainFormData {
  domain: string;
  browse_mode: string;
  robots_status: string;
  robots_ua_hash: string;
  robots_allow: string;
  robots_disallow: string;
  ignore_robots: boolean;
}

interface DomainFormProps {
  domainId?: string | number;
  isNew?: boolean;
}

const browseModeOptions = [
  { value: "detect", label: "Detect" },
  { value: "selenium", label: "Chromium" },
  { value: "firefox", label: "Firefox" },
  { value: "requests", label: "Python Requests" },
];

const robotsStatusOptions = [
  { value: "unknown", label: "Unknown" },
  { value: "empty", label: "Empty" },
  { value: "loaded", label: "Loaded" },
];

export default function DomainForm({
  domainId,
  isNew = false,
}: DomainFormProps) {
  const { message, modal } = App.useApp();
  const router = useRouter();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchDomain = useCallback(async () => {
    if (isNew || !domainId) return;

    try {
      setLoading(true);
      const response = await axios.get<DomainFormData>(
        `/api/domain/${domainId}/`,
      );
      form.setFieldsValue(response.data);
    } catch (error) {
      console.error("Error fetching domain:", error);
      message.error("Failed to load domain");
      router.push("/admin/domains");
    } finally {
      setLoading(false);
    }
  }, [domainId, isNew, form, router, message]);

  useEffect(() => {
    fetchDomain();
  }, [fetchDomain]);

  const handleSubmit = async (values: DomainFormData) => {
    try {
      setSubmitting(true);

      if (isNew) {
        await axios.post("/api/domain/", values);
        message.success("Domain created successfully");
      } else {
        await axios.put(`/api/domain/${domainId}/`, values);
        message.success("Domain updated successfully");
      }

      router.push("/admin/domains");
    } catch (error) {
      console.error("Error saving domain:", error);
      if (axios.isAxiosError(error) && error.response?.data) {
        const errorData = error.response.data;
        if (typeof errorData === "object") {
          Object.entries(errorData).forEach(([field, messages]) => {
            if (Array.isArray(messages)) {
              message.error(`${field}: ${messages.join(", ")}`);
            } else {
              message.error(`${field}: ${messages}`);
            }
          });
        } else {
          message.error("Failed to save domain");
        }
      } else {
        message.error("Failed to save domain");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    router.push("/admin/domains");
  };

  const handleDelete = async () => {
    if (!domainId || isNew) return;

    modal.confirm({
      title: "Delete Domain",
      content:
        "Are you sure you want to delete this domain? This action cannot be undone.",
      okText: "Delete",
      okType: "danger",
      cancelText: "Cancel",
      onOk: async () => {
        try {
          setDeleting(true);
          await axios.delete(`/api/domain/${domainId}/`);
          message.success("Domain deleted successfully");
          router.push("/admin/domains");
        } catch (error) {
          console.error("Error deleting domain:", error);
          message.error("Failed to delete domain");
        } finally {
          setDeleting(false);
        }
      },
    });
  };

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
          alignItems: "center",
          marginBottom: "24px",
        }}
      >
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={handleCancel}
          style={{ marginRight: "16px" }}
        />
        <Title level={2} style={{ margin: 0 }}>
          {isNew ? "New Domain" : "Edit Domain"}
        </Title>
      </div>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          browse_mode: "detect",
          robots_status: "unknown",
          robots_allow: "",
          robots_disallow: "",
          ignore_robots: false,
        }}
        style={{ maxWidth: "800px" }}
      >
        <Form.Item
          label="Domain"
          name="domain"
          rules={[{ required: true, message: "Please enter a domain" }]}
        >
          <Input placeholder="example.com" disabled={!isNew} />
        </Form.Item>

        <Form.Item
          label="Browse Mode"
          name="browse_mode"
          rules={[{ required: true, message: "Please select a browse mode" }]}
        >
          <Select options={browseModeOptions} />
        </Form.Item>

        <Form.Item
          label="Ignore Robots.txt"
          name="ignore_robots"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>

        <Form.Item
          label="Robots.txt Status"
          name="robots_status"
          rules={[{ message: "Please select a robots.txt status" }]}
        >
          <Select options={robotsStatusOptions} disabled />
        </Form.Item>

        <Form.Item label="Robots.txt Allow Rules" name="robots_allow">
          <TextArea
            rows={4}
            placeholder="Enter allow rules (one per line)"
            disabled
          />
        </Form.Item>

        <Form.Item label="Robots.txt Disallow Rules" name="robots_disallow">
          <TextArea
            rows={4}
            placeholder="Enter disallow rules (one per line)"
            disabled
          />
        </Form.Item>

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
            <Button onClick={handleCancel} disabled={submitting || deleting}>
              Cancel
            </Button>
            {!isNew && (
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={handleDelete}
                loading={deleting}
                disabled={submitting}
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
