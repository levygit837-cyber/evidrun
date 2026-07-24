# Isolated Build Brief: Civic Console

01. You own only this workspace: `02-civic-console`.
02. Do not inspect sibling prototype directories.
03. Do not reuse another variant's source, tokens, screenshots, or decisions.
04. This is an image-guided trial.
05. Its source image is `reference/source.png`.
06. Open and inspect the source image before planning.
07. Read `reference/generation-notes.md` and `reference/image-audit.md` when present.
08. The image is a starting point, not a requirement to copy flaws.
09. Correct image audit findings in React.
10. Do not regenerate the image for small errors.
11. Read repository `AGENTS.md` before editing.
12. Read the complete Product Design `image-to-code` skill.
13. Read the complete Product Design `design-qa` skill.
14. Read the complete Product Design `audit` skill.
15. Read the complete `design-taste-frontend` skill.
16. Use at least Product Design `image-to-code` and `audit` materially.
17. Keep all code, assets, tests, and reports in this workspace.
18. Do not edit backend, contracts, DTOs, Electron, or `apps/web`.
19. Do not call providers or persist credentials.
20. The backend is a deterministic local UI stub.

## Product outcome

21. Help an operator understand Project scope, author a Study draft, inspect Admission, run a stub execution, and read evidence.
22. Required routes: Lab, Projects, Study, Runs.
23. Routes must work with pointer, keyboard, and browser history.
24. The primary flow must work end to end in local React state.
25. The first viewport emphasizes current Project, current stage, and next action.
26. Simplify information before adding containers.
27. Avoid row walls, narrow text panes, and repeated abstract references.
28. Use diagrams only for real relationships.
29. Keep copy concise and mainly pt-BR.
30. Preserve domain technical names exactly.

## Visual direction

31. Direction name is `Civic Console`.
32. Preserve cold porcelain white and deep charcoal.
33. Preserve one restrained vermilion accent.
34. Use smoke and silver neutral surfaces.
35. Do not add cobalt, purple, or green decoration.
36. Communicate success with geometry, labels, and checks.
37. Use one rational sans and mono only for IDs.
38. Use Phosphor Icons only.
39. Do not use Lucide, emoji, custom SVG, or text glyph icons.
40. Project uses folder or bounding-box.
41. Study uses notebook or document-search.
42. Admission uses shield or gate.
43. Run uses play or pulse.
44. Evidence uses archive, fingerprint, or file-lock.
45. Tool read uses file-search.
46. Comparison never uses balance scales.
47. Database icons stay neutral.
48. Avoid beige craft, glassmorphism, AI glow, and generic dashboard cards.
49. Use spatial grouping before borders.
50. Use only essential connectors.
51. Keep at most two content zones after navigation.
52. Body copy is 15-16px equivalent.
53. Buttons are content-sized, not desktop slabs.
54. Use one 8-10px radius system.
55. Transitions run roughly 180-250ms.
56. Honor `prefers-reduced-motion`.

## Shell

57. Use the source image's slim vertical navigation rail.
58. Destinations are Lab, Projects, Study, and Runs.
59. Lab is Home.
60. Put Project context in a compact top strip.
61. Do not widen the rail into a ChatGPT sidebar.
62. Keep the main canvas broad.
63. Use a lateral adaptive Chat dock.
64. Keep system readiness in one disclosure.
65. Mobile uses bottom navigation and one-column content.
66. Do not leave persistent narrow inspectors on mobile.
67. Keep Project distinct from Workspace.
68. Keep StudyRevision distinct from RunSpec.
69. Keep AdmissionRecord distinct from Run.
70. Keep Run distinct from job and attempt.

## Stub context

71. Project: `Retrieval Quality`.
72. Study: `Respostas com fontes insuficientes`.
73. Scenario: `source-grounding-check`.
74. Variants: `direct-answer` and `evidence-first`.
75. One repetition per variant.
76. Date: 23 July 2026.
77. Timezone: America/Asuncion.
78. Use readable local IDs labeled as stub.
79. Do not reuse CRL IDs.
80. Do not claim canonical evidence.

## Lab interaction

