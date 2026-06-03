# ai-agent-config

Windows ↔ macOS 공유용 AI 에이전트(Claude Code · Codex) 설정 SSOT.
git가 저장·머지·이력을, `apply.py`/`install.*`가 OS별 적용을 담당한다.

전제: 이 repo는 홈 바로 아래 `~/ai-agent-config`에 clone한다. Windows도
`C:\Users\<유저명>\ai-agent-config` 기준이다. 다른 위치면
`AI_AGENT_CONFIG_REPO` 환경변수로 repo 경로를 지정한다.

설치 전제: Node.js, Python(+pip), Claude Code CLI(`claude`), Codex CLI(`codex`)는
이미 설치되어 있고 PATH에서 실행 가능해야 한다. install 스크립트는 이 기본
런타임들을 설치하지 않는다.

## 무엇이 동기화되나
- **Claude**: `CLAUDE.md`, `settings.json`(훅·권한), `tools/`(한국어 설명 스크립트), MCP 정의, `personal-local` 래퍼(gstack/mattpocock/graphify SKILL.md).
- **Codex**: `AGENTS.md`, `hooks.json`(caveman), `hooks/caveman.py`, config 포터블 키, MCP 정의.
- **자동 역동기화 훅**: Claude/Codex 전역 규칙·플러그인·스킬·MCP·훅 변경 감지 시 live→repo capture.
- **플러그인**: store/curated plugin은 공식 marketplace에서 재설치, local skill pack은 personal plugin으로 복사 후 설치.

## 동기화 안 되는 것 (머신 전용/재생성)
plugins 캐시·sessions·projects·backups·`.credentials.json`, Codex `node_repl`/`hooks.state`/`marketplaces`/`projects`/`[windows]`, gstack 빌드 바이너리(`browse.exe` 등), graphify/gstack 외부 CLI 설치물, 모든 비밀 값.

## 비밀
GitHub MCP 토큰은 `~/.config/github-mcp/env`에 저장한다. `.env`(gitignore)는 최초 설치 seed로만 쓰며, install이 `.env` 값을 공용 env 파일로 옮긴다. Claude/Codex MCP 설정은 `${GITHUB_PERSONAL_ACCESS_TOKEN}` 환경변수를 공통 참조한다.

## 최초 셋업 (새 Mac)
```bash
git clone <repo-url> ~/ai-agent-config && cd ~/ai-agent-config
cp templates/.env.example .env   # 값 채우기
./install.sh                     # 적용 + 플러그인 재설치 + 검증
# 토큰은 install 후 ~/.config/github-mcp/env로 이동/공유
# Claude/Codex 재시작, Codex 전역 훅 신뢰 1회 승인
```
Windows:
```powershell
git clone <repo-url> $HOME\ai-agent-config; cd $HOME\ai-agent-config
Copy-Item templates\.env.example .env   # 값 채우기
powershell -ExecutionPolicy Bypass -File install.ps1
# 토큰은 install 후 ~/.config\github-mcp\env로 이동/공유
```

## 일상 워크플로 (양방향)
- **받기(pull)**: `git pull` → `./install.sh`(또는 `install.ps1`).
- **보내기(push, 자동)**: 전역 UserPromptSubmit 훅이 라이브 관리 설정 변경을 감지하면
  `capture.py`로 미러 → 관리 경로만 stage → 커밋 → `pull --rebase --autostash` 후 push까지 자동.
  push는 detached(프롬프트 안 막음). origin이 앞서 rebase 충돌이면 abort+로그만, 강제 안 함.
- **보내기(push, 수동)**: `python scripts/capture.py` → `git diff` 확인 → `git commit` → `git push`.
- 자동 sync 끄기: `AI_AGENT_CONFIG_NO_SYNC=1`. 로그: `~/.ai-agent-config-state/auto-capture.log`.
- **인증**: auto-push는 git credential helper(macOS keychain 등)에 의존. 새 PC는 최초 1회 수동 push로
  자격증명 캐시 후부터 auto-push 작동.
- capture는 토큰류(`ghp_`/`github_pat_`/`sk-`/`Bearer …`)를 `{{REDACTED}}`로 마스킹해 유출 방지. 비밀은 `${ENV}` 참조로만.
- 충돌은 대부분 `CLAUDE.md`/`AGENTS.md` 텍스트. git로 머지.

## 경로 템플릿
`{{PYTHON}}`(Codex 훅 인터프리터), `{{CODEX_HOME}}`, `{{CLAUDE_HOME}}` →
`apply.py`가 OS 기준으로 치환.

## 구성요소
| 파일 | 역할 |
|------|------|
| `scripts/apply.py` | repo→live 파일 적용·렌더·MCP/config 머지 (크로스플랫폼) |
| `scripts/capture.py` | live→repo 캡처·재템플릿화 |
| `scripts/auto_capture.py` | 전역 훅에서 변경 감지 후 `capture.py` 자동 실행 |
| `install.sh` / `install.ps1` | apply + 플러그인 재설치 + 외부 CLI/바이너리 빌드(graphify/gstack) + 검증 |
| `manifest/*.json` | 플러그인 재설치 목록 |
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
