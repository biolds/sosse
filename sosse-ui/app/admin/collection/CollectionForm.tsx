"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
} from "antd";
import {
  SaveOutlined,
  ArrowLeftOutlined,
  DeleteOutlined,
  SettingOutlined,
  LinkOutlined,
  CameraOutlined,
  ReloadOutlined,
  LockOutlined,
} from "@ant-design/icons";
import axios from "axios";

const { Title } = Typography;
const { TextArea } = Input;

interface CollectionFormData {
  name: string;
  unlimited_regex?: string;
  limited_regex?: string;
  excluded_regex?: string;
  recursion_depth: number;
  keep_params: boolean;
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

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchCollection = useCallback(async () => {
    if (isNew || !collectionId) return;

    try {
      setLoading(true);
      const { data } = await axios.get(`/api/collection/${collectionId}/`);
      form.setFieldsValue(data);
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
                  <LinkOutlined /> URL Rules
                </>
              ),
              children: (
                <>
                  <Form.Item
                    label="Unlimited depth URL regex"
                    name="unlimited_regex"
                  >
                    <TextArea rows={4} />
                  </Form.Item>

                  <Form.Item
                    label="Limited depth URL regex"
                    name="limited_regex"
                  >
                    <TextArea rows={4} />
                  </Form.Item>

                  <Form.Item label="Excluded URL regex" name="excluded_regex">
                    <TextArea rows={4} />
                  </Form.Item>

                  <Form.Item
                    label="Limited recursion depth"
                    name="recursion_depth"
                  >
                    <InputNumber min={0} />
                  </Form.Item>

                  <Form.Item
                    label="Index URL parameters"
                    name="keep_params"
                    valuePropName="checked"
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
