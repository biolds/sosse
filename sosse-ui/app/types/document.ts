// Copyright 2022-2025 Laurent Defert
//
//  This file is part of Sosse.
//
// Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
// General Public License as published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
// the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
// See the GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License along with Sosse.
// If not, see <https://www.gnu.org/licenses/>.

import type { Tag } from "./tag";

export interface FavIcon {
  id: number;
  missing: boolean;
}

export interface Document {
  id: number;
  url: string;
  collection: number;
  normalized_url: string;
  title: string;
  normalized_title: string;
  content: string;
  normalized_content: string;
  content_hash: string | null;
  image_name: string;
  lang_iso_639_1: string | null;
  vector_lang: string;
  mimetype: string | null;
  hidden: boolean;
  retries: number;
  favicon: FavIcon | null;
  robotstxt_rejected: boolean;
  has_html_snapshot: boolean;
  has_screenshot: boolean;
  has_text: boolean;
  redirect_url: string | null;
  too_many_redirects: boolean;
  screenshot_count: number;
  screenshot_format: "png" | "jpg";
  screenshot_size: string;
  has_thumbnail: boolean;
  crawl_first: string | null;
  crawl_last: string | null;
  crawl_next: string | null;
  crawl_dt: string | null;
  crawl_recurse: number;
  modified_date: string | null;
  manual_crawl: boolean;
  error: string;
  error_hash: string;
  show_on_homepage: boolean;
  worker_no: number | null;
  webhooks_result: Record<string, unknown>;
  metadata: Record<string, unknown>;
  mime_plugins_result: string;
  tags: string[];
  tag_list: Tag[];
  tags_str: string;
  preview: string | null;
  snapshot_url: string | null;
}
