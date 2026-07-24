import {
  ACTIVITY_SEQUENCE,
  CORRECTED_REVISION,
  INITIAL_MESSAGES,
  PROJECTS,
  PROJECT_STAGES,
  RUN_PHASES,
  STUDY_REVISIONS,
} from "../data/mockData.js";

const RELEASE_INTEGRITY_PROJECT_ID = "project-release-integrity-stub";

function cloneRevisions(revisions) {
  return revisions.map((revision) => ({
    ...revision,
    runSpecs: revision.runSpecs.map((runSpec) => ({ ...runSpec })),
  }));
}

function createAgentState({ seeded = false, projectName }) {
  return {
    status: "idle",
    auto: false,
    activityCount: seeded ? ACTIVITY_SEQUENCE.length : 0,
    messages: seeded ? INITIAL_MESSAGES.map((message) => ({ ...message })) : [],
    liveMessage: seeded
      ? "Lab Agent pronto para um novo draft local."
      : `Nenhuma Study vinculada a ${projectName}.`,
  };
}

function createReleaseIntegrityStudy() {
  return {
    id: "study:stub-release-integrity",
    title: "Diagnóstico de regressões após deploy",
    scenario: "deployment-log-trace",
    variant: "evidence-first",
    revisions: cloneRevisions(STUDY_REVISIONS),
    selectedRevisionId: STUDY_REVISIONS[0].id,
    notice: "",
  };
}

function createRunState() {
  return {
    status: "idle",
    phaseIndex: -1,
    auto: false,
    sourceRevisionId: null,
    events: [],
    liveMessage: "Nenhuma Run stub admitida foi enfileirada para este Project.",
  };
}

export function selectCurrentProject(state) {
  return state.projects.find((project) => project.id === state.currentProjectId) ?? null;
}

export function selectCurrentAgent(state) {
  return state.agentsByProjectId[state.currentProjectId];
}

export function selectCurrentStudy(state) {
  return state.studiesByProjectId[state.currentProjectId] ?? null;
}

export function selectCurrentRun(state) {
  return state.runsByProjectId[state.currentProjectId] ?? null;
}

function updateCurrentAgent(state, updater) {
  const current = selectCurrentAgent(state);
  if (!current) return state;
  return {
    ...state,
    agentsByProjectId: {
      ...state.agentsByProjectId,
      [state.currentProjectId]: updater(current),
    },
  };
}

function updateCurrentStudy(state, updater) {
  const current = selectCurrentStudy(state);
  if (!current) return state;
  return {
    ...state,
    studiesByProjectId: {
      ...state.studiesByProjectId,
      [state.currentProjectId]: updater(current),
    },
  };
}

function updateCurrentRun(state, updater) {
  const current = selectCurrentRun(state);
  if (!current) return state;
  return {
    ...state,
    runsByProjectId: {
      ...state.runsByProjectId,
      [state.currentProjectId]: updater(current),
    },
  };
}

function admittedSourceRevision(state) {
  const study = selectCurrentStudy(state);
  const run = selectCurrentRun(state);
  if (!study || !run?.sourceRevisionId) return null;
  const revision = study.revisions.find((item) => item.id === run.sourceRevisionId);
  if (!revision || revision.runSpecs.some((runSpec) => runSpec.admission !== "admitted")) {
    return null;
  }
  return revision;
}

