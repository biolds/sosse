"use client";

import { useRef } from "react";
import { Button, Dropdown, Modal, Progress, App } from "antd";
import { DownOutlined } from "@ant-design/icons";
import type { MenuProps } from "antd";
import axios from "axios";

export interface ActionConfig {
  key: string;
  label: string;
  danger?: boolean;
  confirmTitle: (count: number) => string;
  confirmContent: (count: number) => string;
  successMessage: (count: number) => string;
  errorMessage: () => string;
  progressMessage: () => string;
}

interface ActionDropdownProps {
  actionItems: ActionConfig[];
  selectedRowKeys: React.Key[];
  totalCount: number;
  selectAll: boolean;
  apiEndpoint: string;
  searchValue: string;
  itemName?: string;
  onActionComplete?: () => void;
  actionProgress?: {
    visible: boolean;
    current: number;
    total: number;
    message: string;
  };
  onProgress?: (
    visible: boolean,
    current: number,
    total: number,
    message: string,
  ) => void;
  onCancelAction?: () => void;
}

export default function ActionDropdown({
  actionItems,
  selectedRowKeys,
  totalCount,
  selectAll,
  apiEndpoint,
  searchValue,
  itemName = "item",
  onActionComplete,
  actionProgress,
  onProgress,
  onCancelAction,
}: ActionDropdownProps) {
  const { modal, message } = App.useApp();
  const cancelActionRef = useRef(false);

  const handleActionSelected = async (actionKey: string) => {
    if (selectedRowKeys.length === 0 && !selectAll) {
      message.warning(`No ${itemName}s selected`);
      return;
    }

    const actionConfig = actionItems.find((item) => item?.key === actionKey) as
      | ActionConfig
      | undefined;
    if (!actionConfig) return;

    const count = selectAll ? totalCount : selectedRowKeys.length;

    const confirmModal = modal.confirm({
      title: actionConfig.confirmTitle(count),
      content: actionConfig.confirmContent(count),
      okText: actionConfig.label,
      okType: actionConfig.danger ? "danger" : "primary",
      onOk: async () => {
        confirmModal.destroy();
        if (selectAll) {
          await handleActionAllWithProgress(actionKey, actionConfig);
        } else {
          await handleActionBatch(
            actionKey,
            actionConfig,
            selectedRowKeys as number[],
          );
        }
      },
    });
  };

  const handleActionBatch = async (
    action: string,
    actionConfig: ActionConfig,
    ids: number[],
  ) => {
    try {
      await axios.post(`${apiEndpoint}/action/`, {
        action,
        ids,
      });
      message.success(actionConfig.successMessage(ids.length));
      onActionComplete?.();
    } catch (error) {
      message.error(actionConfig.errorMessage());
      console.error(`Error performing ${action} on ${itemName}s:`, error);
    }
  };

  const handleActionAllWithProgress = async (
    action: string,
    actionConfig: ActionConfig,
  ) => {
    cancelActionRef.current = false;
    onProgress?.(true, 0, totalCount, actionConfig.progressMessage());

    try {
      const batchSize = 100;
      let offset = 0;
      let processedCount = 0;

      while (offset < totalCount && !cancelActionRef.current) {
        const response = await axios.get<{ results: { id: number }[] }>(
          apiEndpoint,
          {
            params: {
              ...(searchValue ? { search: searchValue } : {}),
              ids_only: 1,
              offset: 0,
              limit: batchSize,
            },
          },
        );

        if (response.data.results.length === 0) break;

        const ids = response.data.results.map((item) => item.id);

        await axios.post(`${apiEndpoint}/action/`, {
          action,
          ids,
        });

        processedCount += ids.length;
        offset += batchSize;

        onProgress?.(
          true,
          processedCount,
          totalCount,
          actionConfig.progressMessage(),
        );
      }

      onProgress?.(false, 0, 0, "");

      if (cancelActionRef.current) {
        message.info(
          `Action cancelled. ${processedCount} ${itemName}(s) were processed.`,
        );
      } else {
        message.success(actionConfig.successMessage(processedCount));
      }

      onActionComplete?.();
    } catch (error) {
      onProgress?.(false, 0, 0, "");
      message.error(actionConfig.errorMessage());
      console.error(`Error performing ${action} on ${itemName}s:`, error);
    }
  };

  const handleCancelActionInternal = () => {
    cancelActionRef.current = true;
    onCancelAction?.();
  };

  const menuItems: MenuProps["items"] = actionItems.map((action) => ({
    key: action.key,
    label: action.label,
    danger: action.danger,
    onClick: () => handleActionSelected(action.key),
  }));

  const hasSelection = selectedRowKeys.length > 0 || selectAll;

  return (
    <>
      <Dropdown
        menu={{ items: menuItems }}
        trigger={["click"]}
        disabled={!hasSelection}
      >
        <Button disabled={!hasSelection}>
          Actions <DownOutlined />
        </Button>
      </Dropdown>

      {actionProgress && (
        <Modal
          title={`Processing ${itemName}s`}
          open={actionProgress.visible}
          footer={[
            <Button key="cancel" onClick={handleCancelActionInternal}>
              Cancel
            </Button>,
          ]}
          closable={false}
        >
          <Progress
            percent={Math.round(
              (actionProgress.current / actionProgress.total) * 100,
            )}
            status="active"
          />
          <p style={{ marginTop: "16px", textAlign: "center" }}>
            {actionProgress.message}
          </p>
        </Modal>
      )}
    </>
  );
}
