import type { AdvancedFilter } from "@/app/hooks/useAppStore";
import type { SearchTab } from "../components/SearchTabs";

export const getMimetypeFilter = (tab: SearchTab): AdvancedFilter | null => {
  switch (tab) {
    case "images":
      return {
        id: `mimetype-filter-${Date.now()}`,
        type: "inc",
        field: "mimetype",
        operator: "regexp",
        term: "image/.*",
        case_sensitive: false,
      };
    case "audio":
      return {
        id: `mimetype-filter-${Date.now()}`,
        type: "inc",
        field: "mimetype",
        operator: "regexp",
        term: "audio/.*",
        case_sensitive: false,
      };
    case "video":
      return {
        id: `mimetype-filter-${Date.now()}`,
        type: "inc",
        field: "mimetype",
        operator: "regexp",
        term: "video/.*",
        case_sensitive: false,
      };
    default:
      return null;
  }
};

export const getTabFilters = (
  tab: SearchTab,
  baseFilters: AdvancedFilter[],
): AdvancedFilter[] => {
  const mimetypeFilter = getMimetypeFilter(tab);
  if (mimetypeFilter) {
    return [...baseFilters, mimetypeFilter];
  }
  return baseFilters;
};

export const getActiveTab = (
  hasSearchQuery: boolean,
  requestedTab?: SearchTab,
): SearchTab => {
  if (!hasSearchQuery) {
    return "home";
  }
  if (requestedTab && requestedTab !== "home") {
    return requestedTab;
  }
  return "search";
};
