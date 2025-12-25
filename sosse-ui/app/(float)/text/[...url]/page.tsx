"use client";

import { useAppStore } from "@/app/hooks/useAppStore";

export default function TextPage() {
  const { sosseDocument } = useAppStore();
  return <div>{sosseDocument && sosseDocument.content}</div>;
}
