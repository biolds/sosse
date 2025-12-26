"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Button, Card, Layout, Spin, Space, Typography, Divider } from "antd";
import {
  DownOutlined,
  FileTextOutlined,
  GlobalOutlined,
  CameraOutlined,
  SettingOutlined,
  ExportOutlined,
  ArrowRightOutlined,
  ArrowLeftOutlined,
  FolderOutlined,
} from "@ant-design/icons";
import axios from "axios";
import { useAppStore } from "@/app/hooks/useAppStore";
import { useArchiveUrl } from "@/app/hooks/useArchiveUrl";
import archiveLink from "@/app/utils/archiveLink";
import SourceLink from "@/app/utils/SourceLink";
import Header from "@/app/components/Header";
import { FloatProvider, useFloat } from "./FloatContext";

const { Content } = Layout;
const { Text } = Typography;

function FloatLayoutContent({ children }: { children: React.ReactNode }) {
  const url = useArchiveUrl();
  const archiveUrl = archiveLink(url);
  const pathname = usePathname();
  const archivePage = pathname.replace(/\/([^/]+)\/.*/, "$1");
  const {
    sosseDocument,
    setSosseDocument,
    isFloatHeaderFolded,
    toggleFloatHeader,
  } = useAppStore();
  const { loading } = useFloat();
  const cardRef = useRef<HTMLDivElement>(null);
  const [cardHeight, setCardHeight] = useState(0);

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
      const response = await axios.get(`/api/document/${url}`);
      setSosseDocument(response.data || null);
    };

    fetchDocument();
  }, [url, setSosseDocument]);

  useEffect(() => {
    if (cardRef.current) {
      setCardHeight(cardRef.current.offsetHeight);
    }
  }, [sosseDocument, isFloatHeaderFolded]);

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
          <Layout style={{ borderRadius: "8px" }}>
            <Header style={{ borderRadius: "8px 8px 0 0" }} />
            <Content style={{ padding: "16px 20px" }}>
              <div style={{ display: "flex", gap: "16px" }}>
                <div style={{ flex: 1 }}>
                  {/* Title and URL */}
                  <div style={{ marginBottom: "12px" }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        marginBottom: "6px",
                      }}
                    >
                      {sosseDocument &&
                        sosseDocument.favicon &&
                        !sosseDocument.favicon.missing && (
                          <Image
                            src={`/favicon/${sosseDocument.favicon.id}`}
                            alt="icon"
                            width={16}
                            height={16}
                            style={{ marginRight: "8px", flexShrink: 0 }}
                            unoptimized
                          />
                        )}
                      <Text
                        strong
                        style={{
                          fontSize: "20px",
                          lineHeight: "24px",
                        }}
                      >
                        {sosseDocument && sosseDocument.title}
                      </Text>
                    </div>
                    <Text type="secondary" style={{ fontSize: "13px" }}>
                      {url}
                    </Text>
                  </div>

                  {/* Collection */}
                  {sosseDocument && (
                    <div style={{ marginBottom: "12px" }}>
                      <Space size={4} align="center">
                        <FolderOutlined style={{ fontSize: "12px" }} />
                        <Text style={{ fontSize: "13px" }}>
                          Collection: {sosseDocument.collection}
                        </Text>
                      </Space>
                    </div>
                  )}

                  <Divider style={{ margin: "12px 0" }} />

                  {/* View Mode Buttons */}
                  <div style={{ marginBottom: "12px" }}>
                    <Space size={6} wrap>
                      <Link href={`/html/${archiveUrl}`}>
                        <Button
                          type={archivePage === "html" ? "primary" : "default"}
                          size="small"
                          icon={<GlobalOutlined />}
                          style={{ fontSize: "12px", height: "28px" }}
                        >
                          Web
                        </Button>
                      </Link>
                      <Link href={`/text/${archiveUrl}`}>
                        <Button
                          type={archivePage === "text" ? "primary" : "default"}
                          size="small"
                          icon={<FileTextOutlined />}
                          style={{ fontSize: "12px", height: "28px" }}
                        >
                          Text
                        </Button>
                      </Link>
                      <Link href={`/screenshot/${archiveUrl}`}>
                        <Button
                          type={
                            archivePage === "screenshot" ? "primary" : "default"
                          }
                          size="small"
                          icon={<CameraOutlined />}
                          style={{ fontSize: "12px", height: "28px" }}
                        >
                          Screenshot
                        </Button>
                      </Link>
                      <Link href={`/text/${archiveUrl}`}>
                        <Button
                          type={
                            archivePage === "document" ? "primary" : "default"
                          }
                          size="small"
                          icon={<SettingOutlined />}
                          style={{ fontSize: "12px", height: "28px" }}
                        >
                          Admin
                        </Button>
                      </Link>
                    </Space>
                  </div>

                  {/* Quick Links */}
                  <Space
                    size={12}
                    wrap
                    style={{ fontSize: "12px", lineHeight: "20px" }}
                  >
                    <SourceLink href={url} style={{ fontSize: "12px" }}>
                      <ExportOutlined style={{ marginRight: "4px" }} />
                      Source page
                    </SourceLink>
                    <Link href="#" style={{ fontSize: "12px" }}>
                      <ArrowLeftOutlined style={{ marginRight: "4px" }} />
                      Linked by
                    </Link>
                    <Link href="#" style={{ fontSize: "12px" }}>
                      <ArrowRightOutlined style={{ marginRight: "4px" }} />
                      Links to
                    </Link>
                  </Space>
                </div>

                {/* Preview Thumbnail */}
                {sosseDocument && sosseDocument.preview && (
                  <div
                    style={{
                      maxHeight: "120px",
                      maxWidth: "180px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <Image
                      width={0}
                      height={0}
                      sizes="180px"
                      alt="preview"
                      src={sosseDocument.preview}
                      style={{
                        borderRadius: "4px",
                        width: "auto",
                        height: "auto",
                        maxHeight: "120px",
                        maxWidth: "180px",
                        objectFit: "contain",
                      }}
                      unoptimized
                    />
                  </div>
                )}
              </div>
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
        {loading && (
          <div style={{ textAlign: "center", marginTop: "60px" }}>
            <Spin size="large" />
          </div>
        )}
      </div>
      {sosseDocument == null ? (
        <div style={{ textAlign: "center", marginTop: "60px" }}>
          <Spin size="large" />
        </div>
      ) : (
        children
      )}
    </>
  );
}

export default function FloatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <FloatProvider>
      <FloatLayoutContent>{children}</FloatLayoutContent>
    </FloatProvider>
  );
}
