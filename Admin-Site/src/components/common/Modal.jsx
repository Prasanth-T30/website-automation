import { AnimatePresence, motion } from "framer-motion";
import { FiX } from "react-icons/fi";

const Modal = ({ open, onClose, title, children, footer, maxWidth = "max-w-lg" }) => (
  <AnimatePresence>
    {open && (
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F1B2D]/40 p-4 backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          className={`w-full ${maxWidth} rounded-2xl bg-white shadow-[0_24px_60px_-30px_rgba(15,27,45,.6)]`}
          initial={{ scale: 0.95, opacity: 0, y: 10 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 10 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between border-b border-[#EEF2F7] px-5 py-4">
            <h3 className="text-base font-extrabold text-[#0F1B2D]">{title}</h3>
            <button onClick={onClose} className="rounded-full p-1.5 text-[#8494A9] hover:bg-[#F2F6FB] hover:text-[#41536B]">
              <FiX size={18} />
            </button>
          </div>
          <div className="max-h-[70vh] overflow-y-auto px-5 py-4">{children}</div>
          {footer && <div className="flex justify-end gap-2 border-t border-[#EEF2F7] px-5 py-4">{footer}</div>}
        </motion.div>
      </motion.div>
    )}
  </AnimatePresence>
);

export default Modal;
