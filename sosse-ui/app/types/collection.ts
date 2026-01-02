export interface Collection {
  id: number;
  name: string;
  unlimited_regex: string;
  unlimited_regex_pg: string;
  limited_regex: string;
  limited_regex_pg: string;
  excluded_regex: string;
  mimetype_regex: string;
  recursion_depth: number;
  keep_params: boolean;
  hide_documents: boolean;
  default_browse_mode: "detect" | "requests" | "selenium" | "firefox";
  snapshot_html: boolean;
  snapshot_exclude_url_re: string;
  snapshot_exclude_mime_re: string;
  snapshot_exclude_element_re: string;

  thumbnail_mode: "none" | "preview" | "prevscreen" | "screenshot";
  take_screenshots: boolean;
  screenshot_format: "jpg" | "png";

  remove_nav_elements: "idx" | "scr" | "yes" | "no";
  script: string;
  store_extern_links: boolean;

  recrawl_condition: "change" | "manual" | "always";
  recrawl_freq: "none" | "constant" | "adaptive";
  recrawl_dt_min: number | null;
  recrawl_dt_max: number | null;
  hash_mode: "raw" | "no_numbers";

  auth_login_url_re: string | null;
  auth_form_selector: string | null;

  tags: number[];
  webhooks: number[];

  queue_to_any_collection: boolean;
  queue_to_collections: number[];
  documents_count: number;
}
