"use client";

import Image from "next/image";
import { useEffect, useRef, useCallback } from "react";
import { Alert } from "antd";
import { useAppStore } from "@/app/hooks/useAppStore";
import { useDocumentLinks } from "@/app/hooks/useDocumentLinks";
import archiveLink from "@/app/utils/archiveLink";
import { useFloat } from "../../components/FloatContext";

export default function ScreenshotPage() {
  const sosseDocument = useAppStore((state) => state.sosseDocument);
  const { documentLinks, loading: linksLoading, error } = useDocumentLinks();
  const { setLoading } = useFloat();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(linksLoading);
  }, [linksLoading, setLoading]);

  const handleResize = useCallback(() => {
    if (!containerRef.current || !sosseDocument?.screenshot_size) return;

    const [width] = sosseDocument.screenshot_size.split("x").map(Number);
    const windowWidth = window.innerWidth;
    const ratio = windowWidth / width;

    const linkElements = containerRef.current.querySelectorAll(".img_link");
    linkElements.forEach((link) => {
      const htmlLink = link as HTMLElement;
      const pos = htmlLink.dataset.loc;
      if (!pos) return;

      const [left, top, linkWidth, linkHeight] = pos.split(",").map(Number);
      htmlLink.style.left = `${left * ratio}px`;
      htmlLink.style.top = `${top * ratio}px`;
      htmlLink.style.width = `${linkWidth * ratio}px`;
      htmlLink.style.height = `${linkHeight * ratio}px`;
    });

    const images = containerRef.current.querySelectorAll("img");
    images.forEach((img) => {
      img.style.width = `${width * ratio}px`;
    });
  }, [sosseDocument]);

  useEffect(() => {
    window.addEventListener("resize", handleResize);
    handleResize();

    const timer = setTimeout(handleResize, 300);

    return () => {
      window.removeEventListener("resize", handleResize);
      clearTimeout(timer);
    };
  }, [documentLinks, handleResize]);

  if (error) {
    return (
      <div style={{ padding: 40 }}>
        <Alert message="Error" description={error} type="error" showIcon />
      </div>
    );
  }

  if (!sosseDocument) {
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
    : "";
  const screenshotsUrl =
    typeof window !== "undefined" && window.sosseConfig?.screenshotsUrl
      ? window.sosseConfig.screenshotsUrl
      : "/screenshots/";
  const screenshotUrl = `${screenshotsUrl}${sosseDocument.image_name}`;

  const linksWithScreenPos = documentLinks.filter(
    (link) => link.screen_pos !== null,
  );

  return (
    <div style={{ position: "relative", minHeight: "100vh" }}>
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

        {linksWithScreenPos.map((link) => (
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
              if (i === 0) setLoading(false);
            }}
          />
        ))}
      </div>
    </div>
  );
}
