# ai-agent-config

Windows ↔ macOS 공유용 AI 에이전트(Claude Code · Codex) 설정 SSOT.
git가 저장·머지·이력을, `apply.py`/`install.*`가 OS별 적용을 담당한다.

## 무엇이 동기화되나
- **Claude**: `CLAUDE.md`, `settings.json`(훅·권한), `tools/`(한국어 설명 스크립트), MCP 정의, `personal-local` 래퍼(gstack/mattpocock SKILL.md).
- **Codex**: `AGENTS.md`, `hooks.json`(caveman), `hooks/caveman.py`, config 포터블 키, MCP 정의.
- **플러그인**: 파일이 아니라 `manifest/*.json`의 마켓플레이스+id로 **재설치**.

## 동기화 안 되는 것 (머신 전용/재생성)
plugins 캐시·sessions·projects·backups·`.credentials.json`, Codex `node_repl`/`hooks.state`/`marketplaces`/`projects`/`[windows]`, gstack 빌드 바이너리(`browse.exe` 등), 모든 비밀 값.

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
| `install.sh` / `install.ps1` | apply + 플러그인 재설치 + 외부설치(graphify/gstack) + 검증 |
| `manifest/*.json` | 플러그인 재설치 목록 |
| `codex/config.portable.toml` | 머지되는 Codex 포터블 키만 |
| `claude/mcp.portable.json` | 머지되는 MCP 정의 |

## 주의
- gstack/graphify는 OS별 빌드·CLI 설치라 install이 재실행(시간 소요). bun·uv 필요.
- `apply.py`의 Codex config 머지는 포터블 테이블만 교체하고 머신 섹션은 보존한다. 큰 변경 전 `~/.codex/config.toml` 백업 권장.
