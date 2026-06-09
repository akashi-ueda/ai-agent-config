<!--
PR 작성 가이드 (사람·에이전트 공통):
- base 브랜치는 변경 종류에 따른다: 코드/CI/manifest/플러그인 → develop, 릴리스 → main.
- 머지는 저장소 소유자가 결정한다. 에이전트는 CI 통과까지만.
아래 섹션을 채우고, 해당 없는 항목은 지운다.
-->

## What
<!-- 무엇을 바꿨나 (1-3줄) -->

## Why
<!-- 왜 필요한가 / 어떤 문제를 푸나. 관련 이슈가 있으면 `Refs #N` 또는 `Closes #N` -->

## Tests
<!-- 어떻게 검증했나: `python -m unittest discover -s tests`, `ruff check --select F scripts tests`,
     `python scripts/install_plugins.py --dry-run` 등 실제 명령과 결과 -->

## Notes for reviewer
<!-- 리뷰어가 알아야 할 점: 동작 변화 여부, 스택/의존 PR, 후속 작업 등 -->
