# Isolated Build Brief: Spatial Trace

01. You own only this workspace: `04-spatial-trace`.
02. Do not inspect sibling prototype directories.
03. Do not reuse another trial's code, tokens, images, or layout.
04. This is an autonomous, no-image design trial.
05. Do not open any generated mock or existing Evidence Ledger image.
06. Read the repository `AGENTS.md` before editing.
07. Read the full Product Design `get-context` skill.
08. Read the full Product Design `audit` skill.
09. Read the full `design-taste-frontend` skill.
10. Use at least Product Design `audit` and `design-taste-frontend` materially.
11. State a one-line Design Read and design dials before code.
12. Treat the anti-slop rules as guidance, not app architecture.
13. Build a fast, isolated React prototype.
14. Keep every source, asset, test, and QA artifact in this workspace.
15. Do not edit backend, contracts, DTOs, Electron, or `apps/web`.
16. Do not call a real provider or store credentials.
17. All data is deterministic local stub data.
18. Label stub data so it cannot be mistaken for canonical evidence.
19. No hidden implementation may claim human authority.
20. Do not expose private reasoning.

## Product outcome

21. Let an operator move from Project context to Study, Admission, Run, and evidence without losing place.
22. Required routes: Lab, Projects, Study, Runs.
23. Navigation must work by keyboard, pointer, and browser history.
24. The core flow must be demonstrable end to end with mock backend state.
25. The first viewport should answer current scope, active workflow, and next action.
26. Simplify information before adding containers.
27. Avoid text walls, long row stacks, and decorative reference IDs.
28. Use diagrams only when they clarify real relationships.
29. Use direct labels in pt-BR with technical domain names preserved.
30. No fake KPI dashboards.

## Autonomous visual direction

31. Create a direction named `Spatial Trace`.
32. Use a cold porcelain background and deep charcoal foreground.
33. Use one restrained vermilion accent.
34. Supporting neutrals should be silver, smoke, and cool gray.
35. Do not use blue, purple, or green as decorative accents.
36. Success should rely on checks, labels, and filled/outlined geometry.
37. Use one sans family and a mono only for identifiers.
38. Use a single icon family: Phosphor Icons.
39. Do not use Lucide, emoji, handcrafted SVG, or text glyph icons.
40. Use a project-boundary icon for Projects.
41. Use a notebook/file icon for Study.
42. Use a gate/shield icon for Admission.
43. Use a pulse/play icon for Runs.
44. Use archive/fingerprint/file-lock for evidence.
45. Do not use balance scales anywhere.
46. Database icons stay neutral, never green.
47. Do not imitate a generic admin dashboard.
48. Do not use equal card grids as the main structure.
49. Use spatial grouping and a trace path as the visual signature.
50. The trace must map real workflow relationships.
51. Avoid excessive hairlines; only draw essential connectors.
52. Buttons remain content-sized, never full-width on desktop.
53. Use a consistent sharp-soft radius rule, documented in CSS tokens.
54. Motion duration should sit around 180-250ms.
55. Motion communicates continuity when navigating stages.
56. Respect `prefers-reduced-motion`.

## Shell and information architecture

57. Use a thin left rail and a broad spatial canvas.
58. Keep the rail narrow enough that the canvas remains comfortable.
59. Provide a clearly visible project switcher without copying ChatGPT.
60. Lab is the Home route.
61. Projects is a map of bounded project scopes and their current trace.
62. Study is a revision and Admission workspace.
63. Runs is the live/terminal execution trace and evidence inspector.
64. A compact context inspector may appear on demand, not permanently.
65. On mobile, use a bottom navigation and full-width content.
66. Avoid more than two persistent content zones after navigation.
67. Keep Project separate from Workspace.
68. Keep StudyRevision separate from RunSpec.
69. Keep AdmissionRecord separate from Run.
70. Keep Run separate from job and attempt.

## Demonstration context

71. Use Project `Retrieval Quality`.
72. Use Study `Respostas com fontes insuficientes`.
73. Use scenario `source-grounding-check`.
74. Use variants `direct-answer` and `evidence-first`.
75. Use one repetition for each variant.
76. Use 23 July 2026 in America/Asuncion.
77. Use clearly stubbed local IDs.
78. Do not reuse CRL IDs or claim a canonical run.
79. Project workflow should visualize intent, revision, RunSpecs, Admissions, Runs, evaluations, and comparison.
80. Only the selected stage should show detailed metadata.

## Lab agent interaction

