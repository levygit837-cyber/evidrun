# Isolated Build Brief: Carbon Rhythm

01. You own only this workspace: `01-carbon-rhythm`.
02. Do not inspect sibling prototype directories.
03. Do not reuse code, tokens, screenshots, or decisions from another variant.
04. This is an image-guided trial.
05. The source image will be `reference/source.png`.
06. Open and inspect the source image before planning.
07. Also read `reference/generation-notes.md` and `reference/image-audit.md` when present.
08. The image is a reference and base, not a literal implementation contract.
09. Correct documented image problems during implementation.
10. Do not generate replacement images for small errors.
11. Read repository `AGENTS.md` before making changes.
12. Read the complete Product Design `image-to-code` skill.
13. Read the complete Product Design `design-qa` skill.
14. Read the complete Product Design `audit` skill.
15. Read the complete `design-taste-frontend` skill.
16. Use at least `image-to-code` and `design-taste-frontend` materially.
17. Keep every source, asset, test, and report in this workspace.
18. Do not edit contracts, backend, DTOs, Electron, or `apps/web`.
19. Do not call a provider or store credentials.
20. The backend is a deterministic UI stub labeled as such.

## Product outcome

21. Enable an operator to move from Project context through Study, Admission, Run, and evidence.
22. Required routes: Lab, Projects, Study, Runs.
23. Routes work with pointer, keyboard, and browser history.
24. The primary flow is functional end to end with local React state.
25. The first viewport shows current scope, workflow state, and next action.
26. Simplify data before adding UI containers.
27. Avoid long lists, repetitive abstract IDs, and full-row controls.
28. Use diagrams only for true relationships.
29. Keep copy concise and mainly pt-BR.
30. Preserve technical names such as RunSpec and AdmissionRecord.

## Visual direction

31. Direction name is `Carbon Rhythm`.
32. Preserve deep carbon and graphite surfaces.
33. Preserve warm off-white text and restrained oxidized orange accent.
34. Use silver-gray for structure.
35. Do not add green database or success decoration.
36. Do not introduce purple, blue glow, or rainbow statuses.
37. Use shape, check, X, labels, and contrast for state.
38. Use one refined sans and mono only for IDs.
39. Use Phosphor Icons as the only icon family.
40. Do not use Lucide, emoji, custom SVG paths, or text glyph icons.
41. Project icon is folder or bounding box.
42. Study icon is notebook or file-search.
43. Admission icon is shield or gate.
44. Run icon is play or pulse.
45. Evidence icon is fingerprint, archive, or file-lock.
46. Tool read uses file-text or terminal-window.
47. Never use balance scales for comparison.
48. Database icons are neutral silver.
49. Avoid glassmorphism and AI visual effects.
50. Avoid equal card rows and nested card stacks.
51. Use at most two content zones below the command rail.
52. Body copy should be 15-16px.
53. Buttons are content-width and about 36-40px tall.
54. Use one 10-12px radius system.
55. Transitions last roughly 170-240ms.
56. Honor `prefers-reduced-motion`.

## Shell

57. Use the image's compact top command rail.
58. Include EvidRun, Lab, Projects, Study, and Runs.
59. Include a compact Project switcher.
60. Lab is the Home route.
61. Do not introduce a wide ChatGPT-like sidebar.
62. Preserve a broad, calm main canvas.
63. Keep system readiness in one concise disclosure.
64. Use a lateral adaptive Chat dock.
65. Mobile uses a bottom navigation.
66. Mobile content is one column with readable padding.
67. Keep Project distinct from Workspace.
68. Keep StudyRevision distinct from RunSpec.
69. Keep AdmissionRecord distinct from Run.
70. Keep Run distinct from job and attempt.

## Stub data

71. Project: `Release Integrity`.
72. Study: `Diagnóstico de regressões após deploy`.
73. Scenario: `deployment-log-trace`.
74. Variants: `summary-first` and `evidence-first`.
75. One repetition per variant.
76. Date: 23 July 2026.
77. Timezone: America/Asuncion.
78. Use readable local IDs marked as stub data.
79. Do not reuse CRL fixture IDs.
80. Do not claim a canonical run occurred.

## Lab interaction

