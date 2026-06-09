# personal-agent-config

Windows ↔ macOS 공유용 AI 에이전트(Claude Code · Codex) 설정 SSOT.
git가 저장·머지·이력을, `apply.py`/`install.*`가 OS별 적용을 담당한다.

이 저장소의 목적은 어떤 환경에서든 에이전트 설정을 빠르게 재구축하는 것이다.
에이전트 설정을 바꾼 작업자는 반드시 관련 파일을 갱신하고 원격 저장소까지 push한다.

전제: 이 repo는 홈 바로 아래 `~/personal-agent-config`에 clone한다. Windows도
`C:\Users\<유저명>\personal-agent-config` 기준이다. 다른 위치면
`PERSONAL_AGENT_CONFIG_REPO` 환경변수로 repo 경로를 지정한다.

설치 전제: Node.js, Python(+pip), Claude Code CLI(`claude`), Codex CLI(`codex`)는
이미 설치되어 있고 PATH에서 실행 가능해야 한다. install 스크립트는 이 기본
런타임들을 설치하지 않는다.

## 무엇이 동기화되나
- **Claude**: `CLAUDE.md`, `settings.json`(훅·권한), `tools/`(한국어 설명 스크립트), MCP 정의, `personal-local` 래퍼(gstack/mattpocock/graphify SKILL.md).
- **Codex**: `AGENTS.md`, config 포터블 키, MCP 정의, personal plugin wrappers(gstack/mattpocock/graphify/caveman/reply-trace).
- **지침 기반 역동기화**: 전역 규칙·플러그인·스킬·MCP·훅을 바꾸면 에이전트가 `scripts/sync.py`를 실행해 live→repo 미러+commit+push (매 프롬프트 훅 아님).
- **플러그인**: `manifest/plugins.json`(SSOT)을 `install_plugins.py`가 읽어 양쪽 호스트(Claude·Codex)에 설치. graphify pip 설치·gstack bun 빌드도 엔진이 처리.

## 동기화 안 되는 것 (머신 전용/재생성)
plugins 캐시·sessions·projects·backups·`.credentials.json`, Codex `node_repl`/`hooks.state`/`marketplaces`/`projects`/`[windows]`, gstack 빌드 바이너리(`browse.exe` 등), graphify/gstack 외부 CLI 설치물, 모든 비밀 값.

## 시크릿키
GitHub MCP 토큰은 `~/.config/github-mcp/env`에 저장한다. `.env`(gitignore)는 최초 설치 seed로만 쓰며, install이 `.env` 값을 공용 env 파일로 옮긴다. Claude/Codex MCP 설정은 `${GITHUB_PERSONAL_ACCESS_TOKEN}` 환경변수를 공통 참조한다.

## 최초 셋업 (새 Mac)
```bash
git clone <repo-url> ~/personal-agent-config && cd ~/personal-agent-config
cp .env.example .env             # 값 채우기
./install.sh                     # 적용 + 플러그인 재설치 + 검증
# 토큰은 install 후 ~/.config/github-mcp/env로 이동/공유
# Claude/Codex 재시작, Codex 전역 훅 신뢰 1회 승인
```
Windows:
```powershell
git clone <repo-url> $HOME\personal-agent-config; cd $HOME\personal-agent-config
Copy-Item .env.example .env             # 값 채우기
powershell -ExecutionPolicy Bypass -File install.ps1
# 토큰은 install 후 ~/.config\github-mcp\env로 이동/공유
```

## install 스크립트가 설정하는 것
- **공통 비밀/env**: `.env` 또는 `~/.config/github-mcp/env`에서 `GITHUB_PERSONAL_ACCESS_TOKEN`을 읽고, 공용 토큰 파일 `~/.config/github-mcp/env`에 저장한다. macOS/Linux는 `~/.zshrc`가 이 파일을 source하도록 보강한다.
- **파일 배치**: `apply.py`가 Claude/Codex 설정 파일(CLAUDE.md, AGENTS.md, settings.json 등)을 repo에서 live 위치로 복사하고 MCP/config를 병합한다.
- **Codex 훅 정리**: legacy 전역 `~/.codex/hooks.json`의 caveman/reply-trace 훅은 제거하고, `caveman@personal`·`reply-trace@personal` 플러그인에 번들된 `hooks/hooks.json`으로 관리한다.
- **플러그인 설치**: `install_plugins.py`가 `manifest/plugins.json`을 읽어 Claude·Codex 양쪽 호스트에 모든 플러그인을 설치한다. marketplace 등록, store/local/codex install, graphify pip 설치, gstack bun 빌드까지 엔진이 처리한다.
- **한국어 설명/검증**: Claude skill 설명 한국어 매핑을 적용하고, 마지막에 `install_plugins.py --dry-run`으로 설치 상태를 확인한다.

