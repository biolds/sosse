"use client";

import React from "react";
import Link from "next/link";
import { useAppStore } from "@/app/hooks/useAppStore";
import archiveLink from "@/app/utils/archiveLink";

const SearchResultLink = ({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) => {
  const { linkMode } = useAppStore();

  const linkHref = linkMode === "archive" ? "/html/" + archiveLink(href) : href;
  return (
    <Link
      href={linkHref}
      target={
        linkMode === "source" && window.sosseConfig?.linksNewTab
          ? "_blank"
          : undefined
      }
      rel={
        linkMode === "source" && window.sosseConfig?.linksNoReferrer
          ? "noopener noreferrer"
          : undefined
      }
      style={{
        textDecoration: "none",
        color: "inherit",
        width: "100%",
        height: "100%",
      }}
    >
      {children}
    </Link>
  );
};

export default SearchResultLink;
