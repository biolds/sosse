"use client";

import React, { memo, useEffect, useState } from "react";
import { Modal, Form, Select, Input, Checkbox, Alert, Button } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import type { AdvancedFilter } from "@/app/hooks/useAppStore";

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

interface FilterModalProps {
  visible: boolean;
  onCancel: () => void;
  onSubmit: (filter: AdvancedFilter) => void;
  initialFilter?: AdvancedFilter;
  isEditing?: boolean;
}

const FilterModal = memo(
  ({
    visible,
    onCancel,
    onSubmit,
    initialFilter,
    isEditing = false,
  }: FilterModalProps) => {
    const [form] = Form.useForm();
    const [filterType, setFilterType] = useState<"inc" | "exc">("inc");

    useEffect(() => {
      if (visible) {
        if (initialFilter) {
          form.setFieldsValue(initialFilter);
        } else {
          form.setFieldsValue({
            type: "inc",
            field: "doc",
            operator: "contain",
            term: "",
            case_sensitive: false,
          });
        }
      }
    }, [visible, initialFilter, form]);

    const displayType = visible
      ? form.getFieldValue("type") || filterType
      : filterType;

    const handleSubmit = async () => {
      try {
        const values = await form.validateFields();

        if (values.operator === "regexp") {
          try {
            new RegExp(values.term);
          } catch {
            form.setFields([
              {
                name: "term",
                errors: ["Invalid regular expression syntax"],
              },
            ]);
            return;
          }
        }

        onSubmit({
          id: initialFilter?.id || `filter-${Date.now()}-${Math.random()}`,
          ...values,
        });
        form.resetFields();
      } catch (error) {
        console.error("Validation failed:", error);
      }
    };

    const handleCancel = () => {
      form.resetFields();
      onCancel();
    };

    const watchOperator = Form.useWatch("operator", form);

    return (
      <Modal
        title={isEditing ? "Edit Filter" : "Add Filter"}
        open={visible}
        onOk={handleSubmit}
        onCancel={handleCancel}
        okText={isEditing ? "Update Filter" : "Add Filter"}
        cancelText="Cancel"
        width={800}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: "20px" }}
          autoComplete="off"
        >
          <div
            style={{ display: "flex", gap: "16px", alignItems: "flex-start" }}
          >
            <Form.Item
              label="Filter Type"
              name="type"
              rules={[
                { required: true, message: "Please select a filter type" },
              ]}
              style={{ marginBottom: 0, flex: "0 0 140px" }}
            >
              <Button
                block
                type="default"
                onClick={() => {
                  const newType = displayType === "inc" ? "exc" : "inc";
                  setFilterType(newType);
                  form.setFieldsValue({ type: newType });
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                  backgroundColor:
                    displayType === "inc" ? "#e6f4ff" : "#fff7e6",
                  borderColor: displayType === "inc" ? "#1890ff" : "#fa8c16",
                  color: displayType === "inc" ? "#1890ff" : "#fa8c16",
                }}
                icon={
                  displayType === "inc" ? (
                    <CheckCircleOutlined />
                  ) : (
                    <CloseCircleOutlined />
                  )
                }
              >
                {displayType === "inc" ? "Include" : "Exclude"}
              </Button>
            </Form.Item>

            <Form.Item
              label="Field to search"
              name="field"
              rules={[{ required: true, message: "Please select a field" }]}
              style={{ marginBottom: 0, flex: "1" }}
            >
              <Select
                showSearch
                placeholder="Select a field"
                optionFilterProp="children"
              >
                {FILTER_FIELDS.map((field) => (
                  <Option key={field.value} value={field.value}>
                    {field.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              label="Operator"
              name="operator"
              rules={[{ required: true, message: "Please select an operator" }]}
              style={{ marginBottom: 0, flex: "0 0 150px" }}
            >
              <Select placeholder="Select an operator">
                <Option value="contain">Containing</Option>
                <Option value="equal">Equal to</Option>
                <Option value="regexp">Matching Regex</Option>
              </Select>
            </Form.Item>

            <Form.Item
              label="Value"
              name="term"
              rules={[
                { required: true, message: "Please enter a value" },
                { whitespace: true, message: "Value cannot be empty" },
              ]}
              style={{ marginBottom: 0, flex: "2" }}
            >
              <Input
                placeholder="Enter the value to filter"
                allowClear
                autoComplete="off"
                onPressEnter={handleSubmit}
              />
            </Form.Item>
          </div>

          {watchOperator === "regexp" && (
            <Alert
              message="Regular Expression"
              description="Use standard regex syntax. Example: ^https?://.*\.pdf$ to match PDF URLs"
              type="info"
              showIcon
              style={{ marginTop: "16px", marginBottom: "16px" }}
            />
          )}

          <Form.Item
            name="case_sensitive"
            valuePropName="checked"
            style={{ marginTop: "16px" }}
          >
            <Checkbox>Case sensitive</Checkbox>
          </Form.Item>
        </Form>
      </Modal>
    );
  },
);

FilterModal.displayName = "FilterModal";

export default FilterModal;
