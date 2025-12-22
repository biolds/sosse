"use client";

import React from "react";
import { Tabs } from "antd";
import {
  HomeOutlined,
  SearchOutlined,
  FileImageOutlined,
  CustomerServiceOutlined,
  VideoCameraOutlined,
} from "@ant-design/icons";
import type { SearchTab } from "@/app/hooks/useAppStore";

interface SearchTabsProps {
  activeTab: SearchTab;
  onTabChange: (tab: SearchTab) => void;
  hasSearchQuery: boolean;
}

const SearchTabs: React.FC<SearchTabsProps> = ({
  activeTab,
  onTabChange,
  hasSearchQuery,
}) => {
  const items = [
    {
      key: "home",
      label: (
        <span>
          <HomeOutlined /> Home
        </span>
      ),
      disabled: false,
    },
    {
      key: "search",
      label: (
        <span>
          <SearchOutlined /> Search
        </span>
      ),
      disabled: !hasSearchQuery,
    },
    {
      key: "images",
      label: (
        <span>
          <FileImageOutlined /> Images
        </span>
      ),
      disabled: !hasSearchQuery,
    },
    {
      key: "audio",
      label: (
        <span>
          <CustomerServiceOutlined /> Audio
        </span>
      ),
      disabled: !hasSearchQuery,
    },
    {
      key: "video",
      label: (
        <span>
          <VideoCameraOutlined /> Video
        </span>
      ),
      disabled: !hasSearchQuery,
    },
  ];

  return (
    <Tabs
      activeKey={activeTab}
      items={items}
      onChange={(key) => onTabChange(key as SearchTab)}
      style={{ marginTop: "20px" }}
    />
  );
};

export default SearchTabs;
