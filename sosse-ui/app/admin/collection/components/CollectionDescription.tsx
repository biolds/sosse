"use client";

import { memo } from "react";
import {
  BranchesOutlined,
  CalendarOutlined,
  CameraOutlined,
  GlobalOutlined,
  Html5Outlined,
  RetweetOutlined,
} from "@ant-design/icons";
import type { Collection } from "@/app/types/collection";
import { humanDatetime, parseDurationToSeconds } from "@/app/utils/strings";

const title = (word: string) => word.charAt(0).toUpperCase() + word.slice(1);

const CollectionDescription = ({ collection }: { collection: Collection }) => {
  const browserLabel = (() => {
    if (collection.default_browse_mode === "detect") {
      return `${title(window.sosseConfig?.defaultBrowser || "chromium")} / Requests`;
    } else if (collection.default_browse_mode === "selenium") {
      return "Chromium";
    } else {
      return title(collection.default_browse_mode);
    }
  })();
  return (
    <>
      <span>
        <BranchesOutlined style={{ marginRight: 4 }} />
        {collection.unlimited_regex_pg && "Unlimited Recursion"}
        {collection.unlimited_regex_pg && collection.limited_regex_pg && "/"}
        {collection.limited_regex_pg && `Depth ${collection.recursion_depth}`}
        {!collection.limited_regex_pg &&
          !collection.unlimited_regex_pg &&
          "No Recursion"}
      </span>
      <span>
        <GlobalOutlined style={{ marginLeft: 12, marginRight: 4 }} />
        {browserLabel}
      </span>
      <span>
        <CalendarOutlined style={{ marginLeft: 12, marginRight: 4 }} />
        {collection.recrawl_freq === "none" && "Once"}
        {collection.recrawl_freq === "constant" &&
          humanDatetime(parseDurationToSeconds(collection.recrawl_dt_min))}
        {collection.recrawl_freq === "adaptive" &&
          `${humanDatetime(parseDurationToSeconds(collection.recrawl_dt_min))} ~ ${humanDatetime(
            parseDurationToSeconds(collection.recrawl_dt_max),
          )}`}
      </span>
      {collection.snapshot_html && (
        <span>
          <Html5Outlined style={{ marginLeft: 12, marginRight: 4 }} />
          HTML
        </span>
      )}
      {collection.take_screenshots && (
        <span>
          <CameraOutlined style={{ marginLeft: 12, marginRight: 4 }} />
          Screenshot
        </span>
      )}
      {collection.webhooks.length > 0 && (
        <span>
          <RetweetOutlined style={{ marginLeft: 12, marginRight: 4 }} />
          Webhook
          {collection.webhooks.length > 1 ? "s" : ""}
        </span>
      )}
    </>
  );
};

export default memo(CollectionDescription);
