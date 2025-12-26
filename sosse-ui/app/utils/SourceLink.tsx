"use client";

import Link from "next/link";

export default function SourceLink({
  href,
  children,
  style,
}: {
  href: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <Link
      href={href}
      target={window.sosseConfig?.linksNewTab ? "_blank" : undefined}
      rel={
        window.sosseConfig?.linksNoReferrer ? "noopener noreferrer" : undefined
      }
      style={style}
    >
      {children}
    </Link>
  );
}
