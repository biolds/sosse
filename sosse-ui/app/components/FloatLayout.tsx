"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Button, Card, Layout, Spin } from "antd";
import { DownOutlined } from "@ant-design/icons";
import { useAppStore } from "@/app/hooks/useAppStore";
import ArchiveHeader from "@/app/components/ArchiveHeader";
import Header from "@/app/components/Header";
import Footer from "@/app/components/Footer";
import { FloatProvider } from "./FloatContext";
import { useFloat } from "./FloatContext";

function FloatLayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const archivePage = pathname.replace(/\/([^/]+)\/.*/, "$1");
  const isArchivePage = ["html", "text", "screenshot", "document"].includes(
    archivePage,
  );
  const isFloatingLayout = ["html", "screenshot"].includes(archivePage);
  const { sosseDocument, isFloatHeaderFolded, toggleFloatHeader } =
    useAppStore();
  const { loading } = useFloat();

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

  const cardRef = useRef<HTMLDivElement>(null);
  const [cardHeight, setCardHeight] = useState(0);

  useEffect(() => {
    if (cardRef.current) {
      setCardHeight(cardRef.current.offsetHeight);
    }
  }, [sosseDocument, isFloatHeaderFolded]);

  return isFloatingLayout ? (
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
            <ArchiveHeader />
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
  ) : (
    <Layout style={{ minHeight: "100vh" }}>
      <Header />
      {isArchivePage && <ArchiveHeader />}
      {children}
      <Footer />
    </Layout>
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