## 플러그인 추가·갱신
- 플러그인을 추가하거나 변경할 때는 `manifest/plugins.json`을 직접 편집한 뒤 `install.*`을 다시 실행한다.
- upstream 플러그인의 identifier·버전 드리프트를 감지하려면 `refresh-plugins` 스킬을 사용한다. 이 스킬은 각 플러그인 repo의 구조화된 파일을 읽어 drift를 분류하고 manifest-diff PR을 열어준다(설치는 하지 않음). PR을 리뷰·머지한 뒤 `install.*`을 재실행한다.

## 플러그인 저장소

| 플러그인 | 저장소 | 설치 경로 |
|----------|--------|-----------|
| harness | https://github.com/revfactory/harness | claude marketplace |
| caveman | https://github.com/JuliusBrussee/caveman | claude marketplace / codex local |
| superpowers | https://github.com/anthropics/claude-plugins-official | claude marketplace / codex store(`openai-curated`) |
| codex | https://github.com/openai/codex-plugin-cc | claude marketplace |
| reply-trace | https://github.com/akashi-ueda/reply-trace | claude marketplace / codex local |
| gstack | https://github.com/garrytan/gstack | personal-local + `~/.gstack/core` bun 빌드 |
| mattpocock-skills | https://github.com/mattpocock/skills | personal-local |
| graphify | `graphifyy` (PyPI) | personal-local + pip CLI |
| refresh-plugins | 이 repo `claude/personal-local/plugins/refresh-plugins` | personal-local |

권위 출처는 `manifest/plugins.json`(SSOT). 표는 사람이 읽기 위한 요약이다.

## 운영 (플러그인 엔진)

설치/검증은 `scripts/install_plugins.py`가 담당한다. `manifest/plugins.json`을 읽어 method별 핸들러로 양쪽 호스트에 설치한다.

명령:
```bash
python scripts/install_plugins.py --dry-run        # 실행 계획만 출력(CLI 미호출). 안전 확인용
python scripts/install_plugins.py --verify-installed # 실제 설치 상태 검증(plan 아님): manifest 플러그인이 전부 installed+enabled인지, 아니면 exit 1
python scripts/install_plugins.py                  # 실제 설치(멱등: 이미 깔린 건 skip)
python scripts/install_plugins.py --only gstack    # 한 플러그인만
python scripts/install_plugins.py --host codex     # 한 호스트만(claude|codex)
python scripts/apply.py --host claude              # 파일 적용도 한 호스트만(Claude만 건드림)
python scripts/install_plugins.py --prune          # manifest에 없는데 live에 남은 orphan 제거(옵트인)
python -m unittest discover -s tests               # 헬퍼 단위테스트
```

