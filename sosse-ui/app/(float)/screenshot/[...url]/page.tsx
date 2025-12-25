"use client";

import Image from "next/image";
import { useEffect, useState, useRef, useCallback } from "react";
import { Spin, Alert } from "antd";
import axios from "axios";
import { useAppStore } from "@/app/hooks/useAppStore";
import { useArchiveUrl } from "@/app/hooks/useArchiveUrl";
import archiveLink from "@/app/utils/archiveLink";
import type { Link } from "@/app/hooks/useAppStore";

export default function ScreenshotPage() {
  const url = useArchiveUrl();
  const sosseDocument = useAppStore((state) => state.sosseDocument);
  const documentLinks = useAppStore((state) => state.documentLinks);
  const setDocumentLinks = useAppStore((state) => state.setDocumentLinks);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [imageLoading, setImageLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const fetchLinks = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await axios.get<Link[]>(`/api/link/${url}`);
        const filteredLinks = response.data.filter(
          (link) => link.screen_pos !== null,
        );
        setDocumentLinks(filteredLinks);

        if (sosseDocument?.screenshot_size) {
          const [width, height] = sosseDocument.screenshot_size
            .split("x")
            .map(Number);
          setDimensions({ width, height });
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load screenshot",
        );
      } finally {
        setLoading(false);
      }
    };

    fetchLinks();
  }, [url, sosseDocument, setDocumentLinks]);

  const handleResize = useCallback(() => {
    if (!containerRef.current || !dimensions.width) return;

    const windowWidth = window.innerWidth;
    const ratio = windowWidth / dimensions.width;

    const linkElements = containerRef.current.querySelectorAll(".img_link");
    linkElements.forEach((link) => {
      const htmlLink = link as HTMLElement;
      const pos = htmlLink.dataset.loc;
      if (!pos) return;

      const [left, top, width, height] = pos.split(",").map(Number);
      htmlLink.style.left = `${left * ratio}px`;
      htmlLink.style.top = `${top * ratio}px`;
      htmlLink.style.width = `${width * ratio}px`;
      htmlLink.style.height = `${height * ratio}px`;
    });

    const images = containerRef.current.querySelectorAll("img");
    images.forEach((img) => {
      img.style.width = `${dimensions.width * ratio}px`;
    });
  }, [dimensions.width]);

  useEffect(() => {
    window.addEventListener("resize", handleResize);
    handleResize();

    const timer = setTimeout(handleResize, 300);

    return () => {
      window.removeEventListener("resize", handleResize);
      clearTimeout(timer);
    };
  }, [documentLinks, handleResize]);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 40 }}>
        <Alert title="Error" description={error} type="error" showIcon />
      </div>
    );
  }

  if (!sosseDocument) {
    return (
      <div style={{ padding: 40 }}>
        <Alert title="No screenshot available" type="info" showIcon />
      </div>
    );
  }

  const screenshotCount = sosseDocument.screenshot_count || 0;
  const screenshotFormat = sosseDocument.screenshot_format || "png";
  const crawlLast = sosseDocument.crawl_last
    ? new Date(sosseDocument.crawl_last).getTime() / 1000
    : Date.now() / 1000;
  const screenshotsUrl =
    typeof window !== "undefined" && window.sosseConfig?.screenshotsUrl
      ? window.sosseConfig.screenshotsUrl
      : "/screenshots/";
  const screenshotUrl = `${screenshotsUrl}${sosseDocument.image_name}`;

  return (
    <div style={{ position: "relative", minHeight: "100vh" }}>
      {imageLoading && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            zIndex: 1000,
          }}
        >
          <Spin size="large" />
        </div>
      )}
      <div
        ref={containerRef}
        id="screenshots"
        style={{ marginTop: 5, position: "relative" }}
      >
        <style jsx>{`
          #screenshots img {
            margin-top: -5px;
            display: block;
          }
          .img_link {
            position: absolute;
            margin-top: -4px;
          }
          .img_link:hover {
            box-shadow: 0px 0px 4px 4px #91baff;
            margin: -4px 0px 0px -2px;
            padding: 0px 8px 4px 0px;
          }
          .img_link[data-available="false"]:hover {
            box-shadow: 0px 0px 4px 4px #ff9191;
          }
        `}</style>

        {documentLinks.map((link) => (
          <a
            key={link.id}
            className="img_link"
            href={"/screenshot/" + archiveLink(link.url)}
            title={link.title || link.url}
            data-loc={link.screen_pos}
            data-available={link.available}
            style={{ left: 0, top: 0, width: 0, height: 0 }}
          />
        ))}

        {Array.from({ length: screenshotCount }, (_, i) => (
          <Image
            key={i}
            src={`${screenshotUrl}_${i}.${screenshotFormat}?cachetime=${crawlLast}`}
            alt={`Screenshot ${i + 1}`}
            width={0}
            height={0}
            loading="lazy"
            unoptimized
            onLoad={() => {
              if (i === 0) setImageLoading(false);
            }}
          />
        ))}
      </div>
    </div>
  );
}
