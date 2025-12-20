"use client";

import React, { memo } from "react";
import { Tag, Space } from "antd";
import {
  EditOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import type { AdvancedFilter } from "@/app/hooks/useAppStore";

const FIELD_LABELS: Record<string, string> = {
  doc: "Document",
  content: "Content",
  title: "Title",
  url: "URL",
  mimetype: "Mimetype",
  lto_url: "Links to url",
  lto_txt: "Links to text",
  lby_url: "Linked by url",
  lby_txt: "Linked by text",
  tag: "Tag",
};

const OPERATOR_SYMBOLS: Record<string, string> = {
  contain: "has",
  equal: "=",
  regexp: "~",
};

interface FilterBadgeProps {
  filter: AdvancedFilter;
  onEdit: () => void;
  onRemove: () => void;
}

const FilterBadge = memo(({ filter, onEdit, onRemove }: FilterBadgeProps) => {
  const fieldLabel = FIELD_LABELS[filter.field] || filter.field;
  const operatorSymbol = OPERATOR_SYMBOLS[filter.operator] || filter.operator;
  const isInclude = filter.type === "inc";

  const displayText = `${fieldLabel} ${operatorSymbol} ${filter.term}`;
  const prefixIcon = isInclude ? (
    <CheckCircleOutlined />
  ) : (
    <CloseCircleOutlined />
  );

  return (
    <Tag
      className={`filter-badge filter-badge-${filter.type}`}
      color={isInclude ? "blue" : "orange"}
      closable
      onClose={(e) => {
        e.preventDefault();
        onRemove();
      }}
      style={{
        fontSize: "13px",
        padding: "4px 12px",
        margin: "4px",
        display: "inline-flex",
        alignItems: "center",
        cursor: "pointer",
        borderRadius: "16px",
        maxWidth: "100%",
        transition: "all 0.2s ease",
      }}
      onClick={onEdit}
    >
      <Space size={4} style={{ maxWidth: "100%" }}>
        {prefixIcon}
        <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
          {displayText}
        </span>
        {filter.case_sensitive && (
          <span
            title="Case sensitive"
            style={{
              fontSize: "11px",
              opacity: 0.8,
              fontWeight: "bold",
            }}
          >
            Aa
          </span>
        )}
        <EditOutlined
          style={{
            fontSize: "12px",
            opacity: 0.7,
            marginLeft: "4px",
          }}
        />
      </Space>
    </Tag>
  );
});

FilterBadge.displayName = "FilterBadge";

export default FilterBadge;
