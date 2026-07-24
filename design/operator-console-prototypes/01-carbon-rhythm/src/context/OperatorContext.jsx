import { createContext, useContext } from "react";

export const OperatorContext = createContext(null);

export function useOperator() {
  const context = useContext(OperatorContext);
  if (!context) throw new Error("useOperator must be used inside OperatorContext.Provider");
  return context;
}
