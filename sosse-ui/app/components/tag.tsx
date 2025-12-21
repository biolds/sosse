import { Tag as TagComponent } from "antd";
import type { Tag } from "@/app/types/tag";

const Tag = ({ tag }: { tag: Tag }) => {
  return (
    <TagComponent
      variant="outlined"
      style={{
        color: tag.color,
        borderColor: tag.color,
      }}
    >
      {/*<TagComponent variant="outlined" color={tag.color || "default"}>*/}
      {tag.name}
    </TagComponent>
  );
};
export default Tag;
