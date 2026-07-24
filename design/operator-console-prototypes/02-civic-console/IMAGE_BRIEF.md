# Image Direction Brief: Civic Console

01. Generate exactly one horizontal desktop product-UI image.
02. This image represents one focused screen, not a collage.
03. Target dimensions are 1440 x 1024.
04. It is a visual anchor for a React prototype.
05. The later implementation covers Lab, Projects, Study, and Runs.
06. This image focuses on Lab Home with Project workflow context.
07. Do not include several pages in one frame.
08. Do not render a vertical long page.
09. Do not include browser chrome or device framing.
10. Use concise pt-BR copy.

## Product

11. Product: EvidRun Operator Console.
12. User: an operator evaluating grounded agent responses.
13. Active Project: `Retrieval Quality`.
14. Active Study: `Respostas com fontes insuficientes`.
15. Scenario: `source-grounding-check`.
16. Variants: `direct-answer` and `evidence-first`.
17. Current state: local deterministic prototype stub.
18. Date: 23 July 2026.
19. Timezone: America/Asuncion.
20. Label the state `Demonstração local`.

## Design thesis

21. Direction name: `Civic Console`.
22. Imagine a contemporary public records room designed by a premium Swiss product team.
23. The interface should feel calm, accountable, legible, and modern.
24. It must not feel bureaucratic or old fashioned.
25. It must not look like a generic admin dashboard.
26. It must not look like ChatGPT.
27. Use cold porcelain white as the primary surface.
28. Use deep charcoal for text and anchors.
29. Use one restrained vermilion accent.
30. Use smoke and silver neutrals for secondary surfaces.
31. Do not use cobalt as the main accent.
32. Do not use purple or green as decoration.
33. Success should use geometry and labels, not green.
34. Failure uses vermilion with an X and direct language.
35. Avoid beige-paper craft aesthetics.

## Typography and density

36. Use a rational Swiss sans with strong optical hierarchy.
37. Use mono only for IDs and event names.
38. Body text must be 15-16px equivalent.
39. Headings are clear, not enormous.
40. Keep text measures wide enough for easy scanning.
41. Avoid condensed text columns.
42. Avoid tiny explanatory copy.
43. Use whitespace before borders.
44. Use grouping before cards.
45. Use only essential row separators.
46. Avoid lines across the entire page when a local divider works.
47. Buttons remain content-sized.
48. Do not create full-width button rows.
49. Use a consistent moderate radius around 8-10px.
50. Use very soft, cool shadows only for floating Chat.

## Shell

51. Use a slim vertical navigation rail.
52. Keep the rail about 72px wide with icons and short labels on hover or active.
53. Include Lab, Projects, Study, and Runs.
54. Lab is active.
55. Put Project context in a top command strip inside the main canvas.
56. Do not make the left rail a wide ChatGPT sidebar.
57. Use at most two content zones after navigation.
58. Keep the main canvas broad and easy to read.
59. Provide a lateral Chat dock on the right.
60. Show system readiness as one compact disclosure, not four colored rows.

## Main canvas

61. Lead with `Retrieval Quality` and the active Study.
62. Show the current workflow as spatial regions or lanes.
63. The workflow is the visual signature.
64. Stages: Intent, Revision, Admission, Run, Evidence.
65. Show the current position at Admission review.
66. Use only four or five meaningful workflow objects.
67. Avoid a node explosion.
68. Avoid connector spaghetti.
69. Use broad zones with one selected object.
70. Selected object is `Admission preflight`.
71. Show one direct issue: `required source coverage missing`.
72. Explain it in a single human-readable sentence.
73. Show a concise next action `Criar nova revisão`.
74. Enqueue should appear disabled and secondary.
75. Do not claim human approval.
76. Show `RunSpec` as compiled preview, not a Run.
77. Show Workspace as a separate integration concept.
78. Workspace linking is `Integration pending`.
79. Do not include fake KPIs.
80. Do not include a generic analytics chart.

## Agent activity

81. Put the active composer in the lower main canvas.
82. Place a custom spinner immediately above it.
83. Spinner concept: a short sequence of registration stamps resolving into a line.
84. It must not be a generic circular border spinner.
85. Label it `Verificando referências autorizadas`.
86. Show one User message.
87. Show a concise Agent draft response.
88. Include a collapsible `Atividade observável` block.
89. Show `Preparing context`, `Tool call: read_text`, and `Tool result captured`.
90. Do not show private reasoning.
91. Do not show hidden grader text.
92. Tool Call and Tool Result must be distinct but quiet.
93. Use a file-search icon for read.
94. Use a document-check icon for result.
95. Avoid robots, brains, stars, and sparkles.

## Composer

96. Composer placeholder: `Pergunte sobre a evidência ou descreva um draft`.
97. Show the active Project as a compact integrated context selector.
98. Include attach/read-source and send controls.
99. Empty send should look disabled.
100. Avoid making the composer a giant outlined card.
101. Use a vermilion focus line only when active.
102. Keep helper text to one disclosure line.
103. Show that the Lab Agent is draft-only.
104. State that Chat is not part of SubjectEnvelope.

## Adaptive Chat

105. Chat begins as a small right-side dock.
106. Show a compact thread preview with one message count.
107. Include a circular neutral grip along the dock edge.
108. Holding the grip will reveal snap previews in code.
109. Show a subtle translucent placement preview without glassmorphism.
110. Preview indicates a wider and taller thread state.
111. Do not show free-floating draggable windows.
112. Do not cover the workflow issue.
113. Include expand, height, collapse, and close affordances.
114. Icons should feel like one modern outline family.
115. Chat remains subordinate to the Project workflow.

## Icon discipline

116. Use one icon family only.
117. Use modern outline icons with consistent weight.
118. Project uses folder or bounding-box.
119. Study uses notebook or document-search.
120. Admission uses shield/gate.
121. Run uses play/pulse.
122. Evidence uses archive/fingerprint/file-lock.
123. Comparison never uses a balance scale.
124. Database cylinder is neutral charcoal or silver.
125. No emoji.
126. No invented symbolic icons.

## Anti-slop exclusions

127. No AI-purple gradient.
128. No blue glow.
129. No glass card stack.
130. No three equal KPI cards.
131. No fake precision metrics.
132. No tiny text decoration.
133. No excessive pills.
134. No excessive status dots.
135. No full-row buttons.
136. No cards nested inside cards.
137. No balance-scale icon.
138. No green database icon.
139. No robot or sparkle icon for Agent.
140. No connector-heavy workflow.

## Final visual check

141. The selected Project and current workflow stage should be immediately clear.
142. The Admission block should be readable without zooming.
143. The composer and spinner should be easy to locate.
144. Chat should feel adaptive, not intrusive.
145. Tool Call and Tool Result should be visually understandable.
146. The layout should be viable in responsive React and Tailwind.
147. The page should feel premium through typography and restraint.
148. It must be visibly different from Carbon Rhythm and Evidence Ledger.
149. It should not rely on decorative color to explain data.
150. Generate one image and save the final asset under this workspace's `reference/` folder.
