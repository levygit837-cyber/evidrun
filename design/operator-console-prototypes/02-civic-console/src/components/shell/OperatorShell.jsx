import { PrimaryNavRail } from "./PrimaryNavRail.jsx";
import { ProjectContextStrip } from "./ProjectContextStrip.jsx";

export function OperatorShell({
  currentPath,
  onNavigate,
  project,
  chat,
  children,
}) {
  return (
    <div className="operator-shell">
      <PrimaryNavRail currentPath={currentPath} onNavigate={onNavigate} />
      <div className="operator-main">
        <ProjectContextStrip project={project} />
        <main id="main-content" className="route-canvas" tabIndex="-1">
          {children}
        </main>
      </div>
      {chat}
    </div>
  );
}
