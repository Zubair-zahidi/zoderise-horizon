# Horizon: a private workspace for teaching and learning

The central journey is **start with a question → work with evidence → practise → save useful work**. Home introduces four clear workspaces. Chat handles questions and images. Knowledge holds private or administrator-shared material. Research answers from inspectable evidence. Study Lab turns selected files into learning material. Prompt Studio creates editable briefs for lessons, rubrics, tutoring, revision, practice, and parent communication.

## Design implemented

Midnight navy surfaces, soft blue controls, champagne highlights, generous spacing, and a new gold-and-glass astrolabe hero. Existing library artwork remains part of the same visual family. WebP assets keep the visual experience lightweight. Depth comes from layered lighting, perspective hover effects, and CSS orbit details without a separate 3D engine. Balanced is restrained, Immersive adds slow ambient motion, and Reduced keeps the workspace still. Layouts adapt to smaller screens and keyboard focus remains visible.

## Product decisions

- Keep learning and teacher preparation central; avoid unrelated features that compete for the laptop's memory.
- Keep AI output editable and visibly separate from verified evidence. A prompt template does not claim curriculum approval.
- Preserve session-only and saved-chat choices. Explicit library uploads persist independently of chat storage.
- Use local identity facts consistently: Zubair Zahidi, Zoderise Company, Kabul, Afghanistan; built for Kardan Private School. Credit underlying models separately.
- Use small inference context and a short warm period. Serialize generation on this hardware.
- Keep existing document permissions, accounts, history, bookmarks, export tools, and administration.

## Next scaling milestone

Class rosters, assignment submission, grading records, shared collaboration, and multi-host inference require a separate permissions/data-model design and real school acceptance testing. They are not claimed as implemented. Current release provides a usable single-host teaching and learning workspace, not an enterprise school management system.
