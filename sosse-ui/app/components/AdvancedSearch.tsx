"use client";

import { memo, useCallback } from "react";
import {
  Button,
  Select,
  Input,
  Checkbox,
  Space,
  Divider,
  Form,
  Row,
  Col,
  Card,
} from "antd";
import {
  PlusOutlined,
  MinusOutlined,
  DownOutlined,
  FilterOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
} from "@ant-design/icons";
import {
  useAppStore,
  type AdvancedFilter,
  type SearchFilters,
} from "../useAppStore";

const { Option } = Select;

const FILTER_FIELDS = [
  { value: "doc", label: "Document" },
  { value: "content", label: "Content" },
  { value: "title", label: "Title" },
  { value: "url", label: "URL" },
  { value: "mimetype", label: "Mimetype" },
  { value: "lto_url", label: "Links to url" },
  { value: "lto_txt", label: "Links to text" },
  { value: "lby_url", label: "Linked by url" },
  { value: "lby_txt", label: "Linked by text" },
  { value: "tag", label: "Tag" },
];

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

const FilterRow = memo(
  ({
    filter,
    index,
    onRemove,
    onUpdate,
  }: {
    filter: AdvancedFilter;
    index: number;
    onRemove: (index: number) => void;
    onUpdate: (
      index: number,
      field: keyof AdvancedFilter,
      value: string | boolean,
    ) => void;
  }) => {
    return (
      <div
        style={{
          padding: "12px",
          backgroundColor: "#fff",
          borderRadius: "8px",
          border: "1px solid #e8e8e8",
          boxShadow: "0 1px 2px rgba(0, 0, 0, 0.04)",
        }}
      >
        <Row gutter={8} align="middle" wrap>
          <Col flex="none">
            <Button
              size="small"
              icon={<MinusOutlined />}
              onClick={() => onRemove(index)}
              danger
              shape="circle"
              style={{ boxShadow: "0 1px 2px rgba(0, 0, 0, 0.1)" }}
            />
          </Col>
          <Col flex="110px">
            <Button
              size="small"
              onClick={() =>
                onUpdate(index, "type", filter.type === "inc" ? "exc" : "inc")
              }
              icon={
                filter.type === "inc" ? (
                  <CheckCircleOutlined />
                ) : (
                  <CloseCircleOutlined />
                )
              }
              type={filter.type === "inc" ? "primary" : "default"}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {filter.type === "inc" ? "Keep" : "Exclude"}
            </Button>
          </Col>
          <Col flex="150px">
            <Select
              value={filter.field}
              onChange={(value) => onUpdate(index, "field", value)}
              style={{ width: "100%" }}
              size="small"
              variant="filled"
            >
              {FILTER_FIELDS.map((field) => (
                <Option key={field.value} value={field.value}>
                  {field.label}
                </Option>
              ))}
            </Select>
          </Col>
          <Col flex="130px">
            <Select
              value={filter.operator}
              onChange={(value) => onUpdate(index, "operator", value)}
              style={{ width: "100%" }}
              size="small"
              variant="filled"
            >
              <Option value="contain">Containing</Option>
              <Option value="equal">Equal to</Option>
              <Option value="regexp">Matching Regex</Option>
            </Select>
          </Col>
          <Col flex="auto">
            <Input
              value={filter.term}
              onChange={(e) => onUpdate(index, "term", e.target.value)}
              placeholder="Value"
              size="small"
              variant="filled"
            />
          </Col>
          <Col flex="none">
            <Checkbox
              checked={filter.case_sensitive}
              onChange={(e) =>
                onUpdate(index, "case_sensitive", e.target.checked)
              }
            >
              Case sensitive
            </Checkbox>
          </Col>
        </Row>
      </div>
    );
  },
);

FilterRow.displayName = "FilterRow";

