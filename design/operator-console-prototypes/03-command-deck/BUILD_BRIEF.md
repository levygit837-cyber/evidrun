# Isolated Build Brief: Command Deck

01. You own only this workspace: `03-command-deck`.
02. Do not inspect sibling prototype directories.
03. Do not reuse code, tokens, screenshots, or decisions from another variant.
04. This is an autonomous, no-image design trial.
05. Do not look for or open any generated design reference.
06. Read the repository `AGENTS.md` before making changes.
07. Read the complete `design-taste-frontend` skill.
08. Read the complete Product Design `get-context` skill.
09. Read the complete Product Design `image-to-code` skill for build discipline.
10. Read the complete Product Design `audit` skill for QA discipline.
11. Use at least `design-taste-frontend` and Product Design `audit` materially.
12. State a one-line Design Read before implementing.
13. Treat this as dense product UI, where `design-taste-frontend` is advisory only.
14. Use Product Design and domain truth to drive information architecture.
15. Build a fast React prototype, not production EvidRun.
16. Keep every source, asset, test, and report inside this workspace.
17. Do not edit contracts, backend, DTOs, Electron, or `apps/web`.
18. Do not persist secrets or call any real provider.
19. The backend is an explicit deterministic UI stub.
20. Label illustrative records as `Demonstração local` or `Stub local`.

## Product outcome

21. Help an operator understand Project scope, create a Study draft, inspect Admission, run a stub execution, and read evidence.
22. Routes required: Lab, Projects, Study, Runs.
23. Use client-side routing or a small route state with stable URLs or hashes.
24. Every route must be reachable with keyboard and pointer.
25. The browser back button should not leave the app in a broken state.
26. The first viewport must prioritize one task, not advertise every capability.
27. Keep the data hierarchy simple and visually legible.
28. Avoid long hairline lists and repeated abstract references.
29. Prefer grouped stages, compact summaries, and meaningful diagrams.
30. Never use fake KPIs or invented success rates.

## Autonomous visual direction

31. Create a direction named `Command Deck`.
32. Use a cold graphite base with neutral silver surfaces.
33. Use one restrained electric-cobalt accent.
34. Do not use green for database, success, workflow, or icons.
35. Success is communicated with shape, checkmarks, labels, and contrast.
36. Use one modern sans family and one mono only for IDs.
37. Use a single icon family: Phosphor Icons.
38. Do not use Lucide, emoji, handcrafted SVG, or text glyph icons.
39. Choose icons by object semantics, not visual convenience.
40. Project uses a folder or bounding-box icon.
41. Study uses a notebook or file-search icon.
42. Admission uses a shield-check or gate icon.
43. Run uses a play-circle or pulse icon.
44. Evidence uses a fingerprint, archive, or file-lock icon.
45. Never use a balance-scale icon for comparison.
46. Never color a database cylinder green.
47. Avoid glassmorphism, neon glow, AI orbs, and purple-blue mesh.
48. Avoid three equal cards in a row.
49. Avoid full-width button slabs.
50. Buttons should fit their content and have a clear priority.
51. Use at most two persistent content zones plus navigation.
52. Body copy should be 14-16px and comfortably wide.
53. One corner-radius system must be used consistently.
54. Transitions should last roughly 170-240ms.
55. Every motion must communicate navigation, disclosure, or feedback.
56. Honor `prefers-reduced-motion`.

## App shell and routes

57. Build a compact command bar as the shell's organizing element.
58. Do not copy ChatGPT's sidebar.
59. Navigation may be a thin top command rail plus a compact project switcher.
60. On mobile, provide a bottom navigation with four destinations.
61. Lab is the Home route.
62. Projects shows logical project boundaries and current workflow state.
63. Study shows a draft revision, matrix, compile preview, and Admission decision.
64. Runs shows a selected Run, event phases, evidence, and terminal disclosure.
65. Keep Project distinct from Workspace.
66. Keep StudyRevision distinct from RunSpec.
67. Keep AdmissionRecord distinct from Run.
68. Keep Run distinct from job and attempt.
69. Chat never enters the SubjectEnvelope.
70. The Subject Agent receives only the authorized envelope.

## Demonstration data

71. Use Project `Release Integrity`.
72. Use Study `Diagnóstico de regressões após deploy`.
73. Use scenario `deployment-log-trace`.
74. Use variants `summary-first` and `evidence-first`.
75. Use one repetition per variant.
76. Use readable local IDs, visibly marked as stub data.
77. Use date 23 July 2026 and timezone America/Asuncion.
78. Do not present the CRL fixture as if it ran in this prototype.
79. Use a Project workflow visualization with stages, branches, and current position.
80. The workflow should answer what happened, what is blocked, and what comes next.

