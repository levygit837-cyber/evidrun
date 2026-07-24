# Isolated Build Brief: Evidence Ledger Open Canvas

01. You own only this workspace: `05-evidence-ledger-open-canvas`.
02. Do not inspect sibling prototype directories.
03. Do not reuse code or design decisions from any new variant.
04. This is the fifth project and the selected existing Image-to-Code trial.
05. Its visual source is the six images in `reference/`.
06. Open and inspect every reference image before planning.
07. The images are a visual source, not a requirement to preserve their mistakes.
08. Preserve the system, hierarchy, and tone while improving usability.
09. Read the repository `AGENTS.md` before edits.
10. Read the complete Product Design `image-to-code` skill.
11. Read the complete Product Design `design-qa` skill.
12. Read the complete Product Design `audit` skill.
13. Read the complete `design-taste-frontend` skill.
14. Use at least Product Design `image-to-code` and `design-taste-frontend` materially.
15. State a one-line Design Read before implementation.
16. Treat `design-taste-frontend` as anti-slop advice, not dense-app architecture.
17. Keep all code, assets, tests, and reports inside this workspace.
18. Do not edit contracts, backend, DTOs, Electron, or `apps/web`.
19. Do not call providers or persist credentials.
20. The backend is an explicit deterministic local stub.

## Visual source mapping

21. `01-home-first-use.png` defines first-use Lab composition.
22. `02-home-active-chat.png` defines Chat and evidence context.
23. `03-projects.png` defines Project workflow framing.
24. `04-studies-admission.png` defines Study matrix and Admission preflight.
25. `05-run-completed.png` defines terminal Run and Bundle disclosure.
26. `06-run-live-chat.png` defines a live Run with lateral Chat.
27. Match the cold paper-white, ink, and restrained cobalt system.
28. Match typography hierarchy and generous canvas proportions.
29. Match the ~212px sidebar concept on desktop.
30. Use at most two content zones after the sidebar.
31. Maintain 15-16px readable body copy.
32. Keep buttons content-width, about 36-40px tall.
33. Do not reproduce cramped labels or tiny mono prose.
34. Do not reproduce long full-width button rows.
35. Do not reproduce three persistent narrow columns.
36. Do not add green decorative database icons.
37. Do not use a balance-scale icon for Comparison.
38. Use Phosphor Icons only.
39. Do not use Lucide, emoji, custom SVG paths, or text glyph icons.
40. Keep technical IDs secondary to human-readable labels.

## Product outcome

41. Help an operator begin or resume a Study, inspect Admission, execute a stub Run, and understand evidence.
42. Required routes: Lab, Projects, Study, Runs.
43. Routes must work with keyboard, pointer, and history.
44. First use and returning Lab states must both be demonstrable.
45. Do not frame command input as eliminating Chat.
46. Chat and intent input are complementary.
47. Chat is contextual and can discuss Project, Study, Run, and evidence.
48. Chat remains outside SubjectEnvelope.
49. Lab Agent creates drafts only.
50. Human acceptance is not simulated as agent authority.

## Domain truth

51. Project is a logical evaluation scope.
52. Workspace is a separate local data boundary.
53. StudyRevision is authored and versioned.
54. RunSpec is compiled from an accepted revision.
55. AdmissionRecord is a pre-run decision for an exact RunSpec.
56. No Run exists before an admitted AdmissionRecord.
57. Run, job, and attempt remain separate.
58. Events are factual within the selected stub state.
59. SubjectEnvelope excludes Chat.
60. Bundle integrity does not imply portability or replay.
61. Label every noncanonical runtime state `Demonstração local`.
62. Do not claim the demo wrote repository or backend records.

## Demonstration data

63. Preserve Project `Context Reliability Lab`.
64. Preserve Study `Preservação da causa-raiz em logs longos`.
65. Preserve canonical fixture naming `CRL-CTX-002` only where shown as recorded reference.
66. Preserve variants `head-truncation` and `tail-preservation`.
67. Preserve known comparison 0.0 versus 1.0 only as fixture data.
68. Use date 23 July 2026 and America/Asuncion.
69. For tool-call demonstrations, use a separate clearly illustrative Run context.
70. Never claim CRL emitted tool events; its manifest has no tools.

## Lab agent interaction

