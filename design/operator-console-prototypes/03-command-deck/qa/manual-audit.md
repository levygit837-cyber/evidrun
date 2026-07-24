# Command Deck manual audit

Audit date: 23 July 2026  
Target: local React prototype at `http://localhost:4303`  
Primary browser: connected Chrome session  
Scope: Lab, Projects, Study, Runs, adaptive Chat, desktop, tablet, and mobile layouts

## Result

The prototype is visually coherent, responsive at the three required viewports, and operationally clear enough for the intended technical operator. No open P0, P1, or P2 issue remains in the audited scope. All records are demonstrative, no provider call exists, and sensitive authority or evidence claims remain bounded.

This is a prototype audit, not a full WCAG conformance statement or production acceptance.

## Visual audit

| Check | Result | Evidence |
| --- | --- | --- |
| Graphite and silver visual system | Passed | Cold graphite base, neutral panels, silver text, one restrained cobalt family. |
| Icon system | Passed | Phosphor Icons only; no handcrafted SVG, emoji, Lucide, or balance-scale comparison icon. |
| Success semantics | Passed | Checks, labels, shape, and contrast communicate completion without green. |
| Density and hierarchy | Passed | A compact command rail, grouped stages, concise inspectors, and at most two persistent work zones keep the operator path legible. |
| Shape system | Passed | One compact radius family is used throughout; the grip alone is intentionally circular because it is an interaction affordance. |
| Motion | Passed | Navigation, disclosure, Chat layout, and status feedback use short transitions; reduced-motion CSS and `useReducedMotion` remove nonessential motion. |
| Content truthfulness | Passed | Illustrative records are marked Demonstração local or Stub local. No invented KPI, provider call, human authority, replay, portability, or artifact access is claimed. |

## Interaction audit

| Flow | Result | Observation |
| --- | --- | --- |
| Hash navigation and Back | Passed | Lab, Projects, Study, and Runs resolve to stable hashes. Browser Back returned to the previous route with one main landmark and no mixed content. |
| Composer | Passed | Empty send is disabled; Enter submits; Shift+Enter preserves a newline; focus returns to the composer. |
| Lab sequence | Passed | The custom signal sweep appears immediately. The deterministic sequence exposes observable milestones, read_text Tool Call, authorized local Tool Result, and bounded response copy. |
| Adaptive Chat | Passed | Dock, compact thread, wide inspection, three height choices, collapse, 350 ms hold preview, and keyboard snap alternatives are implemented. Chat state survives in-app navigation. |
| Project workflow | Passed | Project selection changes the bounded scope. Stage selection updates the adjacent inspector. Empty creation is rejected and a valid Project exists only in React state. |
| Admission | Passed | Rejected mode disables enqueue and explains the blocking capability or disclosure issue per exact RunSpec. Admitted mode does not claim human authority. |
| Run lifecycle | Passed | Start Stub Run progresses queued, preparing, running, evaluating, and terminal. Terminal state, terminal event, Evidence visibility, and Start availability change coherently; Run, job, attempt, and AdmissionRecord remain separate. Pause is visible but disabled and unsupported. |
| Evidence and comparison | Passed | Digest, references-only Bundle, non-portable/non-replayable limitations, and variant comparison are explicit. |

## Responsive audit

The Browser capability applied the requested viewport overrides. Chrome's content area can be narrower than the requested outer viewport when its vertical scrollbar is present; the comparison below uses the measured document content width.

| Requested viewport | Measured content width | Horizontal overflow | Key observation |
| --- | ---: | --- | --- |
| 1440x940 | 1425 or 1440 px by route | None | Command rail and dense evidence layout remain readable. |
| 834x1112 | 819 px | None | Projects workflow and inspector reflow without clipped controls. |
| 390x844 | 375 px | None | Bottom navigation remains available; Chat becomes a bottom sheet and stays above it. |

The mobile route-scroll regression was rechecked after the fix: navigation starts the destination at scroll top 0. The mobile Chat measurement placed its bottom at 770 px and the navigation top at 778 px, leaving a visible separation.

## Accessibility audit

Passed structural checks:

- One `main` landmark remains mounted during route transitions.
- Navigation has an accessible name and uses real hash links.
- Icon-only controls have explicit `aria-label` text; compact tablet navigation also has title hints.
- Project selection, revision selection, text fields, segmented decisions, and composer controls have programmatic names.
- Disabled controls expose native disabled state for empty send, rejected enqueue, and unsupported pause.
- Dynamic execution status uses a named status region and Chat updates use a polite live region.
- The grip exposes keyboard mappings for compact, half, tall, and full-thread states.
- Focus-visible styling is present for interactive controls.
- Project creation traps Tab and Shift+Tab inside the modal, closes with Escape, and restores focus to `Novo Project`.
- Reduced motion is honored.

Limits of this check:

- No screen-reader session, physical keyboard-only audit, switch-control audit, or physical touch-device test was run.
- No automated WCAG contrast scanner or Lighthouse accessibility score was used. Contrast was inspected visually in the rendered screenshots.
- Chrome was the only live browser in scope; Safari, Firefox, and WebKit behavior remains unverified.

## Issues found and fixed

| Priority | Finding | Resolution |
| --- | --- | --- |
| P1 | Mobile route navigation could retain the previous page's vertical scroll position. | The hash-route hook now resets document and body scroll on every route change. |
| P1 | Study and Runs could visually inherit a Project selected on Projects even though their stub data belongs to Release Integrity. | Those routes now reset and lock the global Project context to Release Integrity. |
| P2 | Route transitions could briefly mount more than one `main` landmark. | A single persistent `main` now contains the keyed animated route surface. |
| P2 | Tablet icon-first navigation did not expose explicit names and hints on every compact item. | Each icon-first link now carries an explicit accessible label and title. |
| P2 | Workflow stage labels and inspector copy could imply records that do not exist for an alternate Project. | Stage state and inspector copy are derived from the selected Project's actual demonstrative progress. |
| P2 | Early mobile evidence was captured after a prior route scroll and did not show the intended first viewport. | The scroll behavior was fixed and the corrected screenshot was captured as `09-lab-mobile-390x844-after-fix.jpg`. |
| P1 | Runs could expose terminal copy while another phase remained current, omit the failed terminal event, or re-enable Start during terminal commit. | Phase views are coherent per preset, terminal commit is atomic, and Start remains disabled and relabeled in-flight and after terminal. |
| P2 | Tablet navigation hid visible route labels. | All four labels remain visible until the mobile breakpoint without horizontal overflow. |
| P2 | Modal keyboard focus escaped and was not restored. | Focus wraps in both directions and every close path restores `Novo Project`. |
| P2 | Functional Chat and evidence text was set between 9 and 12 px. | Message, activity, tool, composer, event, digest, and evidence reference text now computes to at least 14 px. |

## Residual limitations

- The backend is intentionally a deterministic UI stub. Refreshing the page resets created Projects, drafts, Chat state, and Run state.
- Browser evidence covers Chrome only. Physical-device, Safari/WebKit, Firefox, and assistive-technology testing remain outside this prototype pass.
- The exact SubjectEnvelope document is intentionally not persisted or exportable, so the displayed digest cannot make a bundle recomputable.
- Bundle entries are intentional references, not proof of storage access, portability, restore, replay, or every file observed by a real runtime.
- The Chat is an overlay by design. Lower page content remains reachable by scrolling, but the overlay can visually cover it while open.