81. Implement a functional local composer.
82. Disable empty send.
83. Enter sends and Shift+Enter inserts a newline.
84. Sending starts a deterministic agent sequence.
85. Show a custom Civic Console spinner directly above the composer.
86. It should resolve registration marks into a line, not use a generic ring.
87. Sequence: preparing context, reading authorized input, tool call, tool result, response captured.
88. Render User message and Agent response.
89. Render collapsible Thinking Block titled `Atividade observável`.
90. Never reveal private reasoning or hidden grader content.
91. Render Tool Call `read_text`.
92. Render Tool Result with a short authorized local stub excerpt.
93. Label tool activity as demonstration.
94. Provide idle, running, success, and failure presets.
95. Use an accessible live region for status.
96. Preserve focus after submission.
97. Do not steal scroll position.
98. Keep Chat outside SubjectEnvelope.

## Adaptive Chat

99. Chat begins as a small right-side dock.
100. Clicking opens a compact thread.
101. A separate action expands width.
102. Height states are compact, half, and tall.
103. Collapse and close are distinct.
104. A circular neutral grip triggers snap previews.
105. Holding about 350ms reveals future geometry overlays.
106. Moving selects compact, half, tall, or full-thread.
107. Release commits the selected layout.
108. Do not implement arbitrary free dragging.
109. Provide explicit keyboard snap controls.
110. Mobile uses a bottom sheet.
111. The sheet keeps bottom navigation available.
112. Thread state persists while changing routes.
113. Chat remains subordinate to the workflow.

## Projects

114. Show Project boundaries as spatial regions or lanes.
115. Show current workflow position and next action.
116. Stages include intent, revision, Admission, Run, evaluation, and comparison.
117. Selecting a stage updates a concise inspector.
118. Provide at least three realistic stub Projects.
119. Implement a validated create-project dialog.
120. Created Projects persist only in React state.
121. Show Workspace separately as Integration pending.
122. Do not define Project as a folder.

## Study

123. Implement revision selection and draft editing.
124. Visualize `scenario x variants x repetitions` without a table wall.
125. Include compile preview.
126. Include one Admission preflight per RunSpec.
127. Demonstrate rejected and admitted states.
128. Enqueue stays disabled when rejected.
129. Explain requested versus supported values directly.
130. Let a new local revision correct the issue.
131. Never claim agent-created human authority.

## Runs

132. Implement Start Stub Run.
133. Deterministic phases: queued, preparing, running, evaluating, terminal.
134. Show job and attempt separately.
135. Use a spatial trace instead of a dense event table.
136. Tool events belong only to this clearly illustrative stub.
137. Provide loading, failed, and completed presets.
138. Show SubjectEnvelope digest limitation.
139. Show Bundle as references-only, non-portable, and non-replayable.
140. No functional pause/resume.
141. Comparison uses juxtaposition, not balance scales.

## Engineering

142. Use React 19 and Vite from the provided template.
143. Use Tailwind CSS v4 and `@tailwindcss/vite`.
144. Use Motion from `motion/react`.
145. Use `@phosphor-icons/react`.
146. Split shell, routes, Chat, agent blocks, and primitives into maintainable components.
147. Keep mock data in its own module.
148. Use reducers for agent and run state.
149. Avoid a monolithic App.
150. Do not import any sibling workspace code.
151. Use semantic HTML, accessible names, visible focus, and ARIA.
152. Prevent horizontal overflow at 1440x940, 834x1112, and 390x844.

## Verification

153. Add Vitest and React Testing Library.
154. Test navigation, composer, agent blocks, Chat snaps, Admission gating, and Run phases.
155. Add `qa/flow.yaml` with browser actions and expectations.
156. Add `qa/manual-audit.md` with functional, responsive, visual, and accessibility findings.
157. Run install, tests, build, and `npm run test:sites`.
158. Start the app on port 4302.
159. Use real browser control when available.
160. Capture desktop and mobile screenshots under `qa/screenshots/`.
161. Compare source and implementation at matching viewports.
162. Put source and implementation into one comparison input.
163. Fix P0/P1/P2 issues rather than copying source flaws.
164. Re-capture after fixes.
165. Save `design-qa.md` with evidence, findings, comparison history, and final result.
166. `final result: passed` requires browser-rendered evidence and no actionable P0/P1/P2.
167. Keep P3 polish separate.
168. Do not deploy or publish.
169. Keep the server running if practical.
170. Handoff files, commands, screenshots, and honest residual limits.
