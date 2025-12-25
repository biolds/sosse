import { useEffect, useState } from "react";
import axios from "axios";
import { useAppStore } from "./useAppStore";
import { useArchiveUrl } from "./useArchiveUrl";
import type { Link } from "./useAppStore";

export function useDocumentLinks() {
  const url = useArchiveUrl();
  const documentLinks = useAppStore((state) => state.documentLinks);
  const setDocumentLinks = useAppStore((state) => state.setDocumentLinks);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLinks = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get<Link[]>(`/api/link/${url}`);
        setDocumentLinks(response.data);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to load links";
        setError(errorMessage);
        console.error("Failed to load links:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchLinks();
  }, [url, setDocumentLinks]);

  return { documentLinks, loading, error };
}
