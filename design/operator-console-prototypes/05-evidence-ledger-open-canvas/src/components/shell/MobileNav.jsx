import { mobileNavigation } from "./Sidebar.jsx";

export function MobileNav({ path, navigate }) {
  return (
    <nav className="mobile-nav" aria-label="Navegação móvel">
      {mobileNavigation.map(({ path: itemPath, label, icon: Icon }) => (
        <button
          type="button"
          key={itemPath}
          className={path === itemPath ? "is-active" : ""}
          aria-current={path === itemPath ? "page" : undefined}
          aria-label={label}
          onClick={() => navigate(itemPath)}
        >
          <Icon size={22} weight={path === itemPath ? "fill" : "regular"} aria-hidden="true" />
          <span>{label === "Study & Admission" ? "Study" : label === "Runs & Evidence" ? "Runs" : label}</span>
        </button>
      ))}
    </nav>
  );
}
