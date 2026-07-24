# Command Deck design QA

Final audit date: 23 July 2026  
Prototype URL: `http://localhost:4303/#/lab`  
Audit target: isolated React UI stub in `03-command-deck`

## Outcome

Command Deck implements the four required operator routes, deterministic interactive states, fail-closed Admission behavior, explicit evidence limitations, responsive layouts, and an adaptive Chat without calling a provider or claiming production EvidRun behavior.

The design direction materially follows the requested cold graphite and silver console with one restrained cobalt accent, Phosphor object-semantic icons, compact stage diagrams, consistent radii, short motivated motion, and reduced-motion support. Product Design audit discipline materially changed the implementation by requiring rendered screenshot inspection, real browser interaction, responsive measurements, and fixes for context drift, scroll restoration, duplicate landmarks, accessible icon names, and inaccurate alternate-Project workflow labels.

final result: passed

## Final verification

| Gate | Result | Evidence |
| --- | --- | --- |
| Unit and interaction tests | Passed | `npm test`: 1 test file, 10 tests passed. |
| Production build | Passed | `npm run build`: Vite transformed 4,982 modules and prepared the Sites build. |
| Sites worker tests | Passed | `npm run test:sites`: 4 tests passed. |
| Runtime console | Passed | Connected Chrome logs contained Vite debug messages and the React DevTools information message, with no application error or warning. |
| Desktop overflow | Passed | At requested 1440x940, `scrollWidth` equaled `clientWidth` on audited routes. |
| Tablet overflow | Passed | At requested 834x1112, measured content was 819 px wide with no horizontal overflow. |
| Mobile overflow | Passed | At requested 390x844, measured content was 375 px wide with no horizontal overflow. |
| Landmark stability | Passed | Browser DOM inspection found exactly one `main` landmark after route transitions. |
| Browser history | Passed | Browser Back returned from Study to Projects with the expected route and content. |

## Fix verification

The independent follow-up audit in `independent-qa.md` was read in full. Its three P2 findings and the separately reported Runs lifecycle inconsistency were fixed and rechecked in a fresh Chrome tab against the final source state.

| Finding | Final browser verification | Automated coverage |
| --- | --- | --- |
| Runs lifecycle and terminal coherence | During the real Start transition, Evaluating showed Start disabled as `Stub Run em andamento`, Terminal unreached, no Evidence, and the pending-terminal copy. After the terminal callback, the same checks atomically changed to `Terminal completed`, `event-run-completed-001`, Evidence visible, and disabled `Run encerrada`. | Added tests for in-flight atomicity, completed terminal control state, and failed terminal semantics. |
| Failed preset contradicted its event track | Failed now leaves Running non-current, keeps Evaluating unreached, marks Terminal reached/current with `event-run-failed-001`, hides completed Evidence, and disables Start as `Run encerrada`. | A dedicated test asserts every one of these boundaries and that no Evaluation is invented. |
| Tablet navigation hid visual labels | At requested 834x1112, Lab, Projects, Study, and Runs were rendered as visible text beside their icons. Measured `clientWidth` and `scrollWidth` were both 819 px. | Existing stable-route coverage remains green; rendered verification is captured in screenshot 18. |
| Modal focus escaped and was not restored | Reverse traversal moved from the first field to Close, then wrapped from Close to Create. Forward traversal from Create wrapped to Close. Escape removed the dialog and restored focus to `Novo Project`. | Added a test for reverse wrapping, Escape closure, and trigger restoration. |
| Critical Chat and evidence type was 9 to 12 px | Computed styles for message labels/body, Activity, Tool Call/Result, tool payload, composer, event records, digests, and evidence refs are all 14 px on the audited desktop and mobile states. The mobile Chat still ends above primary navigation and has no horizontal overflow. | CSS source scan and rendered computed-style checks cover the affected selectors. |

Fresh gates after these changes:

- `npm test`: 10/10 passed.
- `npm run build`: passed; 4,982 modules transformed and Sites artifacts prepared.
- `npm run test:sites`: 4/4 passed.
- Chrome console: no application warning or error.

## Functional evidence

- Lab starts as the primary task and opens an adaptive compact composer.
- Empty send remains disabled, Shift+Enter keeps a newline, Enter submits, and focus returns to the composer.
- The deterministic Lab execution shows its original signal-sweep activity indicator, observable milestones, `read_text` Tool Call, local Tool Result, and bounded response.
- Success, empty, and failure modes are available through a state switcher.
- The neutral circular Chat grip supports a 350 ms hold preview and keyboard mappings for all four snap layouts.
- Chat draft, state, and layout persist across client-side route navigation.
- Projects keeps Project scope distinct from Workspace integration, updates a stage inspector, validates creation, and stores new Projects only in React state.
- Study keeps StudyRevision distinct from compiled RunSpecs and applies Admission per exact RunSpec.
- Rejected Admission fails closed, disables enqueue, and explains what must change without asserting human authority.
- Runs progresses through queued, preparing, running, evaluating, and terminal; Run, job, attempt, and AdmissionRecord keep distinct IDs.
- Pause is visibly disabled and marked unsupported.
- Evidence records a SubjectEnvelope digest while explicitly stating that the exact document is not persisted or exportable.
- Bundle v2 is described as intentional references only, non-portable, and non-replayable.
- Comparison uses directional arrows rather than a balance-scale icon and does not invent a winner.

