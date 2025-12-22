"use client";

import React from "react";
import Link from "next/link";
import { useAppStore } from "@/app/hooks/useAppStore";

const SearchResultLink = ({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) => {
  const { linkMode } = useAppStore();

  const getResultLink = (url: string) => {
    if (linkMode === "archive") {
      return `/html/${url}`;
    }
    return url;
  };

  return (
    <Link
      href={getResultLink(href)}
      target={linkMode === "source" ? "_blank" : undefined}
      rel={linkMode === "source" ? "noopener noreferrer" : undefined}
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