81. Build a functional local composer.
82. Sending starts a deterministic agent activity sequence.
83. Render a custom spinner above the input while work is active.
84. The spinner should feel like a trace being resolved.
85. Do not use a generic CSS border circle.
86. Render User, Agent, Thinking Block, Tool Call, and Tool Result.
87. Thinking Block title is `Atividade observável`.
88. Thinking Block shows only factual progress states.
89. Tool Call uses `read_text`.
90. Tool Result shows a short authorized local excerpt.
91. Mark Tool Call and Tool Result as stubbed demonstration.
92. Agent response must not claim it modified or executed real resources.
93. Chat cannot enter SubjectEnvelope.
94. Support idle, running, success, and failure states.
95. Disable sending empty text.
96. Support Enter and Shift+Enter correctly.
97. Announce agent state changes in an accessible live region.
98. Avoid auto-scrolling that steals user position.

## Adaptive lateral Chat

99. Chat starts as a compact lateral strip or dock.
100. A click reveals a small thread surface.
101. Expand supports wider thread inspection.
102. Height supports compact, half, and tall states.
103. Provide close and collapse separately.
104. Add a circular grip as a resize/snap affordance.
105. Holding the grip for about 350ms reveals snap previews.
106. Preview zones must show the future Chat geometry.
107. Pointer movement selects compact, half, tall, or full-thread.
108. Release applies the selected geometry.
109. Do not implement uncontrolled free dragging.
110. Keyboard users need explicit snap buttons.
111. Mobile uses an accessible bottom sheet.
112. The sheet must leave the bottom navigation usable.
113. Preserve the stub thread while changing routes.

## Projects route

114. Show project boundaries as spatial regions or lanes.
115. Show current trace position and next meaningful action.
116. Selecting a Project updates the trace without a full reload.
117. Provide at least three realistic stub Projects.
118. Include a create-project dialog with labels and validation.
119. Distinguish local Workspace linkage as unavailable integration.
120. Do not define a Project as a filesystem folder.

## Study route

121. Show revision state and compile preview.
122. Visualize `scenario x variants x repetitions` without a table wall.
123. Show one Admission preflight per RunSpec.
124. Provide a rejected issue and an admitted demonstration.
125. Enqueue remains disabled for rejected Admission.
126. Explain mismatch with requested and supported values.
127. Allow a local draft revision to correct the mismatch.
128. Never record a human acceptance through plain text.

## Runs route

129. Start Stub Run triggers queued, preparing, running, evaluating, terminal.
130. Show job and attempt as operational children of Run.
131. Use a trace path for event phases, not a dense event table.
132. Provide loading, failed, and completed state switches.
133. Show `subject.invoked`, `tool.called`, `tool.completed`, `subject.responded` only in the stub run that supports them.
134. Do not claim these events for CRL.
135. Show SubjectEnvelope digest limitation honestly.
136. Show Bundle disclosure as references-only, portable false, replayable false.
137. Comparison uses spatial juxtaposition, not a balance-scale icon.
138. Pause/resume controls are absent or visibly unsupported.

## Engineering

139. Use React 19 and Vite from the provided template.
140. Use Tailwind CSS v4 and `@tailwindcss/vite`.
141. Use Motion from `motion/react` for motivated transitions.
142. Use `@phosphor-icons/react` for every UI icon.
143. Create maintainable components and focused hooks.
144. Keep stub data in its own module.
145. Prefer a reducer for the run state machine.
146. Avoid one giant App component.
147. Do not import any sibling workspace file.
148. Use semantic HTML, accessible names, and visible focus.
149. Verify contrast and active/disabled states.
150. Prevent horizontal overflow at desktop, tablet, and mobile.

## Verification and deliverables

151. Add Vitest and React Testing Library.
152. Test navigation, create Project, Admission gating, run sequence, agent blocks, and Chat snaps.
153. Add `qa/flow.yaml` with deterministic browser actions and observations.
154. Add `qa/manual-audit.md` covering functionality, responsiveness, visual quality, and accessibility.
155. Run install, tests, build, and `npm run test:sites`.
156. Start the app on port 4304.
157. Use real browser control for QA if available.
158. Save desktop and mobile screenshots under `qa/screenshots/`.
159. Inspect them and repair P0/P1/P2 findings.
160. Re-capture after fixes.
161. Save `design-qa.md` with evidence and exact final result.
162. Do not claim passed without browser-rendered evidence.
163. Do not deploy or publish.
164. Handoff with changed files, commands, screenshots, and remaining limits.