동작 원리:
- **멱등**: 이미 설치·활성이면 `skip`. `codex plugin add`는 재실행 시 캐시 백업 `os error 5`가 나므로, 설치돼 있으면 add 자체를 건너뛴다. 최초 설치는 백업이 없어 정상 동작.
- **orphan**: 기본 실행은 manifest에 없는 live 플러그인을 리포트만 한다. 실제 제거는 `--prune`로만(파괴적이라 옵트인). `refresh-plugins` 스킬도 PR에 orphan을 표기한다.
- **glue 격리**: OS별 처리(UTF-8 디코드, BOM-safe 복사, pip 폴백, 버전폴더 shim, gstack용 bash 탐지, marketplace upsert)는 `scripts/lib/glue.py`에만 있다. method 핸들러·manifest는 OS 무관.
- **호스트 스코프**: `apply.py`·`install_plugins.py` 모두 `--host claude|codex`로 한 에이전트만 적용한다(없으면 양쪽). external 단계(pip/build)는 manifest의 `host` 필드(claude|codex|both, 기본 both)로 태깅돼, 공유 CLI/바이너리(graphify pip, gstack core)는 `--host claude`에도 포함된다.
- **설치 검증**: `--dry-run`은 실행 *계획*만 본다. `--verify-installed`는 `claude/codex plugin list`를 실제 파싱해 manifest의 모든 플러그인이 installed+enabled인지 단언하고 아니면 exit 1 — install 래퍼의 마지막 단계가 이걸 호출한다(실패 시 설치 전체 실패 처리). 설치는 에이전트 개입 없이 스크립트만으로 완전해야 한다는 불변식의 가드레일.
- **드리프트 방지**: 등록 marketplace명과 plugin id를 manifest에 명시 필드로 둔다(소스 repo명과 다를 수 있음 — 예 `akashi-ueda/reply-trace` → mk `reply-trace`).

문제 해결:
- Codex 플러그인 내용을 바꿨는데 안 보임: 캐시는 `codex plugin add` 시에만 갱신된다. `os error 5`로 재-add가 막히면 `codex plugin remove <id>@personal` 후 다시 `install_plugins.py`.
- Codex 플러그인 번들 훅이 안 뜸: 플러그인이 `installed, enabled` 상태인지 `codex plugin list`로 확인하고, Codex 재시작 후 `/hooks`에서 새 hook을 trust한다.
- gstack 스킬이 Codex 목록에 없음: SKILL.md에 BOM이 붙으면 frontmatter 파싱이 깨진다. 엔진은 BOM 없는 UTF-8로 쓴다(`bom_safe_copy`). 의심되면 첫 3바이트가 `2D 2D 2D`(`---`)인지 확인.
- gstack 빌드 skip: `bun`/`bash`(Windows는 Git `usr\bin`) 부재 시 빌드를 건너뛰고 repo fallback skill copy를 쓴다.

## 일상 워크플로 (양방향)
- **받기(pull)**: `git pull` → `./install.sh`(또는 `install.ps1`).
- **보내기(push, 지침)**: 전역 설정을 바꾸면 `python scripts/sync.py [claude|codex]` 실행 →
  `capture.py`로 미러 → 관리 경로만 stage → 커밋 → `pull --rebase --autostash` 후 push.
  origin이 앞서 rebase 충돌이면 abort+안내만, 강제 안 함. `--no-push`로 로컬 커밋만, `-m "msg"`로 메시지 지정.
  CLAUDE.md/AGENTS.md가 에이전트에게 설정 변경 후 이 명령을 실행하도록 지시한다(매 프롬프트 훅 아님).
- **보내기(push, 수동)**: `python scripts/capture.py` → `git diff` 확인 → `git commit` → `git push`.
- **인증**: push는 git credential helper(macOS keychain 등)에 의존. 새 PC는 최초 1회 수동 push로 캐시.
- capture는 토큰류(`ghp_`/`github_pat_`/`sk-`/`Bearer …`)를 `{{REDACTED}}`로 마스킹해 유출 방지. 비밀은 `${ENV}` 참조로만.
- 충돌은 대부분 `CLAUDE.md`/`AGENTS.md` 텍스트. git로 머지.

## 변경 관리 정책

브랜치 모델은 **git-flow**: `main`(릴리스·보호) ← `develop`(통합) ← `feat/*`(기능). 두 에이전트(Claude·Codex)가 같은 repo를 공유 편집하므로 변경 종류로 경로를 나눈다.

| 변경 종류 | 경로 |
|-----------|------|
| **관리 설정 미러** (CLAUDE.md·AGENTS.md·settings·MCP 등 capture 대상) | `develop`에서 `sync.py`로 직접 push (멱등·저위험) |
| **코드·설치엔진·manifest·플러그인·CI** (`scripts/`·`install.*`·`manifest/`·`claude/personal-local` 등) | `feat/<주제>` 브랜치 + `develop` 대상 PR (비자명하면 이슈 먼저), CI 통과까지만 |
| **릴리스** | `develop` → `main` PR |

