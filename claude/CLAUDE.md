## 전역 응답 스타일

에이전트 전역 설정은 여러 환경에서 빠르게 재구축할 수 있도록 SSOT 저장소로 관리한다. Claude 전역 규칙·플러그인·스킬·MCP·훅 등 에이전트 설정을 바꾼 경우, 관리 저장소의 관련 파일을 갱신한 뒤 원격 저장소까지 push한다.

caveman 압축 모드는 `caveman` 플러그인의 SessionStart 훅이 매 세션 자동 활성화한다(별도 기본-스타일 텍스트 불필요). 끄기: "normal mode" 또는 "stop caveman". 레벨 전환: `/caveman lite|full|ultra`.

전역 설정 동기화는 훅이 아니라 **지침**으로 한다. Claude/Codex 전역 규칙·플러그인·스킬·MCP·훅을 바꾸면(또는 사용자가 바꿔달라 하면) 그 작업 끝에 `python ~/ai-agent-config/scripts/sync.py claude`를 실행한다. 이 스크립트가 live→repo 미러(`capture.py`) 후 관리 경로만 commit하고 `pull --rebase` 후 push까지 한다. 설정을 안 바꿨으면 실행하지 않는다. Windows도 `%USERPROFILE%\ai-agent-config` 기준이며 다른 위치는 `AI_AGENT_CONFIG_REPO`로 지정한다.

## Claude 플러그인/스킬 출처

- Claude plugin 설정은 `C:\Users\ENITEC\.claude\plugins` 아래에서 관리한다.
- 활성 Claude plugin 목록은 `C:\Users\ENITEC\.claude\plugins\installed_plugins.json`과 `C:\Users\ENITEC\.claude\settings.json`을 기준으로 한다.
- `gstack`, `mattpocock-skills`는 `personal-local` marketplace에서 관리한다.
- `superpowers`, `caveman`, `harness`는 각 공식 marketplace 또는 공식 repo marketplace 설치를 우선한다.
- `graphify`는 `personal-local` plugin과 `graphifyy` CLI로 사용한다.
- Claude에서는 `C:\Users\ENITEC\.agents`를 공유 스킬 저장소로 사용하지 않는다. Codex personal marketplace metadata와 분리한다.
- `~/.claude/skills` 같은 standalone skills 폴더는 install이 만들거나 수정하지 않는다. 모든 스킬 노출은 plugin으로 처리한다.
- `superpowers`, `caveman`, `harness`처럼 marketplace에 있는 plugin은 공식/원본 marketplace에서 설치한다.
- 한국어 표시 설명은 Claude 설치본의 `description:` 한 줄 치환과 `C:\Users\ENITEC\.claude\tools\skill-descriptions.ko.map.json`을 기준으로 관리한다.
- upstream repo 원본은 수정하지 않는다. 한국어 description은 설치본 copy에만 적용한다.

## 설치된 Claude 플러그인/스킬

설치 플러그인 집합은 `manifest/plugins.json`(SSOT)에 선언된다. 플러그인을 추가·변경하려면 그 파일을 편집하거나 `refresh-plugins` 스킬로 drift PR을 열고, 이후 `install.*`을 재실행한다.

현재 Claude에서 사용하는 항목:

- `superpowers:*`: 계획, TDD, 디버깅, 검증, 병렬 작업 방법론.
- `caveman:*`: 압축 응답, 커밋/리뷰/압축 보조 스킬.
- `harness:harness`: 에이전트 하네스와 전문 에이전트/스킬 설계.
- `graphify:graphify`: 코드, 문서, 아키텍처 관계를 지식 그래프로 탐색.
- `gstack:gstack-*`: 웹 QA, spec, ship, 보안, office-hours, 계획 리뷰, 디자인 리뷰, 문서화, 회고, context, guard 계열.
- `mattpocock-skills:*`: grill, triage, issue 분해, PRD, prototype, architecture 개선, handoff, skill 작성, pre-commit, git guardrail.
- `codex:rescue`: 막혔을 때 Codex CLI에 조사/수정/검토를 위임하는 보조 런타임.
- Claude built-in: `code-review`, `security-review`, `verify`, `review`, `simplify` 등은 항상 사용 가능하다.

## 한국어 자동 트리거

