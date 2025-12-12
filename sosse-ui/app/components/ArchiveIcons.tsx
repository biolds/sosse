"use client";

import { useAppStore } from "../useAppStore";
import { LinkOutlined, AuditOutlined } from "@ant-design/icons";

export const ArchiveIcon = () => {
  return <AuditOutlined style={{ color: "#cc8709" }} />;
};

export const SourceIcon = () => {
  return <LinkOutlined style={{ color: "#00b7ff" }} />;
};

export const AnimatedLinkModeIcon = () => {
  const { linkMode } = useAppStore();
  return (
    <span className="icon-bounce" key={linkMode}>
      {linkMode === "source" ? <SourceIcon /> : <ArchiveIcon />}
    </span>
  );
};
