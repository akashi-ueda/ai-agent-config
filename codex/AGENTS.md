# Codex 전역 지침

경로는 `~/.codex`, `~/.agents` 기준. Windows는 `%USERPROFILE%\.codex` 등으로 대응.

## 응답 스타일

caveman 압축 모드는 전역 훅 `~/.codex/hooks.json`(SessionStart·UserPromptSubmit → `hooks/caveman.py`)이 매 세션·매 턴 자동 주입한다. 여기에 스타일 규칙을 인라인하지 않는다. 끄기: "normal mode" / "stop caveman".

## 설정 동기화 (지침)

에이전트 전역 설정은 여러 환경에서 빠르게 재구축하도록 SSOT 저장소(`~/ai-agent-config`)로 관리한다. 전역 규칙·플러그인·스킬·MCP·훅을 바꾸면(또는 사용자가 바꿔달라 하면) 그 작업 끝에 `python ~/ai-agent-config/scripts/sync.py codex`를 실행한다. 스크립트가 live→repo 미러(`capture.py`) 후 관리 경로만 commit하고 `pull --rebase` 후 push한다. 설정을 안 바꿨으면 실행하지 않는다(매 프롬프트 훅 아님). repo 위치는 기본 `~/ai-agent-config`, 다르면 `AI_AGENT_CONFIG_REPO`로 지정.

변경 종류로 경로를 나눈다(2티어):
- **관리 설정 미러**(CLAUDE.md·AGENTS.md·settings·MCP·hooks 등 capture 대상) → `sync.py`로 `master` 직접 push 허용. 멱등·저위험.
- **코드·설치엔진·manifest·플러그인·CI 변경**(`scripts/`·`install.*`·`manifest/`·`claude/personal-local` 등) → `master` 직접 push·머지 금지. `feat/<주제>` 브랜치 + `gh pr create`로 PR을 열고(비자명하면 이슈 먼저) CI 통과까지만 한다. **PR 머지·클로즈 판단은 사용자가 한다. 에이전트는 사용자가 명시적으로 요청할 때만 머지한다.** 두 에이전트(Claude·Codex)가 같은 코드를 동시 편집할 때 충돌을 막고 머지 게이트를 사람이 통제하는 게 목적.

## 플러그인/스킬 출처

- 설치 플러그인 집합은 `manifest/plugins.json`(SSOT)에 선언된다. 추가·변경은 그 파일을 편집하거나 `refresh-plugins` 스킬로 drift PR을 연 뒤 `install.*`을 재실행한다.
- 모든 스킬은 **plugin으로만** 노출한다. `~/.codex/skills`·`~/.agents/skills` 같은 standalone 폴더는 사용하지 않는다.
- personal marketplace root는 `~/.agents`, 파일은 `~/.agents/plugins/marketplace.json`. 각 entry의 `source.path`는 `./.codex/plugins/<plugin>` 형식.
- local personal 플러그인 원본은 `~/.codex/plugins/<plugin>`, 설치 캐시는 `~/.codex/plugins/cache/personal/<plugin>/<version>`.
- `~/.agents`는 Codex marketplace metadata 전용. 공유 스킬·Claude용 파일을 넣지 않는다.
- `superpowers`처럼 store/curated 플러그인은 `openai-curated` 공식 marketplace에서 설치한다.
- gstack 코어는 `~/.gstack/core`, plugin이 bin을 거기서 직접 resolve한다.
- 한국어 표시 설명은 `~/.codex/skill-descriptions.ko.json` + 설치본 copy의 `SKILL.md` frontmatter `description`에 둔다. upstream 원본은 수정하지 않고 설치본 copy에만 적용한다.

## 설치된 플러그인

- `superpowers@openai-curated` — 계획·TDD·디버깅·검증·병렬 작업 방법론
- `graphify@personal` — 코드·문서·아키텍처 관계 지식 그래프
- `gstack@personal` — 제품·계획·디자인 리뷰, QA, 보안, 문서화, spec, ship
- `mattpocock-skills@personal` — grill, triage, issue 분해, PRD, prototype, architecture 개선
- `reply-trace@personal` — 자동 사용 항목 공개(아래 "최종 응답 공개")

스킬은 실제 Codex id `plugin:skill`로 참조한다.

## 자동 트리거 (한국어)

