export {};

declare global {
  interface Window {
    sosseConfig?: {
      screenshotsUrl?: string;
      snapshotUrl: string;
      anonymousSearch: boolean;
      onlineSearchRedirect: boolean;
      maxPageSize: number;
      pageSize: number;
      csvExport: boolean;
      crawlStatusAutorefresh: number;
      browsableHome: boolean;
      linksNoReferrer: boolean;
      linksNewTab: boolean;
    };
  }
}
