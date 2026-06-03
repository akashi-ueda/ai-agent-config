## 전역 응답 스타일

caveman 압축 모드는 전역 훅 `~/.codex/hooks.json`(SessionStart·UserPromptSubmit → `hooks/caveman.py`)이 매 세션·매 턴 자동 주입한다. 별도 텍스트 지시 불필요. 끄기: "normal mode" 또는 "stop caveman".

전역 설정 동기화는 훅이 아니라 **지침**으로 한다. Claude/Codex 전역 규칙·플러그인·스킬·MCP·훅을 바꾸면(또는 사용자가 바꿔달라 하면) 그 작업 끝에 `python ~/ai-agent-config/scripts/sync.py codex`를 실행한다. 이 스크립트가 live→repo 미러(`capture.py`) 후 관리 경로만 commit하고 `pull --rebase` 후 push까지 한다. 설정을 안 바꿨으면 실행하지 않는다. Windows도 `%USERPROFILE%\ai-agent-config` 기준이며 다른 위치는 `AI_AGENT_CONFIG_REPO`로 지정한다.

## Codex 플러그인/스킬 출처

- Codex personal marketplace 파일은 `C:\Users\ENITEC\.agents\plugins\marketplace.json`이다.
- Codex local personal 플러그인 원본은 `C:\Users\ENITEC\.codex\plugins\<plugin-name>`에 둔다.
- Codex 설치 캐시는 `C:\Users\ENITEC\.codex\plugins\cache\personal\<plugin-name>\<version>`에 생성된다.
- 이 구조는 OpenAI Codex 공식 personal marketplace 규칙을 따른다. marketplace root는 `C:\Users\ENITEC`이고, 각 entry의 `source.path`는 `./.codex/plugins/<plugin-name>` 형식이어야 한다.
- `C:\Users\ENITEC\.agents`는 Codex marketplace metadata 전용으로만 사용한다. 공유 스킬이나 Claude용 파일을 넣지 않는다.
- 한국어 표시 설명은 `C:\Users\ENITEC\.codex\skill-descriptions.ko.json`과 설치된 Codex plugin copy의 `SKILL.md` frontmatter `description`에 둔다.
- upstream repo의 원본 `SKILL.md`는 수정하지 않는다. 한국어 description 변경은 Codex 설치본 copy에만 허용한다.
- `~/.codex/skills`·`~/.agents/skills` 같은 standalone skills 폴더는 사용하지 않는다. 모든 스킬은 plugin으로만 노출한다.
- `superpowers`처럼 Codex store/curated에 있는 플러그인은 `openai-curated` 공식 marketplace에서 설치한다.

## 설치된 Codex 플러그인

현재 Codex에서 사용하는 플러그인:

- `superpowers@openai-curated`: 계획, TDD, 디버깅, 검증, 병렬 작업 방법론.
- `graphify@personal`: 코드, 문서, 아키텍처 관계를 지식 그래프로 탐색.
- `gstack@personal`: 제품, 계획, 디자인 리뷰, QA, 보안, 문서화, spec, ship 워크플로.
- `mattpocock-skills@personal`: grill, triage, issue 분해, PRD, prototype, architecture 개선.

스킬은 실제 Codex id 형식인 `plugin:skill`로 참조한다.

## 한국어 자동 트리거