| 사용자 표현 | 대상 |
|------------|------|
| 짧게 / 토큰 줄여 / 간단히 / 압축 / 요약 / caveman | caveman 전역 훅 압축 모드 |
| 아이디어 / 브레인스토밍 / 요구사항 정리 / 방향 잡자 | `superpowers:brainstorming` |
| 계획 세워 / 구현 계획 / 작업 순서 / 단계별 / 플랜 작성 | `superpowers:writing-plans` |
| 계획 실행 / 플랜대로 진행 / 체크포인트 두고 구현 | `superpowers:executing-plans` |
| TDD / 테스트 주도 / 테스트 먼저 / 레드 그린 | `superpowers:test-driven-development` |
| 서브에이전트 / 병렬 개발 / 작업 나눠 / 독립 작업 | `superpowers:subagent-driven-development` |
| 워크트리 / git worktree / 격리 작업 / 별도 작업공간 | `superpowers:using-git-worktrees` |
| 디버깅 / 원인 추적 / 버그 원인 / 체계적 조사 / 재현 | `superpowers:systematic-debugging` |
| 검증 / 완료 전 확인 / 테스트 확인 / 증거 확인 | `superpowers:verification-before-completion` |
| 그릴 / grill / 계획 검증 / 날카롭게 질문 / 계획 털어봐 | `mattpocock-skills:grill-me` |
| 문서 기준 그릴 / ADR / CONTEXT / 도메인 용어 기준 | `mattpocock-skills:grill-with-docs` |
| 이슈 분류 / 트리아지 / 버그 정리 / 백로그 정리 | `mattpocock-skills:triage` |
| 이슈로 쪼개 / 티켓 만들어 / 작업 분해 / 구현 이슈 | `mattpocock-skills:to-issues` |
| PRD / 제품 요구사항 문서 / 대화를 PRD로 | `mattpocock-skills:to-prd` |
| 프로토타입 / 빠르게 시제품 / 설계 실험 / 목업 | `mattpocock-skills:prototype` |
| 아키텍처 개선 / 리팩터링 기회 / 결합도 / 테스트 쉽게 | `mattpocock-skills:improve-codebase-architecture` |
| 오피스아워 / 제품 아이디어 상담 / 사업 아이디어 | `gstack:office-hours` |
| CEO 리뷰 / 대표 관점 / 전략 리뷰 / 스코프 / 제품 비판 | `gstack:plan-ceo-review` |
| 엔지니어링 리뷰 / 아키텍처 리뷰 / 기술 계획 검토 / 설계 검토 | `gstack:plan-eng-review` |
| 디자인 계획 리뷰 / 디자인 관점 검토 | `gstack:plan-design-review` |
| 디자인 리뷰 / UX 검토 / UI 품질 / 화면 평가 / 시각 품질 | `gstack:design-review` |
| 스펙 작성 / 실행 스펙 / 요구사항 정밀화 / spec | `gstack:spec` |
| QA 테스트 / 웹 테스트 / 사이트 점검 | `gstack:qa` |
| 리포트만 / 수정하지 말고 QA / QA 리포트 | `gstack:qa-only` |
| 배포 / ship / PR 생성 / 릴리스 / 머지 후 푸시 | `gstack:ship` |
| 문서 갱신 / 릴리스 노트 / 문서 동기화 / 문서 드리프트 | `gstack:document-release` |
| 그래프화 / Graphify / 지식 그래프 / 코드·문서 관계 | `graphify:graphify` |

## 트리거 우선순위

- 사용자가 플러그인/스킬을 명시하면 그 요청이 우선한다.
- 여러 스킬이 맞으면 필요한 최소 조합만 쓴다.
- 넓은 아이디어 탐색 → `superpowers:brainstorming`, 구현 계획 → `superpowers:writing-plans`.
- 계획 비판은 문맥에 따라 `mattpocock-skills:grill-me` / `gstack:plan-ceo-review` / `gstack:plan-eng-review` / `gstack:plan-design-review` 중 하나.
- 정확성 위험 코드 변경 → `superpowers:test-driven-development` 고려. 디버깅 → `superpowers:systematic-debugging`. 독립 작업 명확할 때만 `superpowers:subagent-driven-development`.

## MCP 사용 규칙

- OpenAI 제품·Codex·OpenAI API 질문 → `openaiDeveloperDocs`
- Microsoft·Azure·.NET 질문 → `microsoftLearn`
- Anthropic/Claude 공식 문서 → `anthropicDocs`
- GitHub repo·issue·PR·release → `github`

## 최종 응답 공개

`reply-trace` 플러그인(skill + UserPromptSubmit 훅, github.com/akashi-ueda/reply-trace)이 담당한다. 자동 사용한 플러그인/스킬/MCP/서브에이전트/훅을 응답 마지막 한 줄로 공개하며, 매 턴 훅이 포맷을 주입한다. 언어는 `REPLY_TRACE_LOCALE=ko`(레거시 `AGENT_ATTRIBUTION_*` fallback 허용).
