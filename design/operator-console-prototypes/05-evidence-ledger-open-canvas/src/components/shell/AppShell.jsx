import { Sidebar } from "./Sidebar.jsx";
import { Topbar } from "./Topbar.jsx";
import { MobileNav } from "./MobileNav.jsx";

export function AppShell({ children, path, navigate, project, projects, onProjectChange, onUtility, onOpenChat, chatOpen }) {
  return (
    <div className="app-shell">
      <Sidebar path={path} navigate={navigate} project={project} projects={projects} onProjectChange={onProjectChange} />
      <div className="app-frame">
        <Topbar onUtility={onUtility} onOpenChat={onOpenChat} chatOpen={chatOpen} />
        <main className="route-canvas" id="main-content" tabIndex={-1}>{children}</main>
      </div>
      <MobileNav path={path} navigate={navigate} />
    </div>
  );
}
