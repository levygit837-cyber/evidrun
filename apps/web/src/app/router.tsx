import { lazy, Suspense, type ComponentType } from "react";
import {
  createHashHistory,
  createRootRoute,
  createRoute,
  createRouter,
  redirect,
} from "@tanstack/react-router";
import { AppShell } from "./AppShell";
import { LoadingState } from "../ui/primitives";

const LaboratoryPage = lazy(() =>
  import("../features/laboratory/LaboratoryPage").then((module) => ({
    default: module.LaboratoryPage,
  })),
);
const CreatePage = lazy(() =>
  import("../features/create/CreatePage").then((module) => ({ default: module.CreatePage })),
);
const ObservabilityPage = lazy(() =>
  import("../features/observability/ObservabilityPage").then((module) => ({
    default: module.ObservabilityPage,
  })),
);

function suspended(Page: ComponentType) {
  return function SuspendedRoute() {
    return (
      <Suspense fallback={<LoadingState label="Carregando área…" />}>
        <Page />
      </Suspense>
    );
  };
}

const rootRoute = createRootRoute({ component: AppShell });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/laboratory" });
  },
});

const laboratoryRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/laboratory",
  component: suspended(LaboratoryPage),
});

const createPageRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/create",
  component: suspended(CreatePage),
});

export interface ObservabilitySearch {
  q?: string;
  status?: string;
  period?: string;
  run?: string;
}

const observabilityRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/observability",
  validateSearch: (search: Record<string, unknown>): ObservabilitySearch => ({
    q: typeof search.q === "string" && search.q ? search.q : undefined,
    status: typeof search.status === "string" && search.status ? search.status : undefined,
    period: typeof search.period === "string" && search.period ? search.period : undefined,
    run: typeof search.run === "string" && search.run ? search.run : undefined,
  }),
  component: suspended(ObservabilityPage),
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  laboratoryRoute,
  createPageRoute,
  observabilityRoute,
]);

export const router = createRouter({ routeTree, history: createHashHistory() });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
