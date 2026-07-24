import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { BackendRuntimeProvider } from "./app/BackendRuntimeProvider";
import { router } from "./app/router";
import "./styles/index.css";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5_000,
      refetchOnWindowFocus: false,
    },
    mutations: { retry: 0 },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BackendRuntimeProvider>
        <RouterProvider router={router} />
      </BackendRuntimeProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
