import { Modal } from "@/lib/components/Modal";
import { Button } from "@/lib/components/ui/Button";

interface SiteChangeConfirmModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function SiteChangeConfirmModal({
  open,
  onClose,
  onConfirm,
}: SiteChangeConfirmModalProps) {
  return (
    <Modal open={open} onClose={onClose} title="Switch site?" maxWidth="max-w-sm">
      <div className="px-5 pb-5 pt-2">
        <p className="text-sm text-muted-foreground">
          Your current strategy will be cleared when you switch sites. Are you sure you
          want to continue?
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" onClick={onConfirm}>
            Switch site
          </Button>
        </div>
      </div>
    </Modal>
  );
}
