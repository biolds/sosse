"use client";

import { useParams } from "next/navigation";
import CollectionForm from "../CollectionForm";

export default function CollectionFormPage() {
  const params = useParams();
  const pk = params.pk as string;
  const isNew = pk === "new";

  return <CollectionForm collectionId={isNew ? undefined : pk} isNew={isNew} />;
}