71. Implement a working local composer.
72. Empty send must be disabled.
73. Enter sends and Shift+Enter inserts a newline.
74. Sending starts a deterministic agent state sequence.
75. Show a custom spinner directly above the input.
76. Build the spinner as a cobalt ledger cursor or resolving trace.
77. Do not use a generic circular border spinner.
78. Render User, Agent, Thinking Block, Tool Call, and Tool Result.
79. Title the Thinking Block `Atividade observável`.
80. Show only observable progress, never private reasoning.
81. Tool Call uses `read_text` only in illustrative authorized context.
82. Tool Result shows a short stub excerpt and disclosure.
83. Support idle, running, success, and failure switches.
84. Preserve focus and announce state changes accessibly.
85. Keep Chat copy in pt-BR and domain names exact.

## Adaptive lateral Chat

86. Chat begins as a small lateral dock.
87. Clicking reveals a compact thread.
88. Provide a wider expanded thread mode.
89. Let the user choose compact, half, or tall height.
90. Provide collapse and close as distinct controls.
91. Add a circular neutral grip for snap interaction.
92. Holding the grip for roughly 350ms reveals docking previews.
93. Preview states show the future panel geometry.
94. Pointer movement selects compact, half, tall, or full-thread.
95. Release commits the highlighted state.
96. Do not implement arbitrary free positioning.
97. Provide keyboard snap controls.
98. Mobile transforms Chat into a bottom sheet.
99. Bottom sheet must coexist with bottom navigation.
100. Thread state persists during local route changes.

## Projects route

101. Implement the reference's workflow relationship without turning each object into dense text.
102. Use lanes or grouped stages with minimal essential connectors.
103. Selecting a node updates a concise inspector.
104. Show StudyRevision branching into two RunSpecs.
105. Show one Admission and Run per RunSpec.
106. Show evaluations converging into Comparison.
107. Workspace appears separately and stays integration pending.
108. Provide at least three stub Projects in the switcher.
109. Provide a validated create-project dialog.

## Study route

110. Implement revision selection and draft editing.
111. Visualize `scenario x variants x repetitions`.
112. Show compile preview.
113. Show one preflight per RunSpec.
114. Demonstrate rejected and admitted Admission states.
115. Enqueue remains disabled when rejected.
116. Explain mismatch in direct operational language.
117. Create New Revision changes only local React state.
118. Do not claim plain-text human acceptance.

## Runs route

119. Implement Start Stub Run and deterministic phase progression.
120. Phases: queued, preparing, running, evaluating, terminal.
121. Show job and attempt separately.
122. Provide loading, failed, and completed state presets.
123. Completed CRL view has exactly the factual nine-event story if represented.
124. Live tool-call view is explicitly illustrative and separate.
125. Show SubjectEnvelope digest limitation.
126. Show Bundle v3 `references_only`, `portable=false`, `replayable=false`.
127. Integrity is verified only after export in the stub flow.
128. Do not expose active pause/resume.
129. Use a comparison visual without balance scales.

## Engineering

130. Use React 19 and Vite from the provided Product Design template.
131. Use Tailwind CSS v4 with `@tailwindcss/vite`.
132. Use Motion from `motion/react`.
133. Use `@phosphor-icons/react`.
134. Organize components by shell, routes, chat, agent blocks, and primitives.
135. Keep mock data in a dedicated module.
136. Use a reducer for the run and agent state machines.
137. Avoid a monolithic App component.
138. Do not import from sibling prototypes.
139. Use semantic HTML, accessible names, visible focus, and live regions.
140. Prevent horizontal overflow at 1440x940, 834x1112, and 390x844.
141. Respect reduced motion.
142. Keep transitions between 160ms and 260ms.

## Verification and deliverables

143. Add Vitest and React Testing Library.
144. Test navigation, first-use switch, composer, agent blocks, Chat snaps, Admission gating, and Run states.
145. Add `qa/flow.yaml` with deterministic browser actions and expected observations.
146. Add `qa/manual-audit.md` with functional, responsive, visual, and accessibility findings.
147. Run install, tests, build, and `npm run test:sites`.
148. Start the app on port 4305.
149. Use real browser control for runtime QA when available.
150. Capture desktop and mobile screenshots under `qa/screenshots/`.
151. Compare source and implementation at matching viewports.
152. Put source and implementation together in the same comparison input.
153. Fix every P0/P1/P2 difference that harms hierarchy or use.
154. Re-capture after fixes.
155. Save `design-qa.md` with source paths, implementation paths, viewports, findings, history, and final result.
156. `final result: passed` requires browser evidence and no actionable P0/P1/P2.
157. Record P3 polish separately.
158. Do not deploy or publish.
159. Keep the local server running if practical.
160. Handoff with changed files, commands, screenshots, and honest residual limits.
