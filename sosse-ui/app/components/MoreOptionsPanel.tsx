"use client";

import React, { memo } from "react";
import { Card, Form, Row, Col, Select, Checkbox, theme } from "antd";
import { SettingOutlined } from "@ant-design/icons";
import type { SearchFilters } from "@/app/hooks/useAppStore";

const { Option } = Select;

const SORT_OPTIONS = [
  { value: "-rank", label: "Most relevant first" },
  { value: "rank", label: "Most relevant last" },
  { value: "modified_date", label: "Last modified ascending" },
  { value: "-modified_date", label: "Last modified descending" },
  { value: "crawl_first", label: "First crawled ascending" },
  { value: "-crawl_first", label: "First crawled descending" },
  { value: "crawl_last", label: "Last crawled ascending" },
  { value: "-crawl_last", label: "Last crawled descending" },
  { value: "title", label: "Title ascending" },
  { value: "-title", label: "Title descending" },
  { value: "url", label: "URL ascending" },
  { value: "-url", label: "URL descending" },
];

const LANGUAGES = [
  { value: "", label: "Any" },
  { value: "en", label: "🇬🇧 English" },
  { value: "fr", label: "🇫🇷 French" },
  { value: "es", label: "🇪🇸 Spanish" },
  { value: "de", label: "🇩🇪 German" },
  { value: "it", label: "🇮🇹 Italian" },
  { value: "pt", label: "🇵🇹 Portuguese" },
  { value: "nl", label: "🇳🇱 Dutch" },
  { value: "pl", label: "🇵🇱 Polish" },
  { value: "ru", label: "🇷🇺 Russian" },
  { value: "ja", label: "🇯🇵 Japanese" },
  { value: "zh", label: "🇨🇳 Chinese" },
  { value: "ar", label: "🇸🇦 Arabic" },
];

interface MoreOptionsPanelProps {
  filters: SearchFilters;
  setFilters: (filters: SearchFilters) => void;
  collections: Array<{ id: number; name: string }>;
}

const MoreOptionsPanel = memo(
  ({ filters, setFilters, collections }: MoreOptionsPanelProps) => {
    const { token } = theme.useToken();

    return (
      <Card
        style={{
          borderRadius: "8px",
          border: `1px solid ${token.colorBorder}`,
          background: token.colorBgContainer,
        }}
        styles={{ body: { padding: "16px" } }}
        title={
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <SettingOutlined style={{ color: token.colorPrimary }} />
            <span style={{ fontWeight: 500 }}>More Options</span>
          </div>
        }
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={8}>
            <Form.Item label="Language" style={{ marginBottom: 0 }}>
              <Select
                value={filters.lang || ""}
                onChange={(value) =>
                  setFilters({
                    ...filters,
                    lang: value || undefined,
                  })
                }
                style={{ width: "100%" }}
              >
                {LANGUAGES.map((lang) => (
                  <Option key={lang.value} value={lang.value}>
                    {lang.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8}>
            <Form.Item label="Collection" style={{ marginBottom: 0 }}>
              <Select
                value={filters.collection}
                onChange={(value) =>
                  setFilters({ ...filters, collection: value })
                }
                style={{ width: "100%" }}
                allowClear
                placeholder="All collections"
              >
                {collections.map((col) => (
                  <Option key={col.id} value={col.id}>
                    {col.name}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24} sm={12} md={8}>
            <Form.Item label="Sort" style={{ marginBottom: 0 }}>
              <Select
                value={filters.sort}
                onChange={(value) => setFilters({ ...filters, sort: value })}
                style={{ width: "100%" }}
              >
                {SORT_OPTIONS.map((opt) => (
                  <Option key={opt.value} value={opt.value}>
                    {opt.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24}>
            <Checkbox
              checked={filters.include_hidden}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  include_hidden: e.target.checked,
                })
              }
            >
              Include hidden documents
            </Checkbox>
          </Col>

          <Col xs={24} sm={12}>
            <Form.Item label="Robots.txt rejected" style={{ marginBottom: 0 }}>
              <Select
                value={filters.robotstxt_rejected || "exclude"}
                onChange={(value) =>
                  setFilters({
                    ...filters,
                    robotstxt_rejected: value as "include" | "exclude" | "only",
                  })
                }
                style={{ width: "100%" }}
              >
                <Option value="include">Include all</Option>
                <Option value="only">Only rejected</Option>
                <Option value="exclude">Exclude rejected</Option>
              </Select>
            </Form.Item>
          </Col>

          <Col xs={24} sm={12}>
            <Form.Item
              label="Documents with errors"
              style={{ marginBottom: 0 }}
            >
              <Select
                value={filters.has_error || "include"}
                onChange={(value) =>
                  setFilters({
                    ...filters,
                    has_error: value as "include" | "exclude" | "only",
                  })
                }
                style={{ width: "100%" }}
              >
                <Option value="include">Include all</Option>
                <Option value="only">Only with errors</Option>
                <Option value="exclude">Exclude with errors</Option>
              </Select>
            </Form.Item>
          </Col>
        </Row>
      </Card>
    );
  },
);

MoreOptionsPanel.displayName = "MoreOptionsPanel";

export default MoreOptionsPanel;