const AdvancedSearch = ({
  expanded,
  setExpanded,
  draftFilters,
  setDraftFilters,
}: {
  expanded: boolean;
  setExpanded: (expanded: boolean) => void;
  draftFilters: SearchFilters;
  setDraftFilters: (filters: SearchFilters) => void;
}) => {
  const { collections } = useAppStore();

  const addFilter = useCallback(() => {
    setDraftFilters({
      ...draftFilters,
      adv_params: [
        ...draftFilters.adv_params,
        {
          id: `filter-${Date.now()}-${Math.random()}`,
          type: "inc",
          field: "doc",
          operator: "contain",
          term: "",
          case_sensitive: false,
        },
      ],
    });
  }, [draftFilters, setDraftFilters]);

  const removeFilter = useCallback(
    (index: number) => {
      setDraftFilters({
        ...draftFilters,
        adv_params: draftFilters.adv_params.filter((_, i) => i !== index),
      });
    },
    [draftFilters, setDraftFilters],
  );

  const updateFilter = useCallback(
    (index: number, field: keyof AdvancedFilter, value: string | boolean) => {
      setDraftFilters({
        ...draftFilters,
        adv_params: draftFilters.adv_params.map((filter, i) =>
          i === index ? { ...filter, [field]: value } : filter,
        ),
      });
    },
    [draftFilters, setDraftFilters],
  );

  return (
    <div style={{ marginTop: "16px" }}>
      <div style={{ display: "flex", justifyContent: "center" }}>
        <Button
          type={expanded ? "primary" : "default"}
          ghost={expanded}
          size="middle"
          onClick={() => setExpanded(!expanded)}
          icon={<FilterOutlined />}
          style={{
            borderRadius: "20px",
            paddingLeft: "20px",
            paddingRight: "20px",
            boxShadow: expanded
              ? "0 2px 8px rgba(22, 119, 255, 0.2)"
              : "0 2px 4px rgba(0, 0, 0, 0.1)",
            transition: "all 0.3s ease",
          }}
        >
          Filters & Options
          <DownOutlined
            style={{
              marginLeft: "8px",
              fontSize: "12px",
              transition: "transform 0.3s ease",
              display: "inline-block",
              transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
            }}
          />
        </Button>
      </div>

      <div
        style={{
          maxHeight: expanded ? "2000px" : "0",
          opacity: expanded ? 1 : 0,
          overflow: "hidden",
          transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
          transform: expanded ? "translateY(0)" : "translateY(-10px)",
        }}
      >
        <Card
          style={{
            marginTop: "20px",
            borderRadius: "12px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.08)",
            border: "1px solid #e8e8e8",
            background: "linear-gradient(to bottom, #ffffff, #fafafa)",
          }}
          bodyStyle={{ padding: "24px" }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Language" style={{ marginBottom: 0 }}>
                <Select
                  value={draftFilters.lang || ""}
                  onChange={(value) =>
                    setDraftFilters({
                      ...draftFilters,
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

            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Collection" style={{ marginBottom: 0 }}>
                <Select
                  value={draftFilters.collection}
                  onChange={(value) =>
                    setDraftFilters({ ...draftFilters, collection: value })
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

            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Sort" style={{ marginBottom: 0 }}>
                <Select
                  value={draftFilters.sort}
                  onChange={(value) =>
                    setDraftFilters({ ...draftFilters, sort: value })
                  }
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

            <Col xs={24} sm={12} md={6}>
              <Form.Item label=" " style={{ marginBottom: 0 }}>
                <Checkbox
                  checked={draftFilters.include_hidden}
                  onChange={(e) =>
                    setDraftFilters({
                      ...draftFilters,
                      include_hidden: e.target.checked,
                    })
                  }
                >
                  Include hidden documents
                </Checkbox>
              </Form.Item>
            </Col>
          </Row>

          <Divider
            orientation="left"
            style={{ marginTop: "24px", marginBottom: "20px" }}
          >
            <Space>
              <FilterOutlined style={{ color: "#1677ff" }} />
              <span style={{ fontWeight: 500 }}>Custom Filters</span>
            </Space>
          </Divider>

          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            {draftFilters.adv_params.map((filter, index) => (
              <FilterRow
                key={filter.id}
                filter={filter}
                index={index}
                onRemove={removeFilter}
                onUpdate={updateFilter}
              />
            ))}

            <Button
              type="dashed"
              onClick={addFilter}
              icon={<PlusOutlined />}
              style={{
                width: "100%",
                borderRadius: "8px",
                height: "40px",
                borderStyle: "dashed",
                borderWidth: "2px",
              }}
            >
              Add filter
            </Button>
          </Space>
        </Card>
      </div>
    </div>
  );
};

export default memo(AdvancedSearch);
