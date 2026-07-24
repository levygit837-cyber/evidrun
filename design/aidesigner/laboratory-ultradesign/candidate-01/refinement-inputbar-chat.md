# Laboratory refinement: InputBar and chat interaction

## Scope

Refine the existing Laboratory page without redesigning the EvidRun shell. Concentrate the quality
budget on the InputBar, the deterministic chat interaction cycle, the audit trail, tool chronology,
and consistent horizontal alignment.

## InputBar

- Treat the InputBar as the primary crafted object.
- Keep a medium height and a maximum width around 760 px.
- Use a white surface, one precise gray border, 10 px radius, restrained shadow, and a soft blue
  focus treatment.
- Center the InputBar horizontally and vertically in fresh state.
- Move it near the bottom in active state without a layout jump.
- Animate only transform and opacity and provide a reduced-motion fallback.
- Auto-grow the textarea to a sensible maximum.
- Enter sends and Shift+Enter adds a line.
- Implement disabled, ready, sending, and stop states.
- Provide anchored menus for context, approval mode, model, and reasoning.
- Current settings are `Ask before actions`, `deepseek-v4-flash`, and `reasoning: max`.
- Menus need selection marks, keyboard focus, Escape closing, outside-click closing, and
  `aria-expanded`.
- Approval options are `Ask before actions`, `Read-only`, and `Allow admitted tools`.
- Context emerges from behind the InputBar, supports item removal, and disappears when empty.

## Chat interaction cycle

- Preserve the exact first user message.
- Reveal history and transition the InputBar on first send.
- Start a deterministic local demonstration sequence.
- Start and conclude the available audit trail.
- Progress three tool calls in chronological order.
- Reveal a final Lab Agent draft.
- End live activity and return the InputBar to ready state.
- Label all simulated content as Demo.
- Reset cancels pending timers and returns to fresh state.
- Restoring a past session loads its messages and closes history.
- Session Context defaults closed.

## Live activity

- Replace static activity with an animated thin arc or three animated strokes.
- Keep activity inline after the latest event, not inside a card.
- Rotate through `organizando contexto`, `verificando referências`, and `sintetizando draft`.
- Use transform and opacity only.
- Reduced motion uses a stable glyph.

## Audit trail

- Use the label `Trilha de raciocínio auditável`.
- Implement an accessible disclosure with duration and running/concluded status.
- Keep `aria-expanded` synchronized.
- Show only audit information available to the product, never hidden chain-of-thought.
- Use a thin left rule and calm mono text, never a card.

## Tool group

- Use one chronological group with one continuous vertical rail.
- Calls are `search_repository`, `compile_subject`, and `inspect_run`.
- Each row shows status, duration, parameter summary, and result summary.
- Each row expands inline through an accessible disclosure.
- Tool statuses progress during the deterministic demo.
- Every execution is explicitly Demo data.

## Alignment

- Use one centered conversation column with maximum width around 760 px.
- Use a stable identity rail and content rail.
- Align user, agent, audit trail, tools, live activity, final response, and InputBar.
- Keep a 16 px horizontal rhythm and 24-32 px between semantic events.
- Avoid arbitrary right padding and alternating widths.

## Truthfulness and visual constraints

- Keep Laboratory active beside Create and Observability.
- Preserve the approved light shell and exact color tokens.
- Display `cliproxyapi-local` as provider.
- Mark sample Runs, Evals, tools, and artifacts as Demo data.
- Do not imply human authority, admission, runtime integration, or hidden reasoning.
- Do not use chat bubbles, a card feed, decorative gradients, glassmorphism, a dark IDE, emojis,
  giant pills, em dash, or en dash.
- Use semantic buttons, visible focus, useful ARIA labels, and practical hit areas.
- Keep desktop and mobile usable.
