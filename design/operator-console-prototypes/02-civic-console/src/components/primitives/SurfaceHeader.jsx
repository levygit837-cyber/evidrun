export function SurfaceHeader({ eyebrow, title, description, action, as: Tag = "header" }) {
  return (
    <Tag className="surface-header">
      <div>
        {eyebrow ? <p className="surface-eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        {description ? <p className="surface-description">{description}</p> : null}
      </div>
      {action ? <div className="surface-header-action">{action}</div> : null}
    </Tag>
  );
}
