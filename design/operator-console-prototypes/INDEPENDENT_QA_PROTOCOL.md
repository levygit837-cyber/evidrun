# Independent React Prototype QA Protocol

01. This protocol is read-only.
02. Review only the workspace assigned in the task message.
03. Never open or compare sibling prototype workspaces.
04. Never import another variant's design context.
05. Do not edit source, tests, screenshots, or reports.
06. Save only `independent-qa.md` inside the assigned workspace.
07. Read the assigned workspace `BUILD_BRIEF.md` completely.
08. Read its local `AGENTS.md` completely.
09. Read its `design-qa.md`, `qa/manual-audit.md`, and `qa/flow.yaml`.
10. Inspect accepted screenshots with `view_image`.
11. Treat existing QA claims as hypotheses to verify.
12. Read and use Product Design `audit` materially.
13. Read and use `design-taste-frontend` materially.
14. Read and follow the Browser skill for runtime inspection.
15. State the skills and evidence used in the report.

## Evidence rules

16. A build passing is not visual QA.
17. A screenshot existing is not proof that the flow works.
18. A static frame cannot prove keyboard behavior.
19. Code inspection cannot prove rendered layout.
20. Browser runtime evidence is required for a pass.
21. Use only current workspace evidence.
22. Do not rely on another agent's memory.
23. Tie every finding to a route, state, screenshot, or selector.
24. Record evidence limitations explicitly.
25. Do not claim full accessibility compliance.

## Deterministic gates

26. Run `npm test` in the assigned workspace.
27. Run `npm run build`.
28. Run `npm run test:sites`.
29. Report exact pass/fail counts.
30. Check console errors in the running browser.
31. Check that exactly one `main` landmark exists.
32. Check that four primary routes are reachable.
33. Check that mobile navigation exists at 390 x 844.
34. Check that there is no horizontal overflow at 1440 x 940.
35. Check that there is no horizontal overflow at 834 x 1112.
36. Check that there is no horizontal overflow at 390 x 844.
37. Check that focus-visible styling exists and renders.
38. Check that empty send is disabled.
39. Check that Admission reject blocks enqueue.
40. Check that unsupported pause/resume is not active.

## Route flow

41. Start on Lab.
42. Navigate to Projects.
43. Navigate to Study.
44. Navigate to Runs.
45. Use browser Back and verify a coherent prior route.
46. Return to Lab.
47. Confirm no prior route remains visually mixed.
48. Confirm Project context changes intentionally.
49. Confirm Study and Run records do not silently drift across Projects.
50. Confirm navigation labels remain readable at tablet size.

## Lab and Agent states

51. Inspect idle Lab.
52. Confirm the custom spinner is immediately above the composer during execution.
53. Confirm it is not a generic circular border spinner.
54. Submit a realistic local stub message.
55. Confirm a User block appears.
56. Confirm an Agent block appears.
57. Confirm `Atividade observável` appears.
58. Confirm it does not expose private reasoning.
59. Confirm Tool Call is visibly distinct.
60. Confirm Tool Result is visibly distinct.
61. Confirm Tool Call is `read_text` only in illustrative context.
62. Confirm Tool Result is labeled local/stub.
63. Confirm failure preset is reachable.
64. Confirm empty preset is reachable.
65. Confirm focus behavior remains usable after send.
66. Confirm Chat is explicitly outside SubjectEnvelope.

## Adaptive Chat

67. Confirm Chat begins as a small dock or compact trigger.
68. Open compact Chat.
69. Expand Chat width.
70. Select compact height.
71. Select half height.
72. Select tall height.
73. Select full-thread when available.
74. Collapse without deleting thread state.
75. Close when supported.
76. Confirm keyboard snap alternatives exist.
77. Inspect the circular grip or equivalent snap affordance.
78. Verify long-press preview if browser control can model it reliably.
79. If long-press cannot be verified, name the limit instead of guessing.
80. Confirm preview geometry remains within the viewport.
81. Confirm Chat does not hide primary navigation.
82. Confirm mobile Chat behaves as a bottom sheet.
83. Confirm mobile sheet can be dismissed or collapsed.
84. Confirm route changes preserve thread state when promised.

## Projects

85. Confirm Project is presented as logical scope.
86. Confirm Workspace is separately labeled.
87. Confirm Workspace is not defined as Project.
88. Confirm at least three stub Projects are selectable.
89. Open create-project dialog.
90. Verify required-field validation.
91. Create a Project in local state.
92. Confirm it does not claim persistence.
93. Inspect workflow visualization.
94. Confirm selecting a stage updates a concise inspector.
95. Confirm relationships are understandable without reading every ID.

## Study and Admission

96. Confirm StudyRevision and RunSpec remain distinct.
97. Confirm matrix expresses scenario, variants, and repetitions.
98. Confirm compile preview is visually understandable.
99. Confirm one Admission preflight exists per RunSpec.
100. Switch to rejected state.
101. Confirm issue language is operational and direct.
102. Confirm enqueue is disabled.
103. Switch to admitted state.
104. Confirm enqueue becomes available only for that exact RunSpec.
105. Confirm no text field pretends to be human attestation.

## Runs and evidence

106. Start the deterministic stub Run.
107. Observe queued, preparing, running, evaluating, and terminal.
108. Confirm job and attempt are separate from Run.
109. Reach failed state.
110. Reach completed state.
111. Confirm event progression remains readable.
112. Confirm a completed state is not confused with replayability.
113. Confirm SubjectEnvelope digest limitation is stated.
114. Confirm Bundle is references-only.
115. Confirm portable false and replayable false.
116. Confirm Comparison avoids balance-scale iconography.
117. Confirm no unsupported capability is shown as connected.

## Visual and responsive audit

118. Inspect typography hierarchy and wrapping.
119. Inspect whether panes are cramped or too narrow.
120. Inspect whether full-row buttons reappear.
121. Inspect whether there are excessive cards, dividers, pills, or dots.
122. Inspect whether important content is hidden below a giant heading.
123. Inspect whether body copy remains near 14-16px.
124. Inspect button contrast and disabled state contrast.
125. Inspect icon semantics and consistency.
126. Fail any green decorative database icon.
127. Fail any balance-scale comparison icon.
128. Fail emoji or handcrafted SVG used as UI icons.
129. Confirm one accent system is maintained.
130. Confirm reduced motion has an explicit fallback.
131. Confirm transitions support navigation or feedback.
132. Inspect desktop, tablet, and mobile screenshots directly.

## React code quality

133. Check component boundaries.
134. Flag a giant monolithic App.
135. Check hooks for cleanup of timers and pointer listeners.
136. Check stable keys and deterministic state transitions.
137. Check accessible names and semantic controls.
138. Check that continuous pointer values do not drive excessive React state.
139. Check that sibling workspace imports do not exist.
140. Check that secrets, tokens, and real provider calls do not exist.

## Report

141. Use severity P0, P1, P2, and P3.
142. For every finding, include evidence, impact, and concrete fix.
143. Put findings before praise.
144. Include a deterministic gate table.
145. Include a route/interaction coverage table.
146. Include desktop/tablet/mobile observations.
147. Include code-quality observations.
148. Include evidence limits.
149. End with `independent result: passed` only when no P0/P1/P2 remains.
150. Otherwise end with `independent result: blocked` and name exact blockers.
