"use client";

import { useEffect, useState } from "react";
import { useAppStore } from "@/app/hooks/useAppStore";
import { useArchiveUrl } from "@/app/hooks/useArchiveUrl";
import axios from "axios";
import type { Link } from "@/app/hooks/useAppStore";
import { Spin } from "antd";
import archiveLink from "@/app/utils/archiveLink";

export default function TextPage() {
  const url = useArchiveUrl();
  const sosseDocument = useAppStore((state) => state.sosseDocument);
  const documentLinks = useAppStore((state) => state.documentLinks);
  const setDocumentLinks = useAppStore((state) => state.setDocumentLinks);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLinks = async () => {
      try {
        setLoading(true);
        const response = await axios.get<Link[]>(`/api/link/${url}`);
        setDocumentLinks(response.data);
      } catch (err) {
        console.error("Failed to load links:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchLinks();
  }, [url, setDocumentLinks]);

  if (loading || !sosseDocument) {
    return (
      <div style={{ padding: 40, textAlign: "center" }}>
        <Spin size="large" />
      </div>
    );
  }

  const renderContent = () => {
    if (!sosseDocument.content) {
      return null;
    }

    const content: JSX.Element[] = [];
    let contentPos = 0;
    const links = documentLinks.sort((a, b) => a.link_no - b.link_no);
    const linksCount = links.length;
    let linkNo = 0;

    const lines = sosseDocument.content.split("\n");

    for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
      let line = lines[lineIdx];
      const lineElements: JSX.Element[] = [];
      let elementKey = 0;

      while (
        linkNo < linksCount &&
        links[linkNo].pos < contentPos + line.length
      ) {
        const link = links[linkNo];
        const linkPos = link.pos - contentPos;
        const txt = line.slice(0, linkPos);

        if (txt) {
          lineElements.push(
            <span key={`text-${lineIdx}-${elementKey++}`}>{txt}</span>,
          );
        }

        if (!link.in_nav) {
          line = line.slice(linkPos + (link.text?.length || 0));
          contentPos += txt.length + (link.text?.length || 0);
        }

        const linkText = link.text || "<no text link>";
        const linkColor = link.available ? "#1890ff" : "#ff9500";

        lineElements.push(
          <a
            key={`link-${lineIdx}-${elementKey++}`}
            href={"/text/" + archiveLink(link.url)}
            title={link.url}
            style={{ color: linkColor }}
          >
            {linkText}
          </a>,
        );

        linkNo++;
      }

      contentPos += line.length + 1;

      if (line) {
        lineElements.push(
          <span key={`text-${lineIdx}-${elementKey++}`}>{line}</span>,
        );
      }

      content.push(
        <div key={`line-${lineIdx}`}>
          {lineElements.length > 0 ? lineElements : <span>{line}</span>}
          <br />
        </div>,
      );
    }

    return content;
  };

  return (
    <div style={{ padding: "20px", whiteSpace: "pre-wrap" }}>
      {renderContent()}
    </div>
  );
}
