"use client";

import Image from "next/image";
import { useEffect, useState, useRef, useCallback } from "react";
import { Spin, Alert } from "antd";
import axios from "axios";
import { useAppStore } from "@/app/hooks/useAppStore";
import { useArchiveUrl } from "@/app/hooks/useArchiveUrl";
import archiveLink from "@/app/utils/archiveLink";

interface Link {
  id: number;
  text: string | null;
  pos: number;
  link_no: number;
  screen_pos: string | null;
  in_nav: boolean;
  url: string;
  title: string | null;
  available: boolean;
}

interface ScreenshotData {
  screenshot: string;
  links: Link[];
}

export default function ScreenshotPage() {
  const url = useArchiveUrl();
  const sosseDocument = useAppStore((state) => state.sosseDocument);
  const [screenshotData, setScreenshotData] = useState<ScreenshotData | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const fetchScreenshot = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await axios.get<ScreenshotData>(
          `/api/screenshot/${url}`,
        );
        setScreenshotData(response.data);

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

    fetchScreenshot();
  }, [url, sosseDocument]);

  const handleResize = useCallback(() => {
    if (!containerRef.current || !dimensions.width) return;

    const windowWidth = window.innerWidth;
    const ratio = windowWidth / dimensions.width;

    const links = containerRef.current.querySelectorAll(".img_link");
    links.forEach((link) => {
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
  }, [screenshotData, handleResize]);

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
        <Alert message="Error" description={error} type="error" showIcon />
      </div>
    );
  }

  if (!screenshotData || !sosseDocument) {
    return (
      <div style={{ padding: 40 }}>
        <Alert message="No screenshot available" type="info" showIcon />
      </div>
    );
  }

  const screenshotCount = sosseDocument.screenshot_count || 0;
  const screenshotFormat = sosseDocument.screenshot_format || "png";
  const crawlLast = sosseDocument.crawl_last
    ? new Date(sosseDocument.crawl_last).getTime() / 1000
    : Date.now() / 1000;

  return (
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

      {screenshotData.links.map((link) => {
        if (!link.screen_pos) return null;

        return (
          <a
            key={link.id}
            className="img_link"
            href={"/screenshot/" + archiveLink(link.url)}
            title={link.title || link.url}
            data-loc={link.screen_pos}
            data-available={link.available}
            style={{ left: 0, top: 0, width: 0, height: 0 }}
          />
        );
      })}

      {Array.from({ length: screenshotCount }, (_, i) => (
        <Image
          key={i}
          src={`${screenshotData.screenshot}_${i}.${screenshotFormat}?cachetime=${crawlLast}`}
          alt={`Screenshot ${i + 1}`}
          width={0}
          height={0}
          loading="lazy"
          unoptimized
        />
      ))}
    </div>
  );
}
