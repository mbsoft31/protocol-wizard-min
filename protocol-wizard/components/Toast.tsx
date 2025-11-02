
import React, { useEffect } from 'react';

type ToastType = 'success' | 'error' | 'info';

interface ToastProps {
  message: string;
  type: ToastType;
  onClose: () => void;
}

const toastStyles = {
  success: {
    bg: 'bg-green-800/90',
    border: 'border-green-600',
    icon: '✅',
  },
  error: {
    bg: 'bg-red-800/90',
    border: 'border-red-600',
    icon: '❌',
  },
  info: {
    bg: 'bg-sky-800/90',
    border: 'border-sky-600',
    icon: 'ℹ️',
  },
};

const Toast: React.FC<ToastProps> = ({ message, type, onClose }) => {
  const styles = toastStyles[type];

  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div
      className={`flex items-center gap-4 p-4 rounded-lg shadow-lg border text-sm text-slate-100 ${styles.bg} ${styles.border}`}
    >
      <span>{styles.icon}</span>
      <p>{message}</p>
      <button onClick={onClose} className="ml-auto text-xl font-bold leading-none">&times;</button>
    </div>
  );
};

export default Toast;
