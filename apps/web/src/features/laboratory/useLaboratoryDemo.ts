import {
  type KeyboardEvent as ReactKeyboardEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import type { LaboratoryAdapter } from "../../data/contracts";
import {
  CONTEXT_ITEMS,
  type ContextItem,
  type LaboratoryPhase,
  TEXTAREA_MAX_HEIGHT_PX,
  TEXTAREA_MIN_HEIGHT_PX,
  type ToolEvent,
  isRunningPhase,
} from "./laboratoryModel";

/**
 * Phase machine for the Laboratory demo: `empty → ready → submitting → active → stopping →
 * completed | cancelled | failed | unavailable`.
 *
 * `submitLockRef` is a synchronous guard: it is set before the first `await` so two clicks
 * dispatched inside one task can never both reach `adapter.send`.
 */
export function useLaboratoryDemo(laboratoryAdapter: LaboratoryAdapter) {
  const initiallyUnavailable = laboratoryAdapter.mode !== "demo";
  const [phase, setPhase] = useState<LaboratoryPhase>(
    initiallyUnavailable ? "unavailable" : "empty",
  );
  const [input, setInput] = useState("");
  const [userMessage, setUserMessage] = useState<string | null>(null);
  const [agentMessage, setAgentMessage] = useState<string | null>(null);
  const [statusLog, setStatusLog] = useState<string[]>([]);
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [approval, setApproval] = useState("ask");
  const [model, setModel] = useState("deepseek-v4-flash");
  const [reasoning, setReasoning] = useState("max");
  const [contextItems, setContextItems] = useState<ContextItem[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const submitLockRef = useRef(false);
  const lastSubmittedInputRef = useRef<string | null>(null);
  const isRunning = isRunningPhase(phase);
  const conversationStarted = userMessage !== null;

  const resizeTextarea = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(Math.max(textarea.scrollHeight, TEXTAREA_MIN_HEIGHT_PX), TEXTAREA_MAX_HEIGHT_PX)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [input, resizeTextarea]);

  useEffect(
    () => () => {
      abortControllerRef.current?.abort();
    },
    [],
  );

  const runDemo = useCallback(
    async (exactInput: string) => {
      if (submitLockRef.current) return;
      submitLockRef.current = true;
      const controller = new AbortController();
      abortControllerRef.current = controller;
      lastSubmittedInputRef.current = exactInput;
      setUserMessage(exactInput);
      setAgentMessage(null);
      setStatusLog([]);
      setTools([]);
      setError(null);
      setInput("");
      setPhase("submitting");

      let terminalEventSeen = false;
      try {
        for await (const event of laboratoryAdapter.send(
          exactInput,
          controller.signal,
        )) {
          if (event.source !== laboratoryAdapter.mode) {
            setError(
              "O adapter retornou uma fonte incompatível com o modo declarado.",
            );
            setPhase("failed");
            return;
          }

          if (event.type === "status") {
            setPhase("active");
            setStatusLog((current) => [...current, event.label]);
          } else if (event.type === "tool") {
            setPhase("active");
            setTools((current) => {
              const existingIndex = current.findIndex(
                (tool) => tool.id === event.id,
              );
              if (existingIndex === -1) return [...current, event];
              return current.map((tool, index) =>
                index === existingIndex ? event : tool,
              );
            });
          } else if (event.type === "message") {
            setPhase("active");
            setAgentMessage(event.content);
          } else if (event.type === "error") {
            terminalEventSeen = true;
            setError(event.message);
            setPhase(event.source === "demo" ? "failed" : "unavailable");
          } else if (event.type === "done") {
            terminalEventSeen = true;
            setPhase("completed");
          }
        }

        if (!terminalEventSeen && !controller.signal.aborted) {
          setError("O adapter encerrou sem um evento terminal.");
          setPhase("failed");
        }
      } catch (caught) {
        if (
          controller.signal.aborted ||
          (caught instanceof DOMException && caught.name === "AbortError")
        ) {
          if (abortControllerRef.current === controller) setPhase("cancelled");
        } else {
          setError(
            caught instanceof Error
              ? caught.message
              : "Falha inesperada na demonstração.",
          );
          setPhase("failed");
        }
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
          submitLockRef.current = false;
        }
      }
    },
    [laboratoryAdapter],
  );

  function submit() {
    if (
      submitLockRef.current ||
      isRunning ||
      phase === "unavailable" ||
      input.trim().length === 0
    ) {
      return;
    }
    void runDemo(input);
  }

  function cancel() {
    if (!abortControllerRef.current || !isRunning) return;
    setPhase("stopping");
    abortControllerRef.current.abort();
  }

  function reset() {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    submitLockRef.current = false;
    lastSubmittedInputRef.current = null;
    setInput("");
    setUserMessage(null);
    setAgentMessage(null);
    setStatusLog([]);
    setTools([]);
    setError(null);
    setPhase(initiallyUnavailable ? "unavailable" : "empty");
    textareaRef.current?.focus();
  }

  function handleInput(nextInput: string) {
    setInput(nextInput);
    if (!conversationStarted && phase !== "unavailable") {
      setPhase(nextInput.trim().length > 0 ? "ready" : "empty");
    }
  }

  return {
    phase,
    input,
    userMessage,
    agentMessage,
    statusLog,
    tools,
    error,
    approval,
    setApproval,
    model,
    setModel,
    reasoning,
    setReasoning,
    contextItems,
    textareaRef,
    isRunning,
    conversationStarted,
    resizeTextarea,
    submit,
    cancel,
    reset,
    handleInput,
    retry() {
      const lastInput = lastSubmittedInputRef.current;
      if (lastInput) void runDemo(lastInput);
    },
    handleKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        if (isRunning) cancel();
        else submit();
      }
    },
    addContext(value: string) {
      const item = value === "run" ? CONTEXT_ITEMS.run : CONTEXT_ITEMS.artifact;
      setContextItems((current) =>
        current.some((currentItem) => currentItem.id === item.id)
          ? current
          : [...current, item],
      );
    },
    removeContext(id: string) {
      setContextItems((current) => current.filter((item) => item.id !== id));
    },
  };
}