export function createInitialState() {
  const projects = PROJECTS.map((project) => ({ ...project }));
  const agentsByProjectId = Object.fromEntries(
    projects.map((project) => [
      project.id,
      createAgentState({
        seeded: project.id === RELEASE_INTEGRITY_PROJECT_ID,
        projectName: project.name,
      }),
    ]),
  );
  const chatThreadsByProjectId = Object.fromEntries(
    projects.map((project) => [
      project.id,
      project.id === RELEASE_INTEGRITY_PROJECT_ID
        ? [{ id: "chat-seed", body: "O que mudou depois do deploy?", time: "09:16" }]
        : [],
    ]),
  );

  return {
    projects,
    currentProjectId: RELEASE_INTEGRITY_PROJECT_ID,
    selectedProjectStage: PROJECT_STAGES[2].id,
    agentsByProjectId,
    studiesByProjectId: {
      [RELEASE_INTEGRITY_PROJECT_ID]: createReleaseIntegrityStudy(),
    },
    runsByProjectId: {
      [RELEASE_INTEGRITY_PROJECT_ID]: createRunState(),
    },
    chat: {
      mode: "compact",
      lastOpenMode: "compact",
      previewTarget: null,
      snapMenuOpen: false,
      snapIndex: 0,
      threadsByProjectId: chatThreadsByProjectId,
    },
  };
}

function createAgentResponse(prompt, projectName) {
  return {
    id: `message-agent-${Date.now()}`,
    role: "agent",
    body: `Draft local para ${projectName}: o input autorizado relacionado a “${prompt}” aponta para a troca do bundle de release. Revise antes de qualquer aceitação humana.`,
    time: "09:16",
  };
}

function addRunEvent(events, phaseIndex) {
  const phase = RUN_PHASES[phaseIndex];
  if (!phase) return events;
  return [
    ...events,
    {
      id: `event:stub-run-ri-0723-a:${phase.id}`,
      type: phase.event,
      label: phase.label,
    },
  ];
}

