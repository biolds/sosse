import { useState } from "react";
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
} from "antd";
import {
  PlusOutlined,
  MinusOutlined,
  DownOutlined,
  UpOutlined,
} from "@ant-design/icons";

const { Option } = Select;

export interface AdvancedFilter {
  type: "inc" | "exc";
  field: string;
  operator: "contain" | "equal" | "regexp";
  term: string;
  case_sensitive: boolean;
}

export interface AdvancedSearchParams {
  lang?: string;
  collection?: number;
  include_hidden: boolean;
  sort: string;
  adv_params: AdvancedFilter[];
}

interface AdvancedSearchProps {
  params: AdvancedSearchParams;
  onChange: (params: AdvancedSearchParams) => void;
  collections?: Array<{ id: number; name: string }>;
}

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

export default function AdvancedSearch({
  params,
  onChange,
  collections = [],
}: AdvancedSearchProps) {
  const [expanded, setExpanded] = useState(false);

  const addFilter = () => {
    const newFilter: AdvancedFilter = {
      type: "inc",
      field: "doc",
      operator: "contain",
      term: "",
      case_sensitive: false,
    };
    onChange({
      ...params,
      adv_params: [...params.adv_params, newFilter],
    });
  };

  const removeFilter = (index: number) => {
    const newFilters = params.adv_params.filter((_, i) => i !== index);
    onChange({
      ...params,
      adv_params: newFilters,
    });
  };

  const updateFilter = (
    index: number,
    field: keyof AdvancedFilter,
    value: string | boolean,
  ) => {
    const newFilters = [...params.adv_params];
    newFilters[index] = { ...newFilters[index], [field]: value };
    onChange({
      ...params,
      adv_params: newFilters,
    });
  };

  return (
    <div>
      <div style={{ textAlign: "center", marginTop: "10px" }}>
        <Button
          type="link"
          size="small"
          onClick={() => setExpanded(!expanded)}
          icon={expanded ? <UpOutlined /> : <DownOutlined />}
        >
          {expanded ? "Hide advanced search" : "Show advanced search"}
        </Button>
      </div>

      {expanded && (
        <div
          style={{
            marginTop: "20px",
            padding: "20px",
            border: "1px solid #d9d9d9",
            borderRadius: "8px",
            backgroundColor: "#fafafa",
          }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="Language" style={{ marginBottom: 0 }}>
                <Select
                  value={params.lang || ""}
                  onChange={(value) =>
                    onChange({ ...params, lang: value || undefined })
                  }
                  style={{ width: "100%" }}
                  placement="bottomLeft"
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
                  value={params.collection}
                  onChange={(value) =>
                    onChange({ ...params, collection: value })
                  }
                  style={{ width: "100%" }}
                  allowClear
                  placeholder="All collections"
                  placement="bottomLeft"
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
                  value={params.sort}
                  onChange={(value) => onChange({ ...params, sort: value })}
                  style={{ width: "100%" }}
                  placement="bottomLeft"
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
                  checked={params.include_hidden}
                  onChange={(e) =>
                    onChange({ ...params, include_hidden: e.target.checked })
                  }
                >
                  Include hidden documents
                </Checkbox>
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">Custom Filters</Divider>

          <Space direction="vertical" style={{ width: "100%" }}>
            {params.adv_params.map((filter, index) => (
              <Row key={index} gutter={8} align="middle" wrap={false}>
                <Col flex="none">
                  <Button
                    size="small"
                    icon={<MinusOutlined />}
                    onClick={() => removeFilter(index)}
                    danger
                  />
                </Col>
                <Col flex="100px">
                  <Select
                    value={filter.type}
                    onChange={(value) => updateFilter(index, "type", value)}
                    style={{ width: "100%" }}
                    size="small"
                    placement="bottomLeft"
                  >
                    <Option value="inc">Keep</Option>
                    <Option value="exc">Exclude</Option>
                  </Select>
                </Col>
                <Col flex="150px">
                  <Select
                    value={filter.field}
                    onChange={(value) => updateFilter(index, "field", value)}
                    style={{ width: "100%" }}
                    size="small"
                    placement="bottomLeft"
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
                    onChange={(value) => updateFilter(index, "operator", value)}
                    style={{ width: "100%" }}
                    size="small"
                    placement="bottomLeft"
                  >
                    <Option value="contain">Containing</Option>
                    <Option value="equal">Equal to</Option>
                    <Option value="regexp">Matching Regex</Option>
                  </Select>
                </Col>
                <Col flex="auto">
                  <Input
                    value={filter.term}
                    onChange={(e) =>
                      updateFilter(index, "term", e.target.value)
                    }
                    placeholder="Value"
                    size="small"
                  />
                </Col>
                <Col flex="none">
                  <Checkbox
                    checked={filter.case_sensitive}
                    onChange={(e) =>
                      updateFilter(index, "case_sensitive", e.target.checked)
                    }
                  >
                    Case sensitive
                  </Checkbox>
                </Col>
              </Row>
            ))}

            <Button
              type="dashed"
              onClick={addFilter}
              icon={<PlusOutlined />}
              style={{ width: "100%" }}
            >
              Add filter
            </Button>
          </Space>
        </div>
      )}
    </div>
  );
}
