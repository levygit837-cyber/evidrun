import { useMutation, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState, type Dispatch, type FormEvent, type SetStateAction } from "react";
import type { CreationAdapter } from "../../data/contracts";
import type { BootstrapDemoResult } from "../../types";
import {
  type AdmissionState,
  type CompiledStudy,
  type DownstreamState,
  type Step,
  type StudyCollection,
  type StudyDraft,
  classifyFailure,
  initialStudy,
} from "./createModel";

/** Delay before the pending spinner appears, so a fast bootstrap never flashes it. */
const PENDING_SPINNER_DELAY_MS = 150;

/** Wizard state plus the actions the Create stages need. Owned by {@link useStudyDraft}. */
export interface StudyDraftState {
  bootstrap: UseMutationResult<BootstrapDemoResult, Error, void, unknown>;
  activeStep: Step;
  setActiveStep: Dispatch<SetStateAction<Step>>;
  maxReachedStep: Step;
  setMaxReachedStep: Dispatch<SetStateAction<Step>>;
  study: StudyDraft;
  compiledStudy: CompiledStudy | null;
  downstreamState: DownstreamState;
  result: BootstrapDemoResult | null;
  showPendingSpinner: boolean;
  admissionState: AdmissionState;
  updateStudy<Key extends keyof StudyDraft>(key: Key, value: StudyDraft[Key]): void;
  updateStudyItem(collection: StudyCollection, id: string, name: string): void;
  addStudyItem(collection: StudyCollection, name: string): void;
  removeStudyItem(collection: StudyCollection, id: string): void;
  editStudy(): void;
  compileRunSpecs(event: FormEvent): void;
  runBootstrap(): void;
}

/**
 * Wizard state and the CRL-CTX-002 bootstrap mutation.
 *
 * `submissionInFlight` is a synchronous guard set before `mutate`, so two clicks in the same task
 * cannot both reach the adapter. Any effective study edit marks the downstream stale.
 */
export function useStudyDraft(adapter: CreationAdapter): StudyDraftState {
  const queryClient = useQueryClient();
  const [activeStep, setActiveStep] = useState<Step>(1);
  const [maxReachedStep, setMaxReachedStep] = useState<Step>(1);
  const [study, setStudy] = useState<StudyDraft>(initialStudy);
  const [compiledStudy, setCompiledStudy] = useState<CompiledStudy | null>(null);
  const [downstreamState, setDownstreamState] = useState<DownstreamState>("empty");
  const [result, setResult] = useState<BootstrapDemoResult | null>(null);
  const [showPendingSpinner, setShowPendingSpinner] = useState(false);
  const submissionInFlight = useRef(false);
  const nextItemId = useRef(2);

  const bootstrap = useMutation({
    mutationFn: () => adapter.bootstrapCanonicalDemo(),
    onSuccess: async (nextResult) => {
      setResult(nextResult);
      setDownstreamState("fresh");
      setActiveStep(4);
      setMaxReachedStep(4);
      await queryClient.invalidateQueries();
    },
    onSettled: () => {
      submissionInFlight.current = false;
    },
  });

  useEffect(() => {
    if (!bootstrap.isPending) {
      setShowPendingSpinner(false);
      return;
    }
    const timer = window.setTimeout(() => setShowPendingSpinner(true), PENDING_SPINNER_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [bootstrap.isPending]);

  const admissionState = useMemo<AdmissionState>(() => {
    if (downstreamState === "stale") return "stale";
    if (bootstrap.error) return classifyFailure(bootstrap.error);
    if (result) return "admitted";
    if (compiledStudy?.evaluationDisclosure === "pre_run") return "rejected";
    return "unavailable";
  }, [bootstrap.error, compiledStudy?.evaluationDisclosure, downstreamState, result]);

  const markDownstreamStale = () => {
    if (compiledStudy) {
      setDownstreamState("stale");
      setMaxReachedStep(1);
    }
    setResult(null);
    bootstrap.reset();
  };

  return {
    bootstrap,
    activeStep,
    setActiveStep,
    maxReachedStep,
    setMaxReachedStep,
    study,
    compiledStudy,
    downstreamState,
    result,
    showPendingSpinner,
    admissionState,

    updateStudy<Key extends keyof StudyDraft>(key: Key, value: StudyDraft[Key]) {
      setStudy((current) => ({ ...current, [key]: value }));
      markDownstreamStale();
    },

    updateStudyItem(collection: StudyCollection, id: string, name: string) {
      setStudy((current) => ({
        ...current,
        [collection]: current[collection].map((item) => (item.id === id ? { ...item, name } : item)),
      }));
      markDownstreamStale();
    },

    addStudyItem(collection: StudyCollection, name: string) {
      const id = `${collection}-${nextItemId.current++}`;
      setStudy((current) => ({ ...current, [collection]: [...current[collection], { id, name }] }));
      markDownstreamStale();
    },

    removeStudyItem(collection: StudyCollection, id: string) {
      setStudy((current) => ({
        ...current,
        [collection]: current[collection].filter((item) => item.id !== id),
      }));
      markDownstreamStale();
    },

    editStudy() {
      setActiveStep(1);
    },

    compileRunSpecs(event: FormEvent) {
      event.preventDefault();
      setCompiledStudy({
        ...study,
        scenarios: study.scenarios.map((item) => ({ ...item })),
        variants: study.variants.map((item) => ({ ...item })),
        evaluationModules: study.evaluationModules.map((item) => ({ ...item })),
        revision: (compiledStudy?.revision ?? 0) + 1,
      });
      setDownstreamState("fresh");
      setResult(null);
      bootstrap.reset();
      setActiveStep(2);
      setMaxReachedStep(2);
    },

    runBootstrap() {
      if (submissionInFlight.current || bootstrap.isPending) return;
      submissionInFlight.current = true;
      bootstrap.mutate();
    },
  };
}
