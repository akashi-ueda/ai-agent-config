---
name: graphify
description: "코드, 문서, 이미지 등을 지식 그래프로 만들고 관계, 경로, 영향 범위를 질의합니다."
---

# Graphify

Use the `graphify` CLI to build and query knowledge graphs for code, docs, research, and architecture.

## Required Behavior

- If the user asks for graph search, relationship mapping, impact paths, architecture graphs, or says `graphify`, use this skill.
- If no path is given, use the current repo root.
- Prefer existing `graphify-out/graph.json` before broad file reads when it exists.
- Never invent graph edges. Mark uncertainty clearly.

## Setup

Verify the CLI is available:

```bash
command -v graphify >/dev/null 2>&1 || {
  pip install --user graphifyy
}
```

If `pip` cannot install `graphifyy` and `graphify` is missing, stop and show the pip error.

## Common Commands

```bash
graphify .
graphify <path>
graphify <path> --mode deep
graphify <path> --update
graphify query "<question>"
graphify path "<source>" "<target>"
graphify explain "<node>"
```

## Output

Report the generated files, usually:

- `graphify-out/graph.json`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/index.html`

Keep summaries short. Cite graph nodes, paths, and source files when answering from graph data.
