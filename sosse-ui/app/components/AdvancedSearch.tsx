"use client";

import React, {
  memo,
  useCallback,
  useState,
  forwardRef,
  useImperativeHandle,
} from "react";
import { Button, theme } from "antd";
import { PlusOutlined, DownOutlined, SettingOutlined } from "@ant-design/icons";
import { useAppStore } from "@/app/hooks/useAppStore";
import type { AdvancedFilter, SearchFilters } from "@/app/types/search";
import FilterBadge from "./FilterBadge";
import FilterModal from "./FilterModal";
import MoreOptionsPanel from "./MoreOptionsPanel";
import "./AdvancedSearch.css";

export interface AdvancedSearchRef {
  validateFilters: () => boolean;
}

const AdvancedSearch = forwardRef<
  AdvancedSearchRef,
  {
    filters: SearchFilters;
    setFilters: (filters: SearchFilters) => void;
  }
>(({ filters, setFilters }, ref) => {
  const { collections } = useAppStore();
  const { token } = theme.useToken();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingFilterIndex, setEditingFilterIndex] = useState<number | null>(
    null,
  );
  const [moreOptionsExpanded, setMoreOptionsExpanded] = useState(false);

  const openAddModal = useCallback(() => {
    setEditingFilterIndex(null);
    setModalVisible(true);
  }, []);

  const openEditModal = useCallback((index: number) => {
    setEditingFilterIndex(index);
    setModalVisible(true);
  }, []);

  const handleModalSubmit = useCallback(
    (filter: AdvancedFilter) => {
      if (editingFilterIndex !== null) {
        setFilters({
          ...filters,
          adv_params: filters.adv_params.map((f, i) =>
            i === editingFilterIndex ? filter : f,
          ),
        });
      } else {
        setFilters({
          ...filters,
          adv_params: [...filters.adv_params, filter],
        });
      }
      setModalVisible(false);
      setEditingFilterIndex(null);
    },
    [filters, setFilters, editingFilterIndex],
  );

  const handleDeleteFilter = useCallback(
    (index: number) => {
      setFilters({
        ...filters,
        adv_params: filters.adv_params.filter((_, i) => i !== index),
      });
    },
    [filters, setFilters],
  );

  const validateFilters = useCallback(() => {
    const hasEmptyFilters = filters.adv_params.some(
      (filter) => !filter.term || filter.term.trim() === "",
    );
    return !hasEmptyFilters;
  }, [filters.adv_params]);

  useImperativeHandle(ref, () => ({
    validateFilters,
  }));

  return (
    <div style={{ marginTop: "16px" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "8px",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        {filters.adv_params.length > 0 && (
          <>
            <span
              style={{
                fontSize: "13px",
                fontWeight: 500,
                color: token.colorTextSecondary,
                marginRight: "4px",
              }}
            >
              Active Filters:
            </span>
            {filters.adv_params.map((filter, index) => (
              <FilterBadge
                key={filter.id}
                filter={filter}
                onEdit={() => openEditModal(index)}
                onRemove={() => handleDeleteFilter(index)}
              />
            ))}
            <Button
              type="text"
              size="small"
              danger
              onClick={() => setFilters({ ...filters, adv_params: [] })}
              style={{
                fontSize: "12px",
                height: "24px",
                padding: "0 8px",
                opacity: 0.6,
              }}
            >
              Clear all
            </Button>
          </>
        )}
        <Button
          type="dashed"
          size="small"
          icon={<PlusOutlined />}
          onClick={openAddModal}
          style={{
            borderRadius: "16px",
            height: "28px",
            fontSize: "13px",
          }}
        >
          Add Filter
        </Button>
        <Button
          type="text"
          size="small"
          icon={<SettingOutlined />}
          onClick={() => setMoreOptionsExpanded(!moreOptionsExpanded)}
          style={{
            borderRadius: "16px",
            height: "28px",
            fontSize: "13px",
          }}
        >
          More Options
          <DownOutlined
            style={{
              marginLeft: "4px",
              fontSize: "10px",
              transition: "transform 0.3s ease",
              display: "inline-block",
              transform: moreOptionsExpanded
                ? "rotate(180deg)"
                : "rotate(0deg)",
            }}
          />
        </Button>
      </div>

      <div
        style={{
          maxHeight: moreOptionsExpanded ? "500px" : "0",
          opacity: moreOptionsExpanded ? 1 : 0,
          overflow: "hidden",
          transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          marginBottom: moreOptionsExpanded ? "16px" : "0",
        }}
      >
        <MoreOptionsPanel
          filters={filters}
          setFilters={setFilters}
          collections={collections}
        />
      </div>

      <FilterModal
        visible={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingFilterIndex(null);
        }}
        onSubmit={handleModalSubmit}
        initialFilter={
          editingFilterIndex !== null
            ? filters.adv_params[editingFilterIndex]
            : undefined
        }
        isEditing={editingFilterIndex !== null}
      />
    </div>
  );
});

AdvancedSearch.displayName = "AdvancedSearch";

export default memo(AdvancedSearch);
