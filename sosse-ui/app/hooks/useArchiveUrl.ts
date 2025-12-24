import { usePathname, useSearchParams } from "next/navigation";

export function useArchiveUrl() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const pathUrl = decodeURIComponent(pathname.replace(/\/[^/]+\//, ""));
  let url =
    pathUrl.startsWith("http:") || pathUrl.startsWith("https:")
      ? `${pathUrl.replace(/(http:|https:)/, "$1/")}`
      : pathUrl;

  const queryString = searchParams.toString();
  if (queryString) {
    url += `?${queryString}`;
  }

  return url;
}