## Lab and agent interaction

81. Implement a real interactive stub composer.
82. Sending a message starts a deterministic state sequence.
83. Show a custom spinner immediately above the composer while active.
84. The spinner must be visually original and consistent with Command Deck.
85. The spinner cannot be a generic circular border spinner.
86. Sequence: preparing context, reading authorized input, tool call, tool result, response captured.
87. Show a User message block.
88. Show an Agent response block.
89. Show a collapsible Thinking Block.
90. Label it `Atividade observável` rather than private reasoning.
91. Never reveal chain-of-thought or hidden grader content.
92. Implement a Tool Call block for `read_text`.
93. Implement a Tool Result block with a small authorized excerpt.
94. The Tool Result must clearly say it is local stub data.
95. Provide success, empty, and failure demonstrations through a state switcher.
96. Make the composer send button disabled when empty.
97. Support Enter to send and Shift+Enter for a newline.
98. Focus must return sensibly after message submission.

## Adaptive Chat

99. Chat begins as a small lateral dock.
100. Clicking the dock opens a compact thread view.
101. A second control expands Chat to a wider inspection view.
102. A height control lets the user choose compact, half, or tall.
103. Add an explicit close/collapse action.
104. Add a visible drag handle represented by a neutral circular grip.
105. Holding the grip for about 350ms reveals snap previews.
106. Snap previews show where and how the window will be placed.
107. Moving while held highlights compact, half, tall, and full-thread zones.
108. Releasing commits the highlighted layout.
109. This is a dock auto-complete interaction, not arbitrary free dragging.
110. Provide keyboard alternatives for every snap state.
111. On mobile, Chat becomes a bottom sheet with safe-area padding.
112. The bottom sheet must not hide primary navigation.
113. Chat state should persist while navigating within the stub session.

## Projects

114. Show Project as a bounded logical scope.
115. Show Workspace as a separate local integration concept.
116. Represent the Project lifecycle as a compact workflow, not a wall of text.
117. Make selecting a workflow stage update an adjacent concise inspector.
118. Provide a project switcher with at least three realistic stub projects.
119. Add a create-project dialog with validation.
120. Newly created Projects may exist only in React state.

## Study

121. Implement revision selection and a draft editor stub.
122. Show matrix `scenario x variants x repetitions` visually.
123. Include compile preview.
124. Include Admission preflight for each RunSpec.
125. Provide an admitted/rejected demonstration toggle.
126. Enqueue must remain disabled when Admission is rejected.
127. Explain the blocking issue in operational language.
128. A human decision must never be claimed without authority.

## Runs

129. Implement Start Stub Run.
130. Progress through queued, preparing, running, evaluating, terminal.
131. Expose pause only if it is clearly disabled and marked unsupported.
132. Never imply pause/resume is active.
133. Show job and attempt separately from Run identity.
134. Show event phases as a readable progression.
135. Show SubjectEnvelope digest as recorded but not automatically exportable.
136. Show Bundle as references-only, non-portable, and non-replayable.
137. Add a comparison view without a balance-scale icon.
138. Allow the user to switch between loading, failed, and completed states.

## Engineering

139. Use React 19 and Vite from the provided template.
140. Use Tailwind CSS v4 as the CSS framework.
141. Use `@tailwindcss/vite`, not the old PostCSS plugin.
142. Use Motion from `motion/react` for state and layout transitions.
143. Use `@phosphor-icons/react` for icons.
144. Break the UI into maintainable components under `src/`.
145. Keep deterministic mock data in a dedicated module.
146. Keep interaction state in a reducer or focused hooks.
147. Avoid giant monolithic components.
148. Do not import from outside this workspace.
149. Add accessible names, focus-visible styling, and appropriate ARIA.
150. No horizontal overflow at 1440x940, 834x1112, or 390x844.

## Verification and deliverables

151. Add Vitest and React Testing Library tests for navigation and stub execution.
152. Test empty composer, send flow, Thinking disclosure, tool result, Admission gate, and Chat snaps.
153. Add `qa/flow.yaml` with browser actions and expected observations.
154. Add `qa/manual-audit.md` with visual, responsive, interaction, and accessibility findings.
155. Run dependency install, tests, build, and `npm run test:sites`.
156. Start the app on port 4303.
157. Use browser control for real runtime QA when available.
158. Capture desktop and mobile screenshots under `qa/screenshots/`.
159. Inspect the screenshots, fix visible P0/P1/P2 issues, and capture again.
160. Save `design-qa.md` with evidence paths and `final result: passed` only when true.
161. Record any unresolved limitation honestly.
162. Do not deploy or publish.
163. Keep the server running if practical at handoff.
164. Finish by reporting files changed, commands run, screenshots, and residual risks.
