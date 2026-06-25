import { ref } from 'vue';

export interface PopupConfig {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info' | 'success';
  hideCancel?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
}

export function useConfirmModal() {
  const popupState = ref({
    show: false,
    title: '',
    message: '',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    variant: 'danger' as 'danger' | 'warning' | 'info' | 'success',
    hideCancel: false,
    onConfirm: undefined as (() => void) | undefined,
    onCancel: undefined as (() => void) | undefined,
  });

  const triggerPopup = (config: Partial<PopupConfig>) => {
    popupState.value = {
      show: true,
      title: '',
      message: '',
      confirmText: 'Confirm',
      cancelText: 'Cancel',
      variant: 'danger',
      hideCancel: false,
      onConfirm: undefined,
      onCancel: undefined,
      ...config,
    };
  };

  const handlePopupConfirm = () => {
    popupState.value.show = false;
    if (popupState.value.onConfirm) popupState.value.onConfirm();
  };

  const handlePopupCancel = () => {
    popupState.value.show = false;
    if (popupState.value.onCancel) popupState.value.onCancel();
  };

  return {
    popupState,
    triggerPopup,
    handlePopupConfirm,
    handlePopupCancel,
  };
}
