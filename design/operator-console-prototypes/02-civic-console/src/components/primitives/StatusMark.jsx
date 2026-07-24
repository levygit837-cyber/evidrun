import {
  Check,
  Clock,
  Minus,
  WarningCircle,
  X,
} from "@phosphor-icons/react";

const iconByTone = {
  success: Check,
  danger: X,
  pending: Clock,
  neutral: Minus,
  warning: WarningCircle,
};

export function StatusMark({ tone = "neutral", label, compact = false }) {
  const Icon = iconByTone[tone] ?? Minus;

  return (
    <span className={`status-mark status-mark-${tone}${compact ? " is-compact" : ""}`}>
      <Icon aria-hidden="true" size={compact ? 14 : 16} weight="bold" />
      <span>{label}</span>
    </span>
  );
}
