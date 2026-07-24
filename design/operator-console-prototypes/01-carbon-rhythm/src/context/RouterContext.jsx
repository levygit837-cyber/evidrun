import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const RouterContext = createContext(null);

function normalizePath(pathname) {
  if (!pathname || pathname === "/") return "/";
  return pathname.replace(/\/+$/, "") || "/";
}

export function RouterProvider({ children }) {
  const [path, setPath] = useState(() => normalizePath(window.location.pathname));

  useEffect(() => {
    const handlePopState = () => setPath(normalizePath(window.location.pathname));
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((nextPath, { replace = false } = {}) => {
    const normalized = normalizePath(nextPath);
    const method = replace ? "replaceState" : "pushState";
    window.history[method]({}, "", normalized);
    setPath(normalized);
  }, []);

  const value = useMemo(() => ({ path, navigate }), [navigate, path]);
  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function useRouter() {
  const context = useContext(RouterContext);
  if (!context) throw new Error("useRouter must be used inside RouterProvider");
  return context;
}

export function RouteLink({ to, children, className = "", activeClassName = "", ...props }) {
  const { path, navigate } = useRouter();
  const active = path === to;

  return (
    <a
      {...props}
      className={`${className} ${active ? activeClassName : ""}`.trim()}
      href={to}
      aria-current={active ? "page" : undefined}
      onClick={(event) => {
        props.onClick?.(event);
        if (
          event.defaultPrevented ||
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        ) {
          return;
        }
        event.preventDefault();
        navigate(to);
      }}
    >
      {children}
    </a>
  );
}
