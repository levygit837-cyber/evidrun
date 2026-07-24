# Independent Image Review: Carbon Rhythm

01. Review only `reference/source.png` in this workspace.
02. Do not open sibling workspaces.
03. Do not compare against another visual direction.
04. Do not implement React.
05. Do not regenerate the image.
06. Use the actual image as evidence, not its filename or prompt alone.
07. Read `IMAGE_BRIEF.md` before reviewing.
08. Read `reference/generation-notes.md` when present.
09. Read the complete Product Design `audit` skill.
10. Read the complete `design-taste-frontend` skill.
11. Use both skills materially.
12. Treat `design-taste-frontend` as an anti-slop lens, not dense-app architecture.
13. Save the review to `reference/image-audit.md`.
14. Lead with findings ordered by P0, P1, P2, P3.
15. Tie every finding to a visible region in the image.

## Review purpose

16. This review prepares a builder to use the image as a base.
17. It must explicitly say the implementation is not a pixel copy.
18. It must identify what to preserve.
19. It must identify what to correct.
20. It must identify what the image cannot specify.
21. It must distinguish visual flaw from absent interaction state.
22. It must distinguish domain mismatch from visual preference.
23. It must avoid generic taste language.
24. It must provide concrete React/CSS recommendations.
25. It must not claim browser behavior from a static image.

## Hierarchy and usability

26. Is the active Project visible without dominating the page?
27. Is the active Study readable at a glance?
28. Is the current workflow stage immediately clear?
29. Is the primary next action obvious?
30. Are secondary controls clearly subordinate?
31. Is the main canvas broad enough for comfortable text?
32. Are any panes too narrow?
33. Are labels or values squeezed?
34. Is any important copy smaller than a practical UI size?
35. Are IDs visually secondary?
36. Are there full-width buttons disguised as rows?
37. Are there excessive separators?
38. Are containers nested without real hierarchy?
39. Does whitespace organize content effectively?
40. Is there an unnecessary dashboard feel?

## Workflow visualization

41. Does the trace describe a real product flow?
42. Are stages differentiated by more than color?
43. Are completed, active, and future states legible?
44. Are connectors essential or decorative?
45. Can the selected stage support an inspector in code?
46. Would the workflow collapse cleanly on mobile?
47. Are Project, Study, Admission, Run, and evidence conflated?
48. Are job and attempt distinct from Run?
49. Is tool activity clearly illustrative?
50. Are any unsupported capabilities presented as real?

## Agent interaction

51. Can User and Agent messages be distinguished without chat bubbles everywhere?
52. Is the `Atividade observável` block visually distinct?
53. Could the block be mistaken for private reasoning?
54. Is Tool Call visually identifiable?
55. Is Tool Result visually identifiable?
56. Is the custom spinner placed immediately above the input?
57. Does the spinner read as active progress?
58. Is the composer a practical size?
59. Is the disabled send state obvious?
60. Is draft-only status visible but not noisy?
61. Is Chat explicitly outside SubjectEnvelope?

## Adaptive Chat

62. Does the lateral dock look discoverable?
63. Is the dock subordinate to the workflow?
64. Is the circular grip understandable?
65. Is the snap-preview concept visible enough to implement?
66. Could the preview be mistaken for a second permanent panel?
67. Does Chat obscure content?
68. Are compact, expanded, height, collapse, and close actions plausible?
69. Is the thread area wide enough in its shown state?
70. What should change on tablet?
71. What should change on mobile?

## Visual system

72. Is the carbon palette genuinely neutral and premium?
73. Is oxidized orange restrained to meaningful emphasis?
74. Is any green used decoratively?
75. Is any purple/blue AI glow present?
76. Is contrast adequate by visual inspection?
77. Is the type hierarchy consistent?
78. Is mono limited to IDs and events?
79. Is one radius system evident?
80. Are shadows and materials restrained?
81. Are there too many cards?
82. Are there excessive pills or dots?
83. Does the screen feel original without becoming experimental?

## Icon audit

84. Does every visible icon represent its object or action?
85. Is one icon family used consistently?
86. Are stroke weights consistent?
87. Is any database icon green?
88. Is any comparison represented by balance scales?
89. Are there robots, brains, sparkles, or generic AI symbols?
90. Are Tool Call and Tool Result icons contextually correct?
91. Are close, expand, and resize actions distinguishable?
92. Are there icons without accessible text equivalents in planned code?

## Static-image limits

93. List unverified keyboard behavior.
94. List unverified focus behavior.
95. List unverified hover/active/disabled states.
96. List unverified page transitions.
97. List unverified reduced-motion behavior.
98. List unverified loading/failure/terminal transitions.
99. List unverified drag-hold snap mechanics.
100. List unverified responsive collapse.
101. List any copy that looks inaccurate or malformed.
102. List any clipped or distorted content.

## Builder guidance

103. Give a concise `Preserve` list.
104. Give a concise `Correct in code` list.
105. Give a concise `Implement beyond the image` list.
106. Recommend concrete component boundaries.
107. Recommend desktop, tablet, and mobile layout behavior.
108. Recommend the custom spinner anatomy.
109. Recommend Thinking/Tool state anatomy.
110. Recommend Chat snap-state names.
111. Recommend icon replacements for any bad glyph.
112. Recommend spacing/type tokens if visible.
113. Do not recommend copying source defects.
114. Do not request image regeneration.
115. End with `builder disposition: proceed with corrections` or `blocked`.
116. Use `blocked` only for a P0 that prevents meaningful implementation.
117. Otherwise let the builder proceed with explicit corrections.
118. Ensure every P1/P2 has a concrete fix.
119. Keep the report useful and evidence-based.
120. Stop after saving `reference/image-audit.md`.
