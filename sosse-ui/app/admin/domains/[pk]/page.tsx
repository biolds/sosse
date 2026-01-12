"use client";

import { useParams } from "next/navigation";
import DomainForm from "../DomainForm";

export default function DomainFormPage() {
  const params = useParams();
  const pk = params.pk as string;
  const isNew = pk === "new";

  return <DomainForm domainId={isNew ? undefined : pk} isNew={isNew} />;
}
