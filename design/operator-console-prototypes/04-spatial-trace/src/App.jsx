import { useMemo, useState } from "react";
import { AppShell } from "./components/AppShell.jsx";
import { ChatDock } from "./components/ChatDock.jsx";
import { projectsSeed, study } from "./data/stubData.js";
import { useRoute } from "./hooks/useRoute.js";
import { LabView } from "./routes/LabView.jsx";
import { ProjectsView } from "./routes/ProjectsView.jsx";
import { RunsView } from "./routes/RunsView.jsx";
import { StudyView } from "./routes/StudyView.jsx";

function slugify(value) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function App() {
  const { route, linkProps } = useRoute();
  const [projects, setProjects] = useState(projectsSeed);
  const [selectedProjectId, setSelectedProjectId] = useState(projectsSeed[0].id);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? projects[0],
    [projects, selectedProjectId],
  );

  const selectedStudy = useMemo(
    () => (study.projectId === selectedProject.id ? study : null),
    [selectedProject.id],
  );

  const createProject = ({ name, purpose }) => {
    const id = `stub-project-${slugify(name) || "draft"}-${projects.length + 1}`;
    const project = {
      id,
      name,
      description: purpose,
      study: "Study ainda não definido",
      currentStage: "intent",
      nextAction: "Criar uma StudyRevision local",
      tone: "quiet",
      recordProfile: null,
    };
    setProjects((current) => [...current, project]);
    setSelectedProjectId(id);
  };

  let view;
  if (route === "/projects") {
    view = (
      <ProjectsView
        projects={projects}
        selectedProject={selectedProject}
        onSelectProject={setSelectedProjectId}
        onCreateProject={createProject}
        linkProps={linkProps}
      />
    );
  } else if (route === "/study") {
    view = (
      <StudyView
        key={selectedProject.id}
        project={selectedProject}
        study={selectedStudy}
        linkProps={linkProps}
      />
    );
  } else if (route === "/runs") {
    view = (
      <RunsView
        key={selectedProject.id}
        project={selectedProject}
        study={selectedStudy}
        linkProps={linkProps}
      />
    );
  } else {
    view = (
      <LabView
        project={selectedProject}
        hasBoundStudy={Boolean(selectedStudy)}
        linkProps={linkProps}
      />
    );
  }

  return (
    <AppShell
      route={route}
      linkProps={linkProps}
      projects={projects}
      selectedProject={selectedProject}
      activeStudy={selectedStudy}
      onSelectProject={setSelectedProjectId}
      chat={<ChatDock />}
    >
      {view}
    </AppShell>
  );
}
