"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import archiveLink from "@/app/utils/archiveLink";
import { useAppStore } from "@/app/hooks/useAppStore";
import { useFloat } from "../../components/FloatContext";

export default function ArchivePage() {
  const sosseDocument = useAppStore((state) => state.sosseDocument);
  const router = useRouter();
  const { setLoading } = useFloat();

  useEffect(() => {
    setLoading(true);
  }, [setLoading]);

  const iframeLoaded = () => {
    setLoading(false);
    const iframe = document.getElementsByTagName("iframe");
    const links = iframe[0].contentWindow.document.getElementsByTagName("a");
    for (let i = 0; i < links.length; i++) {
      const link = links[i];
      const href = link.getAttribute("href") || "";
      link.href = "/html/" + archiveLink(href.replace("/html/", ""));
      link.onclick = function () {
        router.push(link.href);
      };
    }
    const iframes =
      iframe[0].contentWindow.document.getElementsByTagName("iframe");
    for (let i = 0; i < iframes.length; i++) {
      const innerIframe = iframes[i];
      const src = innerIframe.getAttribute("src") || "";
      innerIframe.src = "/html/" + archiveLink(src.replace("/html/", ""));
    }
  };

  if (!sosseDocument) {
    return null;
  }

  return (
    <iframe
      src={sosseDocument.snapshot_url}
      sandbox="allow-top-navigation allow-same-origin"
      onLoad={iframeLoaded}
      style={{ width: "100%", height: "100%", border: "none" }}
    />
  );
}
