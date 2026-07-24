import {
  Flask,
  FolderOpen,
  Notebook,
  PlayCircle,
  SealCheck,
} from "@phosphor-icons/react";

const destinations = [
  { path: "/", label: "Lab", icon: Flask },
  { path: "/projects", label: "Projects", icon: FolderOpen },
  { path: "/study", label: "Study", icon: Notebook },
  { path: "/runs", label: "Runs", icon: PlayCircle },
];

function RouteLink({ destination, currentPath, onNavigate, mobile = false }) {
  const Icon = destination.icon;
  const active = currentPath === destination.path;

  return (
    <a
      className={`nav-destination${active ? " is-active" : ""}`}
      href={destination.path}
      aria-current={active ? "page" : undefined}
      aria-label={destination.label}
      title={destination.label}
      onClick={(event) => {
        if (
          event.button !== 0 ||
          event.metaKey ||
          event.ctrlKey ||
          event.shiftKey ||
          event.altKey
        ) {
          return;
        }
        event.preventDefault();
        onNavigate(destination.path);
      }}
    >
      <Icon aria-hidden="true" size={mobile ? 22 : 25} weight={active ? "fill" : "regular"} />
      <span>{destination.label}</span>
    </a>
  );
}

export function PrimaryNavRail({ currentPath, onNavigate }) {
  return (
    <>
      <aside className="primary-rail" aria-label="Navegação principal">
        <div className="product-mark" aria-label="EvidRun">
          <SealCheck aria-hidden="true" size={28} weight="duotone" />
        </div>
        <nav>
          {destinations.map((destination) => (
            <RouteLink
              key={destination.path}
              destination={destination}
              currentPath={currentPath}
              onNavigate={onNavigate}
            />
          ))}
        </nav>
        <div className="rail-foot" aria-label="Protótipo local">
          ER
        </div>
      </aside>

      <nav className="mobile-navigation" aria-label="Navegação principal">
        {destinations.map((destination) => (
          <RouteLink
            key={destination.path}
            destination={destination}
            currentPath={currentPath}
            onNavigate={onNavigate}
            mobile
          />
        ))}
      </nav>
    </>
  );
}
