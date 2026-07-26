import { Check, ChevronDown } from "lucide-react";
import {
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import type { MenuOption } from "./laboratoryModel";

export function ComposerMenu({
  label,
  value,
  options,
  icon,
  onChange,
  compact = false,
}: {
  label: string;
  value: string;
  options: MenuOption[];
  icon?: ReactNode;
  onChange(value: string): void;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const menuId = useId();
  const selected =
    options.find((option) => option.value === value) ?? options[0];
  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );

  const openMenu = useCallback(
    (nextIndex = selectedIndex) => {
      setActiveIndex(nextIndex);
      setOpen(true);
    },
    [selectedIndex],
  );

  const closeMenu = useCallback((restoreFocus: boolean) => {
    setOpen(false);
    if (restoreFocus)
      window.requestAnimationFrame(() => triggerRef.current?.focus());
  }, []);

  useEffect(() => {
    if (!open) return;

    function closeOnOutsideClick(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) closeMenu(false);
    }

    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, [closeMenu, open]);

  useEffect(() => {
    if (!open) return;
    window.requestAnimationFrame(() =>
      optionRefs.current[activeIndex]?.focus(),
    );
  }, [activeIndex, open]);

  function handleTriggerKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      openMenu(selectedIndex);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      openMenu(options.length - 1);
    }
  }

  function handleMenuKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    let nextIndex: number | null = null;
    if (event.key === "ArrowDown")
      nextIndex = (activeIndex + 1) % options.length;
    else if (event.key === "ArrowUp")
      nextIndex = (activeIndex - 1 + options.length) % options.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = options.length - 1;
    else if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      closeMenu(true);
      return;
    } else if (event.key === "Tab") {
      closeMenu(false);
      return;
    }

    if (nextIndex !== null) {
      event.preventDefault();
      setActiveIndex(nextIndex);
    }
  }

  return (
    <div className="laboratory-menu" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className={
          compact
            ? "laboratory-menu-trigger compact"
            : "laboratory-menu-trigger"
        }
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onKeyDown={handleTriggerKeyDown}
        onClick={() => (open ? closeMenu(false) : openMenu())}
      >
        {icon}
        <span>{selected?.label}</span>
        <ChevronDown aria-hidden="true" size={12} />
      </button>
      {open ? (
        <div
          id={menuId}
          className="laboratory-menu-popover"
          role="menu"
          aria-label={label}
          onKeyDown={handleMenuKeyDown}
        >
          {options.map((option, index) => (
            <button
              ref={(element) => {
                optionRefs.current[index] = element;
              }}
              key={option.value}
              type="button"
              role="menuitemradio"
              aria-checked={option.value === value}
              tabIndex={index === activeIndex ? 0 : -1}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => {
                onChange(option.value);
                closeMenu(true);
              }}
            >
              <span>{option.label}</span>
              {option.value === value ? (
                <Check aria-hidden="true" size={14} />
              ) : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