## Screenshot evidence

Final or accepted screenshots:

- `qa/screenshots/01-lab-desktop-1440x940.jpg`: initial desktop Lab task and SubjectEnvelope boundary.
- `qa/screenshots/09-lab-mobile-390x844-after-fix.jpg`: corrected first mobile viewport after route-scroll fix.
- `qa/screenshots/10-chat-mobile-bottom-sheet-390x844.jpg`: mobile bottom sheet above primary navigation.
- `qa/screenshots/12-runs-mobile-390x844.jpg`: responsive Runs route and mobile command model.
- `qa/screenshots/13-projects-tablet-834x1112-final.jpg`: final tablet Projects workflow and inspector.
- `qa/screenshots/14-study-desktop-1440x940-final.jpg`: final desktop Study draft, matrix, and compile context for Release Integrity.
- `qa/screenshots/15-lab-completed-desktop-1440x940-final.jpg`: wide completed Lab Chat with Tool Call, local Tool Result, and response.
- `qa/screenshots/16-runs-completed-desktop-1440x940-final.jpg`: terminal Run with phase progression and Evidence entry point.
- `qa/screenshots/17-study-rejected-desktop-1440x940-final.jpg`: rejected per-RunSpec Admission with disabled enqueue and operational explanation.
- `qa/screenshots/18-projects-tablet-834x1112-nav-labels-fix.jpg`: tablet navigation with all four visual labels and no horizontal overflow.
- `qa/screenshots/19-project-modal-tablet-focus-fix.jpg`: corrected modal with visible initial focus; keyboard trap and focus restoration were verified interactively.
- `qa/screenshots/20-chat-mobile-390x844-14px-fix.jpg`: mobile Chat with 14 px functional copy above primary navigation.
- `qa/screenshots/21-runs-completed-desktop-lifecycle-type-fix.jpg`: coherent completed lifecycle, disabled terminal Start, completed event, and enlarged evidence type.
- `qa/screenshots/22-runs-failed-desktop-lifecycle-fix.jpg`: failed terminal event with Evaluating reserved and no completed Evidence.

Earlier captures with lower numbers remain as audit history. When a corrected `-final` or `-after-fix` file exists, it supersedes the earlier image for acceptance.

## Issues resolved during screenshot audit

| Priority | Issue | Final state |
| --- | --- | --- |
| P1 | Mobile route changes retained a prior vertical scroll offset. | Route changes reset scroll to 0; corrected mobile evidence captured. |
| P1 | Study and Runs could display a selected global Project inconsistent with their Release Integrity records. | Those routes reset and lock the Project switcher to Release Integrity. |
| P2 | Route motion briefly allowed duplicate main landmarks. | A single static main wraps the animated route content. |
| P2 | Tablet icon-first navigation needed explicit accessible naming. | Every compact icon link has an `aria-label` and title. |
| P2 | Alternate Project stages could imply canonical records not yet reached. | Stage state and inspector copy are derived from current demonstrative progress. |
| P2 | The first mobile capture began below the route header. | Scroll restoration was corrected and the route was recaptured. |
| P1 | Runs presets and the Start transition could disagree about the current phase, terminal event, Evidence, and Start availability. | Ready, loading, failed, and completed now derive coherent phase views; terminal commit is atomic; Start is disabled and relabeled throughout in-flight and terminal states. |
| P2 | Tablet navigation removed all four visible destination labels. | Labels remain visible until the mobile bottom-navigation breakpoint, with no tablet overflow. |
| P2 | Project modal focus could escape and Escape did not return focus to its trigger. | Tab and Shift+Tab wrap inside the modal; every close path restores focus to `Novo Project`. |
| P2 | Functional Chat, tool, event, and evidence copy used 9 to 12 px sizes. | Every affected functional selector now computes to at least 14 px on desktop and mobile. |

No unresolved P0, P1, or P2 issue remains in the audited prototype scope.

## Honest limitations

- This is a deterministic frontend prototype. It does not execute the EvidRun backend, provider, real queue, artifact storage, or CRL fixture.
- The connected Chrome session is the only live browser verified. Safari/WebKit, Firefox, physical devices, screen readers, and switch control were not tested.
- Visual contrast was inspected in rendered screenshots, but no automated contrast scanner or Lighthouse audit was run.
- Refresh resets React-only Project creation, Chat state, Study edits, and Run state.
- The exact SubjectEnvelope document is intentionally unavailable, so the shown digest does not make the bundle recomputable.
- No deployment or publication was performed.

Detailed steps and findings are recorded in `qa/flow.yaml` and `qa/manual-audit.md`.
