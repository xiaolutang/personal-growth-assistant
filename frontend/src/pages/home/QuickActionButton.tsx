interface QuickActionButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}

export function QuickActionButton({ icon, label, onClick }: QuickActionButtonProps) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center justify-center gap-1.5 rounded-xl border bg-card p-4 text-sm font-medium hover:bg-accent hover:border-primary/30 transition-colors active:scale-95"
    >
      <span className="text-primary">{icon}</span>
      <span>{label}</span>
    </button>
  );
}
