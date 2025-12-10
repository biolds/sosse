"use client";

import { useState } from "react";
import { Form, Input, Button, Card, Typography, message } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useRouter, useSearchParams } from "next/navigation";
import { useAppStore } from "../useAppStore";

const { Title } = Typography;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnTo = searchParams.get("returnTo") || "/";
  const { login } = useAppStore();

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);

    const success = await login(values.username, values.password);

    if (success) {
      message.success("Login successful");
      router.push(returnTo);
    } else {
      message.error("Invalid credentials");
    }

    setLoading(false);
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
            <Input prefix={<UserOutlined />} placeholder="Username" size="large" autoFocus />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: "Please enter your password" }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Password" size="large" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={loading}>
              Log In
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
