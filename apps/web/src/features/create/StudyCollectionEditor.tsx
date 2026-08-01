import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button, Input } from "../../ui/primitives";
import type { StudyCollection, StudyItem } from "./createModel";

interface StudyCollectionEditorProps {
  title: string;
  collection: StudyCollection;
  items: StudyItem[];
  addLabel: string;
  placeholder: string;
  defaultOpen?: boolean;
  onAdd(collection: StudyCollection, name: string): void;
  onChange(collection: StudyCollection, id: string, name: string): void;
  onRemove(collection: StudyCollection, id: string): void;
}

export function StudyCollectionEditor({
  title,
  collection,
  items,
  addLabel,
  placeholder,
  defaultOpen = false,
  onAdd,
  onChange,
  onRemove,
}: StudyCollectionEditorProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <details
      className="create-collection"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>
        <span>{title}</span>
        <small>{items.length}</small>
      </summary>
      <div className="create-collection-body">
        {items.length ? (
          items.map((item, index) => (
            <div className="create-collection-row" key={item.id}>
              <Input
                aria-label={`${title} ${index + 1}`}
                autoComplete="off"
                name={`${collection}-${index + 1}`}
                value={item.name}
                onChange={(event) => onChange(collection, item.id, event.target.value)}
              />
              <Button
                variant="quiet"
                size="small"
                aria-label={`Remove ${title} ${index + 1}`}
                onClick={() => onRemove(collection, item.id)}
              >
                <Trash2 aria-hidden="true" size={13} />
              </Button>
            </div>
          ))
        ) : (
          <p className="create-collection-empty">Nenhum item nesta seção local.</p>
        )}
        <Button variant="quiet" size="small" onClick={() => onAdd(collection, placeholder)}>
          <Plus aria-hidden="true" size={13} />
          {addLabel}
        </Button>
      </div>
    </details>
  );
}
