import { useCallback, useEffect, useState } from "react";

const VALID_ROUTES = new Set(["lab", "projects", "study", "runs"]);

function routeFromHash() {
  const candidate = window.location.hash.replace(/^#\/?/, "").split("/")[0];
  return VALID_ROUTES.has(candidate) ? candidate : "lab";
}

export function useHashRoute() {
  const [route, setRoute] = useState(routeFromHash);

  useEffect(() => {
    const resetScroll = () => {
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
    };

    if (!VALID_ROUTES.has(window.location.hash.replace(/^#\/?/, "").split("/")[0])) {
      window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}#/lab`);
    }
    resetScroll();

    const handleHashChange = () => {
      resetScroll();
      setRoute(routeFromHash());
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const navigate = useCallback((nextRoute) => {
    if (!VALID_ROUTES.has(nextRoute)) return;
    if (routeFromHash() === nextRoute) {
      setRoute(nextRoute);
      return;
    }
    window.location.hash = `/${nextRoute}`;
  }, []);

  return { route, navigate };
}