**브랜치 보호**: `main`은 PR + CI(`test`) 필수, force-push·삭제 금지(릴리스 PR로만 갱신). `develop`은 force-push·삭제 금지(직접 push 허용).

**머지 게이트**: PR의 머지·클로즈 판단은 **사람(저장소 소유자)**이 한다. 에이전트는 PR/이슈를 열고 CI를 통과시키는 데까지만 관여하며, 사용자가 명시적으로 요청할 때만 머지한다. `main`엔 직접 push하지 않는다. 운영 규칙 본문은 `claude/CLAUDE.md` / `codex/AGENTS.md`의 "변경 관리 정책" 절에 있다.

## 릴리스 (CD)

`main`은 릴리스 브랜치다. `develop` → `main` 릴리스 PR에서 `VERSION`(SemVer)을 bump해 머지하면 `.github/workflows/release.yml`이 자동으로:
- `v<VERSION>` 태그 생성·push,
- 자동 생성 노트(`--generate-notes`)로 GitHub Release 발행.

같은 `VERSION`이면 멱등(이미 릴리스 있으면 skip). 머신 자동 배포는 하지 않는다(pull 기반 `install.sh` 유지) — 릴리스는 stable 스냅샷을 pin/추적하기 위한 것.

## 경로 템플릿
`{{CODEX_HOME}}`, `{{CLAUDE_HOME}}` →
`apply.py`가 OS 기준으로 치환.

## 구성요소
| 파일 | 역할 |
|------|------|
| `scripts/apply.py` | repo→live 파일 적용·렌더·MCP/config 머지 (크로스플랫폼) |
| `scripts/capture.py` | live→repo 캡처·재템플릿화·시크릿 마스킹 |
| `scripts/sync.py` | capture + 관리경로 commit + rebase&push (설정 변경 후 지침으로 실행) |
| `scripts/install_plugins.py` | manifest-driven 플러그인 설치 엔진 (Claude·Codex 양쪽 처리) |
| `scripts/lib/glue.py` | method handler 라우팅 |
| `scripts/lib/manifest.py` | manifest/plugins.json 파싱 |
| `scripts/lib/methods.py` | 각 install method 구현(claude_marketplace, claude_local, codex_local, external_cli, built_binary, codex_store) |
| `install.sh` / `install.ps1` | dep 체크·secrets 처리 후 apply.py → install_plugins.py → ko-desc → dry-run 검증 |
| `manifest/plugins.json` | 플러그인 SSOT 선언 (구 `manifest/{claude,codex}-plugins.json`은 제거됨) |
| `codex/config.portable.toml` | 머지되는 Codex 포터블 키만 |
| `claude/mcp.portable.json` | 머지되는 MCP 정의 |

## 주의
- 에이전트별 standalone skills 폴더(`~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`)는 install이 만들거나 수정하지 않는다. 모든 스킬 노출은 plugin 경유.
- store/curated plugin(예: Codex `superpowers@openai-curated`, Claude `superpowers@claude-plugins-official`)은 공식 marketplace에서 받는다.
- gstack/mattpocock/graphify는 local personal plugin으로만 사용한다. Claude는 `personal-local`, Codex는 `~/.agents/plugins/marketplace.json` + `~/.codex/plugins/<name>` 구조.
- gstack 코어 repo는 `~/.gstack/core`에 둔다. plugin SKILL.md는 gstack bin을 `~/.gstack/core/bin`에서 찾는다. `~/.gstack` 루트는 gstack 데이터(`projects/` 등)도 함께 보관한다.
- graphify는 `pip install --user graphifyy`(없으면 `pip3`)로 CLI만 설치하고, agent skill 등록은 `graphify@personal-local` / `graphify@personal` plugin이 담당한다.
- Node.js/Python/Claude Code CLI/Codex CLI는 사전 설치 전제다. 없으면 install이 실패한다.
- gstack core 빌드는 `bun`이 있으면 수행한다. `bun`이 없으면 경고만 출력하고 기존/로컬 plugin skill copy를 사용한다.
- `apply.py`의 Codex config 머지는 포터블 테이블만 교체하고 머신 섹션은 보존한다. 큰 변경 전 `~/.codex/config.toml` 백업 권장.
