import {
  BoundingBox,
  CaretDown,
  Flask,
  Info,
  Notebook,
  Pulse,
  SidebarSimple,
  X,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useId, useRef, useState } from "react";
import { DEMO_NOTICE } from "../data/stubData.js";

const navItems = [
  { route: "/", label: "Lab", Icon: Flask },
  { route: "/projects", label: "Projects", Icon: BoundingBox },
  { route: "/study", label: "Study", Icon: Notebook },
  { route: "/runs", label: "Runs", Icon: Pulse },
];

function NavItems({ route, linkProps, mobile = false }) {
  return navItems.map(({ route: target, label, Icon }) => {
    const active = route === target;
    return (
      <a
        {...linkProps(target)}
        key={target}
        className={`${mobile ? "mobile-nav__link" : "rail-nav__link"} ${active ? "is-active" : ""}`}
        aria-current={active ? "page" : undefined}
      >
        <Icon size={mobile ? 22 : 21} weight={active ? "fill" : "regular"} aria-hidden="true" />
        <span>{label}</span>
      </a>
    );
  });
}

function ProjectSwitcher({ projects, selectedProject, onSelect }) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const ref = useRef(null);
  const triggerRef = useRef(null);
  const optionRefs = useRef([]);
  const listboxId = useId();
  const selectedIndex = Math.max(
    0,
    projects.findIndex((project) => project.id === selectedProject.id),
  );

  const closeMenu = (restoreFocus = true) => {
    setOpen(false);
    if (restoreFocus) triggerRef.current?.focus();
  };

  const openMenu = () => {
    setActiveIndex(selectedIndex);
    setOpen(true);
  };

  const selectAt = (index) => {
    const project = projects[index];
    if (!project) return;
    onSelect(project.id);
    setActiveIndex(index);
    closeMenu();
  };

  const moveActive = (nextIndex) => {
    const count = projects.length;
    if (!count) return;
    setActiveIndex((nextIndex + count) % count);
  };

  useEffect(() => {
    if (!open) setActiveIndex(selectedIndex);
  }, [open, selectedIndex, selectedProject.id]);

  useEffect(() => {
    if (open) optionRefs.current[activeIndex]?.focus();
  }, [activeIndex, open]);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event) => {
      if (!ref.current?.contains(event.target)) closeMenu(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  return (
    <div className="project-switcher" ref={ref}>
      <button
        ref={triggerRef}
        className="project-switcher__button"
        type="button"
        aria-label={`Project selecionado: ${selectedProject.name}. Abrir lista`}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listboxId}
        onClick={() => {
          if (open) closeMenu();
          else openMenu();
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            openMenu();
          } else if (event.key === "Escape" && open) {
            event.preventDefault();
            closeMenu();
          }
        }}
      >
        <span className="project-switcher__mark" aria-hidden="true">
          <BoundingBox size={18} weight="fill" />
        </span>
        <span className="project-switcher__copy">
          <span>Project</span>
          <strong>{selectedProject.name}</strong>
        </span>
        <CaretDown size={15} aria-hidden="true" />
      </button>
      <AnimatePresence>
        {open ? (
          <motion.div
            id={listboxId}
            className="project-switcher__menu"
            role="listbox"
            aria-label="Selecionar Project"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.18 }}
          >
            {projects.map((project, index) => (
              <button
                ref={(node) => {
                  optionRefs.current[index] = node;
                }}
                key={project.id}
                type="button"
                role="option"
                aria-selected={project.id === selectedProject.id}
                tabIndex={index === activeIndex ? 0 : -1}
                onClick={() => selectAt(index)}
                onKeyDown={(event) => {
                  if (event.key === "ArrowDown") {
                    event.preventDefault();
                    moveActive(activeIndex + 1);
                  } else if (event.key === "ArrowUp") {
                    event.preventDefault();
                    moveActive(activeIndex - 1);
                  } else if (event.key === "Home") {
                    event.preventDefault();
                    moveActive(0);
                  } else if (event.key === "End") {
                    event.preventDefault();
                    moveActive(projects.length - 1);
                  } else if (
                    event.key === "Enter"
                    || event.key === " "
                    || event.key === "Space"
                    || event.key === "Spacebar"
                    || event.code === "Space"
                  ) {
                    event.preventDefault();
                    selectAt(activeIndex);
                  } else if (event.key === "Escape") {
                    event.preventDefault();
                    event.stopPropagation();
                    closeMenu();
                  } else if (event.key === "Tab") {
                    closeMenu(false);
                  }
                }}
              >
                <span>{project.name}</span>
                <small>{project.study}</small>
              </button>
            ))}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

function ContextInspector({ project, activeStudy, onClose }) {
  return (
    <motion.aside
      className="context-inspector"
      aria-label="Inspetor de contexto"
      initial={{ opacity: 0, x: 18 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 18 }}
      transition={{ duration: 0.2 }}
    >
      <header>
        <div>
          <span className="section-label">Contexto atual</span>
          <h2>{project.name}</h2>
        </div>
        <button type="button" className="icon-button" aria-label="Fechar inspetor" onClick={onClose}>
          <X size={18} aria-hidden="true" />
        </button>
      </header>
      <dl>
        <div>
          <dt>Project</dt>
          <dd>{project.id}</dd>
        </div>
        <div>
          <dt>Study</dt>
          <dd>{project.study}</dd>
        </div>
        <div>
          <dt>Scenario</dt>
          <dd className="mono">{activeStudy?.scenario ?? "Não compilado neste stub"}</dd>
        </div>
        <div>
          <dt>Data</dt>
          <dd>23 jul 2026, America/Asuncion</dd>
        </div>
      </dl>
      <p className="inspector-boundary">
        Project organiza um escopo lógico. Não representa uma pasta do filesystem nem uma Workspace.
      </p>
    </motion.aside>
  );
}

export function AppShell({
  children,
  route,
  linkProps,
  projects,
  selectedProject,
  activeStudy,
  onSelectProject,
  chat,
}) {
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const reduceMotion = useReducedMotion();

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Pular para o conteúdo
      </a>
      <aside className="left-rail" aria-label="Navegação principal">
        <a {...linkProps("/")} className="brand-mark" aria-label="Spatial Trace, Lab">
          <span aria-hidden="true">E</span>
        </a>
        <nav className="rail-nav">
          <NavItems route={route} linkProps={linkProps} />
        </nav>
        <button
          className="rail-context-button"
          type="button"
          aria-label="Abrir inspetor de contexto"
          onClick={() => setInspectorOpen(true)}
        >
          <SidebarSimple size={20} aria-hidden="true" />
          <span>Contexto</span>
        </button>
      </aside>

      <div className="shell-body">
        <header className="topbar">
          <ProjectSwitcher
            projects={projects}
            selectedProject={selectedProject}
            onSelect={onSelectProject}
          />
          <div className="topbar__boundary" role="note">
            <Info size={16} aria-hidden="true" />
            <span>{DEMO_NOTICE}</span>
          </div>
          <button
            className="context-button"
            type="button"
            onClick={() => setInspectorOpen(true)}
          >
            <SidebarSimple size={17} aria-hidden="true" />
            Contexto
          </button>
        </header>

        <AnimatePresence mode="wait" initial={false}>
          <motion.main
            id="main-content"
            key={route}
            className="spatial-canvas"
            initial={reduceMotion ? false : { opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={reduceMotion ? undefined : { opacity: 0, x: -8 }}
            transition={{ duration: reduceMotion ? 0 : 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            {children}
          </motion.main>
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {inspectorOpen ? (
          <>
            <motion.button
              type="button"
              className="context-scrim"
              aria-label="Fechar inspetor"
              onClick={() => setInspectorOpen(false)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <ContextInspector
              project={selectedProject}
              activeStudy={activeStudy}
              onClose={() => setInspectorOpen(false)}
            />
          </>
        ) : null}
      </AnimatePresence>

      {chat}

      <nav className="mobile-nav" aria-label="Navegação principal">
        <NavItems route={route} linkProps={linkProps} mobile />
      </nav>
    </div>
  );
}
