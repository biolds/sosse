export interface AdvancedFilter {
  id?: string;
  type: "inc" | "exc";
  field: string;
  operator: "contain" | "equal" | "regexp";
  term: string;
  case_sensitive: boolean;
}

export interface SearchFilters {
  lang: string;
  collection?: number;
  include_hidden: boolean;
  sort: string;
  adv_params: AdvancedFilter[];
}
