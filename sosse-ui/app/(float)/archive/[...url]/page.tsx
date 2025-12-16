"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Button, Card, Layout, Spin, Typography } from "antd";
import { DownOutlined } from "@ant-design/icons";
import axios from "axios";
import { useAppStore } from "@/app/hooks/useAppStore";
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
  const { isFloatHeaderFolded, toggleFloatHeader } = useAppStore();
  const cardRef = useRef<HTMLDivElement>(null);
  const [cardHeight, setCardHeight] = useState(0);
  const router = useRouter();

  const options = {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  };
  const crawlDate = sosseDocument && new Date(sosseDocument.crawl_last);
  const formattedDate =
    sosseDocument &&
    new Intl.DateTimeFormat(navigator.language, options).format(crawlDate);

  useEffect(() => {
    const fetchDocument = async () => {
      const response = await axios.get<Document>(`/api/document/${url}`);
      setDocument(response.data || null);
    };

    fetchDocument();
  }, [url]);

  useEffect(() => {
    if (cardRef.current) {
      setCardHeight(cardRef.current.offsetHeight);
    }
  }, [sosseDocument, isFloatHeaderFolded]);

  const iframeLoaded = () => {
    const iframe = document.getElementsByTagName("iframe");
    const links = iframe[0].contentWindow.document.getElementsByTagName("a");
    for (let i = 0; i < links.length; i++) {
      const link = links[i];
      link.onclick = function () {
        router.push(link.getAttribute("href").replace("/html/", "/archive/"));
      };
    }
  };
  return (
    <>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          position: "fixed",
          top: cardHeight ? -cardHeight : -200,
          left: 16,
          right: 16,
          zIndex: 1000,
          transform: isFloatHeaderFolded
            ? "translateY(0)"
            : `translateY(${cardHeight + 16}px)`,
          transition: "transform 0.3s ease",
        }}
      >
        <Card
          ref={cardRef}
          styles={{ body: { padding: 0 } }}
          style={{
            width: "100%",
            opacity: isFloatHeaderFolded ? 0 : 1,
            transform: isFloatHeaderFolded
              ? "translateY(-20px)"
              : "translateY(0)",
            transition: "opacity 0.3s ease, transform 0.3s ease",
            pointerEvents: isFloatHeaderFolded ? "none" : "auto",
          }}
        >
          <Layout>
            <Header />
            <Content style={{ padding: "24px" }}>
              <Title level={2}>{url}</Title>
            </Content>
          </Layout>
        </Card>
        <Button
          size="middle"
          onClick={() => toggleFloatHeader()}
          style={{
            marginTop: 8,
            borderRadius: "20px",
            paddingLeft: "20px",
            paddingRight: "20px",
            boxShadow: isFloatHeaderFolded
              ? "0 2px 8px rgba(22, 119, 255, 0.2)"
              : "0 2px 4px rgba(0, 0, 0, 0.1)",
            transition: "all 0.3s ease",
          }}
        >
          {sosseDocument && formattedDate}
          <DownOutlined
            style={{
              marginLeft: "8px",
              fontSize: "12px",
              transition: "transform 0.3s ease",
              display: "inline-block",
              transform: isFloatHeaderFolded
                ? "rotate(0deg)"
                : "rotate(180deg)",
            }}
          />
        </Button>
      </div>

      {sosseDocument == null ? (
        <div style={{ textAlign: "center", marginTop: "60px" }}>
          <Spin size="large" />
        </div>
      ) : (
        <iframe
          src={sosseDocument?.snapshot_url}
          sandbox="allow-top-navigation allow-same-origin"
          onLoad={iframeLoaded}
          style={{ width: "100%", height: "100%", border: "none" }}
        />
      )}
    </>
  );
}
