# Claude Code 전역 지침

경로는 `~/.claude`, `~/.codex`, `~/.agents` 기준. Windows는 `%USERPROFILE%\.claude` 등으로 대응.

## 응답 스타일

caveman 압축 모드는 `caveman` 플러그인 훅(SessionStart·UserPromptSubmit)이 매 세션·매 턴 자동 주입한다. 여기에 스타일 규칙을 인라인하지 않는다. 끄기: "normal mode" / "stop caveman". 레벨: `/caveman lite|full|ultra`.

## 설정 동기화 (지침)

에이전트 전역 설정은 여러 환경에서 빠르게 재구축하도록 SSOT 저장소(`~/personal-agent-config`)로 관리한다. 전역 규칙·플러그인·스킬·MCP·훅을 바꾸면(또는 사용자가 바꿔달라 하면) 그 작업 끝에 `python ~/personal-agent-config/scripts/sync.py claude`를 실행한다. 스크립트가 live→repo 미러(`capture.py`) 후 관리 경로만 commit하고 `pull --rebase` 후 push한다. 설정을 안 바꿨으면 실행하지 않는다(매 프롬프트 훅 아님). repo 위치는 기본 `~/personal-agent-config`, 다르면 `PERSONAL_AGENT_CONFIG_REPO`로 지정.

## 변경 관리 정책

브랜치 모델은 **git-flow**: `main`(릴리스·보호) ← `develop`(통합) ← `feat/*`(기능). 두 에이전트(Claude·Codex)가 같은 repo를 공유 편집하므로 변경 종류로 경로를 나눈다:
- **관리 설정 미러**(CLAUDE.md·AGENTS.md·settings·MCP 등 capture 대상) → `develop`에서 `sync.py`로 직접 push 허용. 멱등·저위험.
- **코드·설치엔진·manifest·플러그인·CI 변경**(`scripts/`·`install.*`·`manifest/`·`claude/personal-local` 등) → `feat/<주제>` 브랜치 + `gh pr create`로 `develop` 대상 PR(비자명하면 이슈 먼저). CI 통과까지만.
- **릴리스**: `develop` → `main` PR. `main`은 PR+CI 필수·force/delete 금지로 보호된다.

**머지 게이트**: PR 머지·클로즈 판단은 사용자가 한다. 에이전트는 PR/이슈를 열고 CI를 통과시키는 데까지만 관여하며, 사용자가 명시적으로 요청할 때만 머지한다. `main`엔 직접 push하지 않는다.

**스택 PR 주의**: 스택 PR을 중간 base 브랜치로 머지하면 그 변경이 `develop`까지 자동으로 올라오지 않는다(중간 브랜치에만 안착해 stranding). 독립 변경은 전부 `develop` 직접 대상으로 연다. 스택이 불가피하면 bottom-up 순서로 즉시 머지하고 다음 PR base를 `develop`으로 재타깃한다. 머지 후 `git log origin/main..origin/develop`로 의도한 변경이 실제 안착했는지 확인한다.

**템플릿**: repo에 `.github/pull_request_template.md`·`.github/ISSUE_TEMPLATE/`가 있으면 PR·이슈 본문을 그 구조대로 채운다. `gh pr create --body`/`gh issue create --body`는 네이티브 템플릿을 우회하므로 본문에 직접 템플릿 섹션을 반영한다.

## 플러그인/스킬 출처

- 설치 플러그인 집합은 `manifest/plugins.json`(SSOT)에 선언된다. 추가·변경은 그 파일을 편집하거나 `refresh-plugins` 스킬로 drift PR을 연 뒤 `install.*`을 재실행한다.
- 모든 스킬은 **plugin으로만** 노출한다. `~/.claude/skills` 같은 standalone 폴더는 install이 만들거나 수정하지 않는다.
- `superpowers`·`caveman`·`harness`·`codex`·`reply-trace`는 각 공식/원본 marketplace에서, `gstack`·`mattpocock-skills`·`graphify`·`refresh-plugins`는 `personal-local` marketplace(= repo의 `claude/personal-local`)에서 설치한다.
- 활성 목록 기준은 `~/.claude/settings.json`(enabledPlugins). 설치된 스킬 카탈로그·한국어 트리거는 매 세션 주입되는 available-skills 목록과 각 스킬 `description:`이 제공하므로 여기 재서술하지 않는다.
- **설치=스크립트-온리 불변식**: 설치는 에이전트 개입 없이 스크립트만으로 완전해야 한다(SSOT 재구축 약속). 검증은 `python scripts/install_plugins.py --verify-installed`(plan 아닌 실제 설치 상태; 미충족 시 exit 1). 에이전트는 설치 *실행*이 아니라 설치 스크립트 *유지보수*를 담당한다.

## 스킬 선택·우선순위

- 사용자가 플러그인/스킬을 명시하면 그 요청이 우선. 여러 개 맞으면 최소 조합만.
- **process 스킬 먼저**(brainstorming·systematic-debugging) → 구현/도메인 스킬. "X 만들자"=brainstorming 먼저, "버그 고쳐"=debugging 먼저.
- 코드 리뷰 실행은 built-in `code-review` 우선. Codex 위임은 `codex:rescue`. 웹/제품 워크플로는 `gstack`. 이슈/그릴/프로토타입은 `mattpocock-skills`.
- 정확성 위험 코드 변경 → `superpowers:test-driven-development` 고려. 독립 작업 명확할 때만 `superpowers:subagent-driven-development`.
- 계획 비판은 문맥에 따라 `mattpocock-skills:grill-me` / `gstack:gstack-plan-{ceo,eng,design}-review` 중 하나.

## MCP 사용 규칙

- OpenAI 제품·Codex·OpenAI API 질문 → `openaiDeveloperDocs`
- Microsoft·Azure·.NET 질문 → `microsoftLearn`
- Anthropic/Claude 공식 문서 → `anthropicDocs`
- GitHub repo·issue·PR·release → `github`

## 최종 응답 공개

`reply-trace` 플러그인(skill + UserPromptSubmit 훅, github.com/akashi-ueda/reply-trace)이 담당한다. 자동 사용한 플러그인/스킬/MCP/서브에이전트/훅을 응답 마지막 한 줄로 공개하며, 매 턴 훅이 포맷을 주입한다. 언어는 `REPLY_TRACE_LOCALE=ko`(레거시 `AGENT_ATTRIBUTION_*` fallback 허용).