- "짧게", "토큰 줄여", "간단히", "압축해서", "요약해서", "caveman" -> caveman 전역 훅 압축 모드
- "아이디어", "브레인스토밍", "요구사항 정리", "방향 잡자", "뭘 만들지 같이 생각" -> `superpowers:brainstorming`
- "계획 세워", "구현 계획", "작업 순서", "단계별", "멀티스텝", "플랜 작성" -> `superpowers:writing-plans`
- "계획 실행", "플랜대로 진행", "체크포인트 두고 구현" -> `superpowers:executing-plans`
- "TDD", "테스트 주도", "테스트 먼저", "레드 그린", "red green" -> `superpowers:test-driven-development`
- "서브에이전트", "병렬 개발", "작업 나눠", "독립 작업", "여러 에이전트" -> `superpowers:subagent-driven-development`
- "워크트리", "git worktree", "격리 작업", "현재 변경 보호", "별도 작업공간" -> `superpowers:using-git-worktrees`
- "디버깅", "원인 추적", "버그 원인", "체계적으로 조사", "재현" -> `superpowers:systematic-debugging`
- "검증", "완료 전 확인", "테스트 확인", "증거 확인" -> `superpowers:verification-before-completion`
- "그릴", "grill", "계획 검증", "날카롭게 질문", "집요하게 물어봐", "내 계획 털어봐" -> `mattpocock-skills:grill-me`
- "문서 기준 그릴", "ADR 기준", "CONTEXT 기준", "도메인 용어 기준", "문서 보면서 질문" -> `mattpocock-skills:grill-with-docs`
- "이슈 분류", "트리아지", "버그 정리", "백로그 정리" -> `mattpocock-skills:triage`
- "이슈로 쪼개", "티켓 만들어", "작업 분해", "계획을 이슈로", "구현 이슈" -> `mattpocock-skills:to-issues`
- "PRD", "제품 요구사항 문서", "요구사항 문서화", "대화를 PRD로" -> `mattpocock-skills:to-prd`
- "프로토타입", "빠르게 시제품", "설계 실험", "목업", "여러 UI 안" -> `mattpocock-skills:prototype`
- "아키텍처 개선", "리팩터링 기회", "결합도 줄이기", "테스트 쉽게", "코드 구조 개선" -> `mattpocock-skills:improve-codebase-architecture`
- "오피스아워", "제품 아이디어 상담", "스타트업 아이디어", "이거 만들 가치", "사업 아이디어" -> `gstack:office-hours`
- "CEO 리뷰", "대표 관점", "사업 관점", "전략 리뷰", "스코프 키워", "스코프 줄여", "제품 비판" -> `gstack:plan-ceo-review`
- "엔지니어링 리뷰", "아키텍처 리뷰", "기술 계획 검토", "실행 계획 검토", "설계 검토" -> `gstack:plan-eng-review`
- "디자인 계획 리뷰", "디자인 관점 검토" -> `gstack:plan-design-review`
- "디자인 리뷰", "UX 검토", "UI 품질", "화면 평가", "시각적 품질", "디자인 폴리시" -> `gstack:design-review`
- "스펙 작성", "실행 스펙", "요구사항 정밀화", "spec" -> `gstack:spec`
- "QA 테스트", "웹 테스트", "사이트 점검" -> `gstack:qa`
- "리포트만", "수정하지 말고 QA", "QA 리포트" -> `gstack:qa-only`
- "배포", "ship", "PR 생성", "릴리스", "머지 후 푸시" -> `gstack:ship`
- "문서 갱신", "릴리스 노트", "문서 동기화", "문서 드리프트" -> `gstack:document-release`
- "그래프화", "Graphify", "지식 그래프", "관계 그래프", "코드 관계", "문서 관계", "그래프로 조사" -> `graphify:graphify`

## 트리거 우선순위

- 사용자가 플러그인이나 스킬을 명시하면 그 요청이 우선한다.
- 여러 스킬이 맞으면 필요한 최소 조합만 사용한다.
- 넓은 아이디어 탐색은 `superpowers:brainstorming`을 우선한다.
- 구현 계획은 `superpowers:writing-plans`를 우선한다.
- 계획 비판은 문맥에 따라 `mattpocock-skills:grill-me`, `gstack:plan-ceo-review`, `gstack:plan-eng-review`, `gstack:plan-design-review` 중 하나를 고른다.
- 정확성 위험이 있는 코드 변경은 `superpowers:test-driven-development`를 고려한다.
- 독립 작업이 명확할 때만 `superpowers:subagent-driven-development`를 사용한다.
- 디버깅은 `superpowers:systematic-debugging`을 우선한다.

## MCP 사용 규칙

- OpenAI 제품, Codex, OpenAI API, Codex plugin 관련 질문은 `openaiDeveloperDocs` MCP를 우선 사용한다.
- Microsoft, Azure, .NET 관련 질문은 `microsoftLearn` MCP를 우선 사용한다.
- Anthropic/Claude 공식 문서 확인이 필요하면 `anthropicDocs` MCP를 사용한다.
- GitHub repo, issue, PR, release 확인은 GitHub MCP를 우선 사용한다.

## 최종 응답 공개

`attribution` 플러그인(skill + UserPromptSubmit 훅, github.com/akashi-ueda/agent-attribution)이 담당한다. 자동 사용한 스킬/MCP/훅을 응답 마지막 한 줄로 공개하며, 매 턴 훅이 포맷을 주입한다. 언어는 `AGENT_ATTRIBUTION_LOCALE=ko`로 한국어 고정.
