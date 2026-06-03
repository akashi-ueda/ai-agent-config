# ai-agent-config

Windows ↔ macOS 공유용 AI 에이전트(Claude Code · Codex) 설정 SSOT.
git가 저장·머지·이력을, `apply.py`/`install.*`가 OS별 적용을 담당한다.

## 무엇이 동기화되나
- **Claude**: `CLAUDE.md`, `settings.json`(훅·권한), `tools/`(한국어 설명 스크립트), MCP 정의, `personal-local` 래퍼(gstack/mattpocock/graphify SKILL.md).
- **Codex**: `AGENTS.md`, `hooks.json`(caveman), `hooks/caveman.py`, config 포터블 키, MCP 정의.
- **플러그인**: store/curated plugin은 공식 marketplace에서 재설치, local skill pack은 personal plugin으로 복사 후 설치.

## 동기화 안 되는 것 (머신 전용/재생성)
plugins 캐시·sessions·projects·backups·`.credentials.json`, Codex `node_repl`/`hooks.state`/`marketplaces`/`projects`/`[windows]`, gstack 빌드 바이너리(`browse.exe` 등), graphify/gstack 외부 CLI 설치물, 모든 비밀 값.

## 비밀
`.env`(gitignore)에 토큰. `.env.example` 복사해 채운다. install이 OS 환경변수로 등록한다. github 토큰은 config가 env를 직접 참조(`${GITHUB_PERSONAL_ACCESS_TOKEN}`).

## 최초 셋업 (새 Mac)
```bash
git clone <repo-url> ~/ai-agent-config && cd ~/ai-agent-config
cp templates/.env.example .env   # 값 채우기
./install.sh                     # 적용 + 플러그인 재설치 + 검증
# Claude/Codex 재시작, Codex 전역 훅 신뢰 1회 승인
```
Windows:
```powershell
git clone <repo-url> $HOME\ai-agent-config; cd $HOME\ai-agent-config
Copy-Item templates\.env.example .env   # 값 채우기
powershell -ExecutionPolicy Bypass -File install.ps1
```

## 일상 워크플로 (양방향)
- **받기(pull)**: `git pull` → `./install.sh`(또는 `install.ps1`).
- **보내기(push)**: 라이브(`~/.claude`,`~/.codex`)에서 수정했으면
  `python scripts/capture.py` → `git diff` 확인 → `git commit` → `git push`.
- 충돌은 대부분 `CLAUDE.md`/`AGENTS.md` 텍스트. git로 머지.

## 경로 템플릿
`{{PYTHON}}`(Codex 훅 인터프리터), `{{CODEX_HOME}}`, `{{CLAUDE_HOME}}` →
`apply.py`가 OS 기준으로 치환.

## 구성요소
| 파일 | 역할 |
|------|------|
| `scripts/apply.py` | repo→live 파일 적용·렌더·MCP/config 머지 (크로스플랫폼) |
| `scripts/capture.py` | live→repo 캡처·재템플릿화 |
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
- `apply.py`의 Codex config 머지는 포터블 테이블만 교체하고 머신 섹션은 보존한다. 큰 변경 전 `~/.codex/config.toml` 백업 권장.
