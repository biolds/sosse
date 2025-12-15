"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Card, Layout, Spin, Typography } from "antd";
import axios from "axios";
import Header from "@/app/components/Header";
import type { Document } from "@/app/types/document";

const { Title } = Typography;

const { Content } = Layout;

export default function ArchivePage() {
  const pathname = usePathname();
  const pathUrl = decodeURIComponent(pathname.replace("/archive/", ""));
  const url =
    pathUrl.startsWith("http:") || pathUrl.startsWith("https:")
      ? `${pathUrl.replace(/(http:|https:)/, "$1/")}`
      : pathUrl;
  const [sosseDocument, setDocument] = useState<Document | null>(null);

  useEffect(() => {
    const fetchDocument = async () => {
      const response = await axios.get<Document>(`/api/document/${url}`);
      setDocument(response.data || null);
    };

    fetchDocument();
  }, [url]);

  return (
    <>
      <Card styles={{ body: { padding: 0 } }} style={{ margin: 16 }}>
        <Layout>
          <Header />
          <Content style={{ padding: "24px" }}>
            <Title level={2}>{url}</Title>
          </Content>
        </Layout>
      </Card>
      {sosseDocument == null ? (
        <div style={{ textAlign: "center", marginTop: "60px" }}>
          <Spin size="large" />
        </div>
      ) : (
        <iframe
          src={sosseDocument?.snapshot_url}
          sandbox="allow-top-navigation allow-same-origin"
          style={{ width: "100%", height: "100%", border: "none" }}
        />
      )}
    </>
  );
}
