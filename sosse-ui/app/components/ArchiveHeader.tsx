"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { memo, useEffect } from "react";
import Image from "next/image";
import { Button, Divider, Layout, Space, Typography } from "antd";
import {
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

const { Content } = Layout;
const { Text } = Typography;

const ArchiveHeader: React.FC = () => {
  const pathname = usePathname();
  const archivePage = pathname.replace(/\/([^/]+)\/.*/, "$1");
  const url = useArchiveUrl();
  const archiveUrl = archiveLink(url);
  const { sosseDocument, setSosseDocument } = useAppStore();

  useEffect(() => {
    const fetchDocument = async () => {
      const response = await axios.get(`/api/document/${url}`);
      setSosseDocument(response.data || null);
    };

    setSosseDocument(null);
    fetchDocument();
  }, [url, setSosseDocument]);

  return (
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
                  type={archivePage === "screenshot" ? "primary" : "default"}
                  size="small"
                  icon={<CameraOutlined />}
                  style={{ fontSize: "12px", height: "28px" }}
                >
                  Screenshot
                </Button>
              </Link>
              <Link href={`/text/${archiveUrl}`}>
                <Button
                  type={archivePage === "document" ? "primary" : "default"}
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
            <Link
              href={`/?ft0=inc&ff0=lto_url&fo0=equal&fv0=${encodeURIComponent(url)}`}
              style={{ fontSize: "12px" }}
            >
              <ArrowLeftOutlined style={{ marginRight: "4px" }} />
              Linked by
            </Link>
            <Link
              href={`/?ft0=inc&ff0=lby_url&fo0=equal&fv0=${encodeURIComponent(url)}`}
              style={{ fontSize: "12px" }}
            >
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
  );
};

export default memo(ArchiveHeader);
