# Independent Image Review: Civic Console

01. Review only `reference/source.png` in this workspace.
02. Do not open sibling workspaces.
03. Do not compare with Carbon Rhythm or Evidence Ledger.
04. Do not implement React.
05. Do not regenerate the image.
06. Inspect the actual image before writing findings.
07. Read `IMAGE_BRIEF.md` first.
08. Read `reference/generation-notes.md` when present.
09. Read the complete Product Design `audit` skill.
10. Read the complete `design-taste-frontend` skill.
11. Use both skills materially.
12. Treat anti-slop guidance contextually for dense product UI.
13. Save findings to `reference/image-audit.md`.
14. Order findings by P0, P1, P2, and P3.
15. Tie every finding to a visible screen region.

## Review purpose

16. Prepare an implementation agent to use the image as a base.
17. Explicitly state that implementation is not a pixel-perfect copy of errors.
18. Identify what should be preserved.
19. Identify what needs correction.
20. Identify interaction and responsive gaps the image cannot answer.
21. Separate visual flaws from missing states.
22. Separate domain truth issues from taste.
23. Avoid vague feedback such as `make it modern`.
24. Give concrete React/Tailwind recommendations.
25. Do not claim browser behavior from the static frame.

## Hierarchy and readability

26. Is active Project immediately understandable?
27. Is active Study readable?
28. Is the selected workflow stage clear?
29. Is the next action obvious?
30. Is Enqueue visually secondary when disabled?
31. Is the main canvas sufficiently wide?
32. Are any panels too narrow?
33. Is any text cramped or clipped?
34. Is any important copy too small?
35. Are IDs and event names secondary?
36. Are there long full-width button rows?
37. Are there too many dividers?
38. Are there cards nested inside cards?
39. Does spacing organize the page before borders?
40. Does it resemble a generic admin dashboard?

## Project workflow

41. Do spatial regions map to real entities?
42. Are Intent, Revision, Admission, Run, and Evidence distinct?
43. Is RunSpec clearly a preview rather than a Run?
44. Is Workspace visibly separate from Project?
45. Are current and future states legible without relying only on vermilion?
46. Are connectors essential and easy to follow?
47. Is the selected Admission issue readable?
48. Can an inspector be built without a third persistent column?
49. Can the workflow collapse sensibly on tablet and mobile?
50. Is any unavailable capability shown as connected?

## Agent and composer

51. Are User and Agent blocks visually distinct?
52. Is `Atividade observável` recognizable as progress?
53. Could it be mistaken for chain-of-thought?
54. Is Tool Call clearly identifiable?
55. Is Tool Result clearly identifiable?
56. Is the custom spinner immediately above the composer?
57. Does the spinner feel unique and functional?
58. Is the composer wide enough?
59. Is empty send obviously disabled?
60. Is draft-only disclosure clear but quiet?
61. Is Chat exclusion from SubjectEnvelope visible?

## Adaptive Chat

62. Is the compact dock discoverable?
63. Is it subordinate to the workflow?
64. Is the circular grip understandable?
65. Does the snap preview communicate future geometry?
66. Could it be mistaken for a permanent third panel?
67. Does it obscure the Admission issue?
68. Are expand, height, collapse, and close distinguishable?
69. Is the thread width usable?
70. What should change on tablet?
71. What should change on mobile?

## Visual system

72. Does cold porcelain avoid beige craft aesthetics?
73. Is vermilion restrained to semantic emphasis?
74. Is any green used decoratively?
75. Is cobalt or purple introduced unexpectedly?
76. Is contrast credible by visual inspection?
77. Is typography consistently rational and readable?
78. Is mono limited to appropriate content?
79. Is the radius system consistent?
80. Are shadows restrained?
81. Are there excessive cards?
82. Are pills and status dots overused?
83. Does the page feel premium through restraint?

## Icon audit

84. Does each icon match its object or action?
85. Is one icon family used?
86. Are stroke weights consistent?
87. Is a database cylinder green?
88. Is Comparison represented with balance scales?
89. Are robots, brains, sparkles, or generic AI glyphs present?
90. Are file-search and document-check used for Tool Call/Result?
91. Are close, expand, and resize controls distinct?
92. Identify any decorative icon badges that should be removed.

## Static limits

93. List unverified keyboard navigation.
94. List unverified focus states.
95. List unverified hover/active/disabled states.
96. List unverified route transitions.
97. List unverified reduced motion.
98. List unverified loading/failure/terminal states.
99. List unverified long-press snap behavior.
100. List unverified responsive behavior.
101. Identify malformed or inaccurate copy.
102. Identify clipping or visual distortion.

## Builder guidance

103. Provide a `Preserve` list.
104. Provide a `Correct in code` list.
105. Provide an `Implement beyond the image` list.
106. Recommend component boundaries.
107. Recommend desktop, tablet, and mobile behavior.
108. Recommend custom spinner anatomy.
109. Recommend Thinking and tool-block anatomy.
110. Recommend Chat snap-state names.
111. Recommend replacements for any invalid icon.
112. Recommend visible spacing and type tokens.
113. Do not recommend reproducing image defects.
114. Do not request regeneration.
115. End with `builder disposition: proceed with corrections` or `blocked`.
116. Use `blocked` only for a P0 preventing meaningful implementation.
117. Otherwise allow the builder to proceed with corrections.
118. Ensure every P1/P2 has a concrete fix.
119. Keep the report evidence-based and practical.
120. Stop after saving `reference/image-audit.md`.
