import { useRef, useEffect, useCallback } from "react";
import { X, Loader2 } from "lucide-react";

interface BaseDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  confirmLabel?: string;
  /** loading 状态下的确认按钮文本（如 "创建中..."、"转化中..."） */
  loadingLabel?: string;
  cancelLabel?: string;
  onConfirm?: () => void;
  onCancel?: () => void;
  loading?: boolean;
  confirmDisabled?: boolean;
}

export function BaseDialog({
  open,
  onOpenChange,
  title,
  children,
  footer,
  confirmLabel,
  loadingLabel,
  cancelLabel = "取消",
  onConfirm,
  onCancel,
  loading = false,
  confirmDisabled = false,
}: BaseDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  // 同步对话框开关
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  const handleClose = useCallback(() => {
    onOpenChange(false);
  }, [onOpenChange]);

  const handleCancel = useCallback(() => {
    if (onCancel) {
      onCancel();
    } else {
      handleClose();
    }
  }, [onCancel, handleClose]);

  if (!open) return null;

  // 判断是否需要渲染默认 footer
  const hasDefaultFooter = onConfirm || confirmLabel;

  return (
    <dialog
      ref={dialogRef}
      onClose={handleClose}
      className="rounded-xl p-0 bg-transparent backdrop:bg-black/40 max-w-md w-full max-sm:max-w-full max-sm:m-0 max-sm:mt-auto max-sm:rounded-b-none max-sm:h-[90vh] max-sm:rounded-t-xl"
    >
      <div className="bg-card rounded-xl p-6 shadow-lg flex flex-col max-sm:h-full max-sm:rounded-b-none">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button
            onClick={handleClose}
            className="text-muted-foreground hover:text-foreground transition-colors"
            disabled={loading}
            aria-label="关闭"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        {children}

        {/* Default Footer */}
        {hasDefaultFooter && (
          <div className="flex gap-3 mt-4 max-sm:mt-auto max-sm:pt-4">
            <button
              onClick={handleCancel}
              disabled={loading}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border border-border hover:bg-accent transition-colors"
            >
              {cancelLabel}
            </button>
            <button
              onClick={onConfirm}
              disabled={loading || confirmDisabled}
              className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {loadingLabel ?? (confirmLabel ? `${confirmLabel}...` : "处理中...")}
                </>
              ) : (
                confirmLabel ?? "确认"
              )}
            </button>
          </div>
        )}

        {/* Custom Footer */}
        {footer && !hasDefaultFooter && footer}
      </div>
    </dialog>
  );
}