export function operatorReducer(state, action) {
  switch (action.type) {
    case "PROJECT_SELECT": {
      if (!state.projects.some((project) => project.id === action.projectId)) return state;
      return {
        ...state,
        currentProjectId: action.projectId,
        chat: { ...state.chat, previewTarget: null, snapMenuOpen: false },
      };
    }

    case "PROJECT_STAGE_SELECT":
      return { ...state, selectedProjectStage: action.stageId };

    case "PROJECT_CREATE": {
      const project = {
        id: `project-local-stub-${state.projects.length + 1}`,
        name: action.name.trim(),
        intent: action.intent.trim(),
        study: "Nenhuma Study vinculada",
        linkedStudyId: null,
        workspace: "Integration pending",
      };
      return {
        ...state,
        projects: [...state.projects, project],
        currentProjectId: project.id,
        selectedProjectStage: "intent",
        agentsByProjectId: {
          ...state.agentsByProjectId,
          [project.id]: createAgentState({ projectName: project.name }),
        },
        chat: {
          ...state.chat,
          threadsByProjectId: {
            ...state.chat.threadsByProjectId,
            [project.id]: [],
          },
        },
      };
    }

    case "AGENT_SEND": {
      const prompt = action.prompt.trim();
      const agent = selectCurrentAgent(state);
      const study = selectCurrentStudy(state);
      if (!prompt || !study || !agent || agent.status === "running") return state;
      return updateCurrentAgent(state, (current) => ({
        ...current,
        status: "running",
        auto: true,
        activityCount: 1,
        pendingPrompt: prompt,
        messages: [
          ...current.messages,
          {
            id: `message-user-${Date.now()}`,
            role: "user",
            body: prompt,
            time: "09:16",
          },
        ],
        liveMessage: ACTIVITY_SEQUENCE[0].label,
      }));
    }

    case "AGENT_ADVANCE": {
      const agent = selectCurrentAgent(state);
      if (!agent || agent.status !== "running" || !agent.auto || !selectCurrentStudy(state)) {
        return state;
      }
      const nextCount = Math.min(ACTIVITY_SEQUENCE.length, agent.activityCount + 1);
      const completed = nextCount === ACTIVITY_SEQUENCE.length;
      const project = selectCurrentProject(state);
      return updateCurrentAgent(state, (current) => ({
        ...current,
        status: completed ? "success" : "running",
        auto: !completed,
        activityCount: nextCount,
        messages: completed
          ? [...current.messages, createAgentResponse(current.pendingPrompt, project?.name ?? "Project")]
          : current.messages,
        liveMessage: completed
          ? "Resposta capturada como draft local do Lab Agent."
          : ACTIVITY_SEQUENCE[nextCount - 1].label,
      }));
    }

    case "AGENT_PRESET": {
      if (!selectCurrentStudy(state)) return state;
      const config = {
        idle: {
          status: "idle",
          activityCount: ACTIVITY_SEQUENCE.length,
          liveMessage: "Lab Agent pronto para um novo draft local.",
        },
        running: {
          status: "running",
          activityCount: 3,
          liveMessage: "Chamada local de tool em andamento.",
        },
        success: {
          status: "success",
          activityCount: ACTIVITY_SEQUENCE.length,
          liveMessage: "Resposta capturada como draft local do Lab Agent.",
        },
        failure: {
          status: "failure",
          activityCount: 3,
          liveMessage: "Falha local ilustrativa. Nenhuma resposta foi capturada.",
        },
      }[action.preset];
      if (!config) return state;
      return updateCurrentAgent(state, (current) => ({ ...current, ...config, auto: false }));
    }

    case "CHAT_ADD_MESSAGE": {
      const body = action.body.trim();
      if (!body) return state;
      const currentThread = state.chat.threadsByProjectId[state.currentProjectId] ?? [];
      return {
        ...state,
        chat: {
          ...state.chat,
          threadsByProjectId: {
            ...state.chat.threadsByProjectId,
            [state.currentProjectId]: [
              ...currentThread,
              { id: `chat-${Date.now()}`, body, time: "09:17" },
            ],
          },
        },
      };
    }

    case "CHAT_OPEN": {
      const mode = state.chat.mode === "closed" ? state.chat.lastOpenMode : state.chat.mode;
      return { ...state, chat: { ...state.chat, mode } };
    }

    case "CHAT_CLOSE":
      return {
        ...state,
        chat: {
          ...state.chat,
          lastOpenMode: state.chat.mode === "closed" ? state.chat.lastOpenMode : state.chat.mode,
          mode: "closed",
          previewTarget: null,
          snapMenuOpen: false,
        },
      };

    case "CHAT_SET_MODE":
      return {
        ...state,
        chat: {
          ...state.chat,
          mode: action.mode,
          lastOpenMode: action.mode,
          previewTarget: null,
          snapMenuOpen: false,
        },
      };

    case "CHAT_TOGGLE_MENU":
      return {
        ...state,
        chat: {
          ...state.chat,
          snapMenuOpen: !state.chat.snapMenuOpen,
          previewTarget: null,
        },
      };

    case "CHAT_MENU_CLOSE":
      return { ...state, chat: { ...state.chat, snapMenuOpen: false, previewTarget: null } };

    case "CHAT_MENU_INDEX":
      return { ...state, chat: { ...state.chat, snapIndex: action.index } };

    case "CHAT_PREVIEW":
      return { ...state, chat: { ...state.chat, previewTarget: action.target } };

    case "STUDY_SELECT_REVISION":
      return updateCurrentStudy(state, (study) => ({
        ...study,
        selectedRevisionId: action.revisionId,
        notice: "",
      }));

    case "STUDY_UPDATE_OBJECTIVE":
      return updateCurrentStudy(state, (study) => ({
        ...study,
        revisions: study.revisions.map((revision) =>
          revision.id === study.selectedRevisionId
            ? { ...revision, objective: action.objective }
            : revision,
        ),
      }));

    case "STUDY_CORRECT_REVISION":
      return updateCurrentStudy(state, (study) => {
        const alreadyExists = study.revisions.some(
          (revision) => revision.id === CORRECTED_REVISION.id,
        );
        return {
          ...study,
          revisions: alreadyExists
            ? study.revisions
            : [
                {
                  ...CORRECTED_REVISION,
                  runSpecs: CORRECTED_REVISION.runSpecs.map((runSpec) => ({ ...runSpec })),
                },
                ...study.revisions,
              ],
          selectedRevisionId: CORRECTED_REVISION.id,
          notice: "Revisão 04 criada em estado local. Nenhuma aceitação humana foi inferida.",
        };
      });

    case "STUDY_ENQUEUE": {
      const study = selectCurrentStudy(state);
      if (!study) return state;
      const revision = study.revisions.find((item) => item.id === study.selectedRevisionId);
      if (!revision || revision.runSpecs.some((runSpec) => runSpec.admission !== "admitted")) {
        return state;
      }
      const nextStudy = {
        ...study,
        notice: "Dois RunSpecs admitidos foram enfileirados apenas neste stub local.",
      };
      const run = selectCurrentRun(state) ?? createRunState();
      const nextRun = {
        ...run,
        status: "queued",
        phaseIndex: 0,
        auto: false,
        sourceRevisionId: revision.id,
        events: addRunEvent([], 0),
        liveMessage: "Run stub enfileirada. Inicie a sequência determinística quando estiver pronto.",
      };
      return {
        ...state,
        studiesByProjectId: {
          ...state.studiesByProjectId,
          [state.currentProjectId]: nextStudy,
        },
        runsByProjectId: {
          ...state.runsByProjectId,
          [state.currentProjectId]: nextRun,
        },
      };
    }

    case "RUN_START": {
      const run = selectCurrentRun(state);
      if (!run || run.auto || !admittedSourceRevision(state)) return state;
      return updateCurrentRun(state, (current) => ({
        ...current,
        status: "queued",
        phaseIndex: 0,
        auto: true,
        events: addRunEvent([], 0),
        liveMessage: "Run stub enfileirada.",
      }));
    }

    case "RUN_ADVANCE": {
      const run = selectCurrentRun(state);
      if (
        !run ||
        !run.auto ||
        !admittedSourceRevision(state) ||
        run.phaseIndex >= RUN_PHASES.length - 1
      ) {
        return state;
      }
      const nextIndex = run.phaseIndex + 1;
      const phase = RUN_PHASES[nextIndex];
      const terminal = phase.id === "terminal";
      return updateCurrentRun(state, (current) => ({
        ...current,
        status: phase.id,
        phaseIndex: nextIndex,
        auto: !terminal,
        events: addRunEvent(current.events, nextIndex),
        liveMessage: terminal
          ? "Sequência stub chegou ao estado terminal. Isto não prova uma Run canônica."
          : `Fase local: ${phase.label}.`,
      }));
    }

    case "RUN_PRESET": {
      if (!admittedSourceRevision(state)) return state;
      const presetIndex = {
        loading: 1,
        failed: 2,
        completed: RUN_PHASES.length - 1,
      }[action.preset];
      if (presetIndex === undefined) return state;
      const status = action.preset === "failed" ? "failed" : RUN_PHASES[presetIndex].id;
      return updateCurrentRun(state, (run) => ({
        ...run,
        status,
        phaseIndex: presetIndex,
        auto: false,
        events:
          action.preset === "failed"
            ? [
                ...RUN_PHASES.slice(0, 3).map((_, index) => addRunEvent([], index)[0]),
                {
                  id: "event:stub-run-ri-0723-a:failed",
                  type: "run.failed",
                  label: "Falha local ilustrativa",
                },
              ]
            : RUN_PHASES.slice(0, presetIndex + 1).map((_, index) => addRunEvent([], index)[0]),
        liveMessage:
          action.preset === "failed"
            ? "Falha local ilustrativa. O estado terminal não foi convertido em completed."
            : action.preset === "completed"
              ? "Sequência stub terminal concluída; nenhuma Run canônica foi alegada."
              : "Carregando preparação local ilustrativa.",
      }));
    }

    default:
      return state;
  }
}