81. Implement a working composer.
82. Empty send is disabled.
83. Enter sends; Shift+Enter inserts a newline.
84. Sending starts a deterministic activity sequence.
85. Show a custom Carbon Rhythm spinner directly above the composer.
86. The spinner is not a generic circular border spinner.
87. Sequence: preparing context, reading authorized input, tool call, tool result, response captured.
88. Render a User message.
89. Render an Agent response.
90. Render a collapsible Thinking Block titled `Atividade observável`.
91. Never reveal chain-of-thought or hidden grader content.
92. Render Tool Call `read_text`.
93. Render Tool Result with a short authorized stub excerpt.
94. Mark the tool blocks as local demonstration.
95. Provide idle, running, success, and failure state presets.
96. Announce state changes in an accessible live region.
97. Preserve sensible focus after send.
98. Avoid forced scroll that steals the user's reading position.

## Adaptive Chat

99. Chat begins as a small lateral dock.
100. Clicking opens a compact thread view.
101. A separate action expands to a wider thread view.
102. Height supports compact, half, and tall states.
103. Collapse and close are separate controls.
104. A circular neutral grip controls snap preview.
105. Holding the grip for about 350ms reveals preview zones.
106. Preview zones show future compact, half, tall, and full-thread geometry.
107. Pointer movement highlights a zone.
108. Releasing commits the highlighted layout.
109. Do not implement uncontrolled free dragging.
110. Provide explicit keyboard snap controls.
111. Mobile Chat becomes a bottom sheet.
112. The sheet must not cover the bottom navigation.
113. Preserve the thread across route changes.

## Projects

114. Represent Project as a bounded logical scope.
115. Represent Workspace as a separate local integration concept.
116. Show the Project lifecycle as a compact rhythm/trace workflow.
117. Stages include intent, revision, Admission, Run, evaluation, and comparison.
118. Selecting a stage updates a concise adjacent inspector.
119. Provide at least three realistic stub Projects.
120. Implement a create-project dialog with validation.
121. Created Projects live only in local React state.
122. Workspace linking remains Integration pending.

## Study

123. Implement revision selection and a draft editor stub.
124. Show `scenario x variants x repetitions` visually.
125. Include compile preview.
126. Include one Admission preflight per RunSpec.
127. Provide admitted and rejected demonstration states.
128. Enqueue remains disabled for rejected Admission.
129. Explain the issue in direct operational language.
130. A new revision can correct the issue in local state.
131. Never claim an agent supplied human acceptance.

## Runs

132. Implement Start Stub Run.
133. Deterministic phases: queued, preparing, running, evaluating, terminal.
134. Show job and attempt separately.
135. Show events through a compact staged trace, not a dense table.
136. Tool events appear only in this explicitly illustrative stub.
137. Provide loading, failed, and completed state presets.
138. Show SubjectEnvelope digest as recorded but not automatically exportable.
139. Show Bundle as references-only, non-portable, and non-replayable.
140. Do not expose functional pause/resume.
141. Comparison uses juxtaposition, never balance scales.

## Engineering

142. Use React 19 and the provided Vite template.
143. Use Tailwind CSS v4 with `@tailwindcss/vite`.
144. Use Motion from `motion/react`.
145. Use `@phosphor-icons/react`.
146. Split shell, routes, Chat, agent blocks, and primitives into maintainable components.
147. Keep deterministic mock data in a dedicated module.
148. Use a reducer for run and agent states.
149. Avoid a monolithic App component.
150. Do not import from any sibling workspace.
151. Use semantic HTML, accessible names, visible focus, and appropriate ARIA.
152. Prevent horizontal overflow at 1440x940, 834x1112, and 390x844.

## Verification

153. Add Vitest and React Testing Library.
154. Test navigation, composer, Thinking disclosure, tool result, Chat snaps, Admission gate, and Run phases.
155. Add `qa/flow.yaml` with browser actions and expected observations.
156. Add `qa/manual-audit.md` covering functionality, responsiveness, visual quality, and accessibility.
157. Run install, tests, build, and `npm run test:sites`.
158. Start the app on port 4301.
159. Use real browser control for runtime QA when available.
160. Capture desktop and mobile screenshots under `qa/screenshots/`.
161. Compare the source and implementation at matching viewports.
162. Put the source and implementation together in one comparison input.
163. Fix every P0/P1/P2 issue that harms use or hierarchy.
164. Re-capture after fixes.
165. Save `design-qa.md` with source, implementation, viewport, findings, history, and final result.
166. `final result: passed` requires browser evidence and no actionable P0/P1/P2.
167. Keep P3 polish separate.
168. Do not deploy or publish.
169. Keep the server running if practical.
170. Handoff commands, files, screenshots, and honest residual limits.
