import {
  FileText,
  History,
  MapPinned,
  MessageSquare,
  PawPrint,
  ShieldCheck,
  X,
} from "lucide-react";
import { Dialog, Modal, ModalOverlay } from "react-aria-components";

interface GuestModeModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

const guestLimitations = [
  {
    icon: FileText,
    text: "Puedes subir un hemograma, revisar valores extraídos y ver el análisis ML de ese hemograma.",
  },
  { icon: ShieldCheck, text: "No se guardarán datos." },
  { icon: PawPrint, text: "No tendrás mascotas registradas." },
  { icon: History, text: "No tendrás historial personalizado." },
  { icon: MapPinned, text: "No tendrás acceso al mapa poblacional." },
  { icon: MessageSquare, text: "No tendrás acceso al Chat LLM." },
];

export function GuestModeModal({
  open,
  onClose,
  onConfirm,
}: GuestModeModalProps): React.JSX.Element | null {
  if (!open) return null;

  return (
    <ModalOverlay
      isOpen={open}
      isDismissable
      className="modal-overlay"
      onOpenChange={(isOpen) => {
        if (!isOpen) onClose();
      }}
    >
      <Modal className="modal guest-mode-modal">
        <Dialog
          className="dialog"
          aria-labelledby="guest-mode-title"
          aria-describedby="guest-mode-description"
        >
          <div className="dialog__header">
            <div>
              <p className="eyebrow">Cuenta opcional</p>
              <h2 id="guest-mode-title">Entrar en modo invitado</h2>
            </div>
            <button
              className="icon-button dialog__close"
              type="button"
              onClick={onClose}
              aria-label="Cerrar"
            >
              <X size={18} aria-hidden="true" />
            </button>
          </div>

          <div className="guest-mode-modal__body">
            <p id="guest-mode-description" className="guest-mode-modal__lead">
              El modo invitado está pensado para revisar un hemograma puntual sin crear una cuenta.
              Antes de continuar, ten presente estas limitaciones:
            </p>

            <ul className="guest-mode-list">
              {guestLimitations.map(({ icon: Icon, text }) => (
                <li key={text}>
                  <span aria-hidden="true">
                    <Icon size={18} />
                  </span>
                  <p>{text}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="dialog__actions">
            <button className="button button--ghost" type="button" onClick={onClose}>
              Volver
            </button>
            <button className="button button--primary" type="button" onClick={onConfirm}>
              Continuar como invitado
            </button>
          </div>
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}
