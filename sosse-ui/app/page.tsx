"use client";

import { Input, Button, Card, List, Typography } from "antd";
import { SearchOutlined } from "@ant-design/icons";

const { Title, Text } = Typography;
const { Search } = Input;

export default function HomePage() {
  const recentSearches = [
    "machine learning tutorials",
    "web development best practices",
    "database optimization",
  ];

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", paddingTop: "60px" }}>
      <Title level={1} style={{ textAlign: "center", marginBottom: "40px" }}>
        Search Archived Pages
      </Title>
      <Search
        placeholder="Enter search query..."
        enterButton={<Button type="primary" icon={<SearchOutlined />}>Search</Button>}
        size="large"
        onSearch={(value) => console.log(value)}
      />
      <Card title="Recent Searches" style={{ marginTop: "40px" }}>
        <List
          dataSource={recentSearches}
          renderItem={(item) => (
            <List.Item>
              <Text>{item}</Text>
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
}
