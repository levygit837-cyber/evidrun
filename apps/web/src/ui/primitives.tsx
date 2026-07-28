import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Info,
  LoaderCircle,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import {
  forwardRef,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type TextareaHTMLAttributes,
} from "react";

type ButtonVariant = "primary" | "secondary" | "quiet" | "danger";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "small" | "medium";
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className = "", variant = "secondary", size = "medium", type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={`ui-button ui-button-${variant} ui-button-${size} ${className}`.trim()}
      {...props}
    />
  );
});

export const IconButton = forwardRef<HTMLButtonElement, ButtonProps>(function IconButton(
  { className = "", ...props },
  ref,
) {
  return <Button ref={ref} className={`ui-icon-button ${className}`.trim()} {...props} />;
});

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = "", ...props }, ref) {
    return <input ref={ref} className={`ui-input ${className}`.trim()} {...props} />;
  },
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className = "", ...props }, ref) {
    return <textarea ref={ref} className={`ui-textarea ${className}`.trim()} {...props} />;
  },
);

export function Spinner({ label = "Carregando", size = 16 }: { label?: string; size?: number }) {
  return (
    <span className="ui-spinner" role="status" aria-label={label}>
      <LoaderCircle aria-hidden="true" size={size} />
    </span>
  );
}

type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";

/** Distinct glyph per tone, for callers where colour alone would carry the difference. */
const statusGlyphs: Record<StatusTone, LucideIcon> = {
  neutral: Circle,
  info: Circle,
  success: CheckCircle2,
  warning: AlertCircle,
  danger: XCircle,
};

export function StatusIndicator({
  tone = "neutral",
  label,
  shape = "dot",
}: {
  tone?: StatusTone;
  label: string;
  /**
   * `dot` keeps the uniform bullet used across the app. `glyph` varies the icon per tone, so
   * two indicators side by side stay distinguishable without relying on colour — the tones
   * differ from each other by well under 3:1.
   */
  shape?: "dot" | "glyph";
}) {
  const Icon = shape === "glyph" ? statusGlyphs[tone] : Circle;
  return (
    <span className={`ui-status ui-status-${tone}`}>
      <Icon aria-hidden="true" size={shape === "glyph" ? 12 : 7} fill={shape === "glyph" ? "none" : "currentColor"} />
      <span>{label}</span>
    </span>
  );
}

const noticeIcons: Record<Exclude<StatusTone, "neutral">, LucideIcon> = {
  info: Info,
  success: CheckCircle2,
  warning: AlertCircle,
  danger: AlertCircle,
};

export function InlineNotice({
  tone = "info",
  title,
  children,
}: {
  tone?: Exclude<StatusTone, "neutral">;
  title?: string;
  children: ReactNode;
}) {
  const Icon = noticeIcons[tone];
  return (
    <div className={`ui-notice ui-notice-${tone}`} role={tone === "danger" ? "alert" : "status"}>
      <Icon aria-hidden="true" size={16} />
      <div>
        {title ? <strong>{title}</strong> : null}
        <div>{children}</div>
      </div>
    </div>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="ui-page-state" role="status">
      <Spinner label={label} size={20} />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="ui-page-state ui-empty-state">
      <strong>{title}</strong>
      {children ? <div>{children}</div> : null}
    </div>
  );
}

export function ErrorState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="ui-page-state ui-error-state" role="alert">
      <AlertCircle aria-hidden="true" size={20} />
      <strong>{title}</strong>
      {children ? <div>{children}</div> : null}
    </div>
  );
}

export function Tooltip({ content, children }: { content: ReactNode; children: ReactNode }) {
  return (
    <TooltipPrimitive.Provider delayDuration={250}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content className="ui-tooltip" sideOffset={6}>
            {content}
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}
