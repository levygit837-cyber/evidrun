import { useCallback, useEffect, useState } from "react";

const knownRoutes = new Set(["/", "/projects", "/study", "/runs"]);

function normalizePath(pathname) {
  if (pathname !== "/" && pathname.endsWith("/")) {
    return pathname.slice(0, -1);
  }
  return knownRoutes.has(pathname) ? pathname : "/";
}

export function useRoute() {
  const [route, setRoute] = useState(() => normalizePath(window.location.pathname));

  useEffect(() => {
    const onPopState = () => setRoute(normalizePath(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate = useCallback((nextRoute, options = {}) => {
    const normalized = normalizePath(nextRoute);
    if (normalized === normalizePath(window.location.pathname)) return;
    const method = options.replace ? "replaceState" : "pushState";
    window.history[method]({}, "", normalized);
    setRoute(normalized);
    window.scrollTo?.({ top: 0, behavior: "instant" });
  }, []);

  const linkProps = useCallback(
    (href) => ({
      href,
      onClick: (event) => {
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
        navigate(href);
      },
    }),
    [navigate],
  );

  return { route, navigate, linkProps };
}
