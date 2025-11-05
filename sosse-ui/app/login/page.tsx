"use client";

import { Form, Input, Button, Card, Typography } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";

const { Title } = Typography;

export default function LoginPage() {
  const onFinish = (values: Record<string, unknown>) => {
    console.log("Login:", values);
  };

  return (
    <div style={{ maxWidth: "400px", margin: "60px auto" }}>
      <Card>
        <Title level={2} style={{ textAlign: "center", marginBottom: "30px" }}>
          Login to Sosse
        </Title>
        <Form
          name="login"
          onFinish={onFinish}
          layout="vertical"
          autoComplete="off"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: "Please enter your username" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="Username" size="large" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: "Please enter your password" }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Password" size="large" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block size="large">
              Log In
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
