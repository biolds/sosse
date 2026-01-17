import { Tooltip } from "antd";
import { humanDt } from "@/app/utils/strings";

interface HumanDateProps {
  date: Date | string | null | undefined;
  short?: boolean;
}

export default function HumanDate({ date, short = true }: HumanDateProps) {
  if (!date) {
    return <span>-</span>;
  }

  const dateObj = typeof date === "string" ? new Date(date) : date;
  const humanReadable = humanDt(date, short);
  const fullDate = dateObj.toLocaleString();

  return (
    <Tooltip title={fullDate}>
      <span>{humanReadable}</span>
    </Tooltip>
  );
}
