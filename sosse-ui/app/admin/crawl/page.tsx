"use client";

import { Card, Form, Input, Button, Select, InputNumber, Typography } from "antd";

const { Title } = Typography;
const { TextArea } = Input;

export default function CrawlPage() {
  const onFinish = (values: any) => {
    console.log("Crawl triggered:", values);
  };

  return (
    <div>
      <Title level={2}>Crawl New URL</Title>
      <Card>
        <Form
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            depth: 1,
            method: "get",
          }}
        >
          <Form.Item
            label="URL"
            name="url"
            rules={[{ required: true, message: "Please enter a URL" }]}
          >
            <Input placeholder="https://example.com" size="large" />
          </Form.Item>
          <Form.Item
            label="Crawl Depth"
            name="depth"
            help="Number of levels to follow links"
          >
            <InputNumber min={1} max={10} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="Collection" name="collection">
            <Select placeholder="Select collection (optional)">
              <Select.Option value="research">Research</Select.Option>
              <Select.Option value="news">News</Select.Option>
              <Select.Option value="documentation">Documentation</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="Tags" name="tags">
            <Select mode="tags" placeholder="Add tags">
              <Select.Option value="tech">Tech</Select.Option>
              <Select.Option value="science">Science</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item label="Notes" name="notes">
            <TextArea rows={4} placeholder="Optional notes about this crawl" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" size="large">
              Start Crawl
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