- "짧게", "토큰 줄여", "간단히", "압축해서", "요약해서", "caveman" -> `caveman:caveman`
- "커밋 메시지", "커밋 써줘", "/commit" -> `caveman:caveman-commit`
- "아이디어", "브레인스토밍", "요구사항 정리", "방향 잡자", "뭘 만들지 같이 생각" -> `superpowers:brainstorming`
- "계획 세워", "구현 계획", "작업 순서", "단계별", "멀티스텝", "플랜 작성" -> `superpowers:writing-plans`
- "계획 실행", "플랜대로 진행", "체크포인트 두고 구현" -> `superpowers:executing-plans`
- "TDD", "테스트 주도", "테스트 먼저", "레드 그린", "red green" -> `superpowers:test-driven-development`
- "서브에이전트", "병렬 개발", "작업 나눠", "독립 작업", "여러 에이전트" -> `superpowers:subagent-driven-development`
- "워크트리", "git worktree", "격리 작업", "현재 변경 보호", "별도 작업공간" -> `superpowers:using-git-worktrees`
- "디버깅", "원인 추적", "버그 원인", "체계적으로 조사", "재현" -> `superpowers:systematic-debugging`
- "검증", "완료 전 확인", "테스트 확인", "증거 확인" -> `superpowers:verification-before-completion`
- "코드리뷰", "diff 리뷰", "PR 리뷰", "변경 검토" -> built-in `code-review`
- "보안 리뷰", "취약점 점검", "OWASP", "STRIDE", "보안 감사" -> `gstack:gstack-cso` 또는 built-in `security-review`
- "그릴", "grill", "계획 검증", "날카롭게 질문", "집요하게 물어봐", "내 계획 털어봐" -> `mattpocock-skills:grill-me`
- "문서 기준 그릴", "ADR 기준", "CONTEXT 기준", "도메인 용어 기준", "문서 보면서 질문" -> `mattpocock-skills:grill-with-docs`
- "이슈 분류", "트리아지", "버그 정리", "백로그 정리" -> `mattpocock-skills:triage`
- "이슈로 쪼개", "티켓 만들어", "작업 분해", "계획을 이슈로", "구현 이슈" -> `mattpocock-skills:to-issues`
- "PRD", "제품 요구사항 문서", "요구사항 문서화", "대화를 PRD로" -> `mattpocock-skills:to-prd`
- "프로토타입", "빠르게 시제품", "설계 실험", "목업", "여러 UI 안" -> `mattpocock-skills:prototype`
- "아키텍처 개선", "리팩터링 기회", "결합도 줄이기", "테스트 쉽게", "코드 구조 개선" -> `mattpocock-skills:improve-codebase-architecture`
- "오피스아워", "제품 아이디어 상담", "스타트업 아이디어", "이거 만들 가치", "사업 아이디어" -> `gstack:gstack-office-hours`
- "CEO 리뷰", "대표 관점", "사업 관점", "전략 리뷰", "스코프 키워", "스코프 줄여", "제품 비판" -> `gstack:gstack-plan-ceo-review`
- "엔지니어링 리뷰", "아키텍처 리뷰", "기술 계획 검토", "실행 계획 검토", "설계 검토" -> `gstack:gstack-plan-eng-review`
- "디자인 계획 리뷰", "디자인 관점 검토" -> `gstack:gstack-plan-design-review`
- "디자인 리뷰", "UX 검토", "UI 품질", "화면 평가", "시각적 품질", "디자인 폴리시" -> `gstack:gstack-design-review`
- "스펙 작성", "실행 스펙", "요구사항 정밀화", "spec" -> `gstack:gstack-spec`
- "QA 테스트", "웹 테스트", "브라우저로 확인", "사이트 점검" -> `gstack:gstack-qa`
- "리포트만", "수정하지 말고 QA", "QA 리포트" -> `gstack:gstack-qa-only`
- "배포", "ship", "PR 생성", "릴리스", "머지 후 푸시" -> `gstack:gstack-ship`
- "문서 갱신", "릴리스 노트", "문서 동기화", "문서 드리프트" -> `gstack:gstack-document-release`
- "그래프화", "Graphify", "지식 그래프", "관계 그래프", "코드 관계", "문서 관계", "그래프로 조사" -> `graphify`
- "하네스", "에이전트 하네스", "하네스 설계", "하네스 구축", "하네스 구성", "하네스 엔지니어링", "에이전트/스킬 동기화", "에이전트 하네스 작성" -> `harness:harness`
- "코덱스에 넘겨", "막혔어 코덱스", "second opinion", "코덱스 리뷰", "코덱스한테 물어봐" -> `codex:rescue`

## 트리거 우선순위

- 사용자가 플러그인이나 스킬을 명시하면 그 요청이 우선한다.
- 여러 스킬이 맞으면 필요한 최소 조합만 사용한다.
- 넓은 아이디어 탐색은 `superpowers:brainstorming`을 우선한다.
- 구현 계획은 `superpowers:writing-plans`를 우선한다.
- 계획 비판은 문맥에 따라 `mattpocock-skills:grill-me`, `gstack:gstack-plan-ceo-review`, `gstack:gstack-plan-eng-review`, `gstack:gstack-plan-design-review` 중 하나를 고른다.
- 코드 리뷰 실행은 built-in `code-review`를 우선한다. `superpowers:requesting-code-review`와 `superpowers:receiving-code-review`는 리뷰 요청/수용 프로세스용으로만 쓴다.
- 정확성 위험이 있는 코드 변경은 `superpowers:test-driven-development`를 고려한다.
- 독립 작업이 명확할 때만 `superpowers:subagent-driven-development`를 사용한다.
- 디버깅은 `superpowers:systematic-debugging`을 우선한다.
- 기능별 기본 역할은 방법론 `superpowers`, 코드리뷰 실행 built-in `code-review`, Codex 위임 `codex:rescue`, 웹/제품 워크플로 `gstack`, 이슈/그릴/프로토타입 `mattpocock-skills`로 둔다.

## 최종 응답 공개

`reply-trace` 플러그인(skill + UserPromptSubmit 훅, github.com/akashi-ueda/reply-trace)이 담당한다. 자동 사용한 플러그인/스킬/MCP/서브에이전트/훅을 응답 마지막 한 줄로 공개하며, 매 턴 훅이 포맷을 주입한다. 언어는 `REPLY_TRACE_LOCALE=ko`로 한국어 고정(레거시 `AGENT_ATTRIBUTION_*`도 fallback 허용).
