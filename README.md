# econ-systems-map_personal_260710

인터랙티브 3D 경제 인과관계 지도 웹앱. 금리·물가·환율 등 30개 거시 변수를 노드로, 인과관계를 방향성 있는 엣지로 표현하고, 2차·3차 파급효과 탐색, 시나리오 시뮬레이터, 역사 사례 재생, 피드백 루프 뷰로 "시스템 사고"를 훈련하는 도구. Three.js 기반 홀로그램 관제실 스타일, KO/EN.

## Folder Structure

| 폴더/파일 | 용도 |
|---|---|
| `PLAN.md` | 현황 보드 (한 눈에: 지금/다음/블로커). 제일 먼저 본다 |
| `docs/` | plan.md (깊은 계획), session-log.md (연속성·결정) |
| `archives/` | 보관 (삭제 X) |
| `.claude/skills/project-manager/` | PM 작업 sub-skill |
| `index.html` | 앱 진입점 (정적 사이트, 빌드 불필요) |
| `css/`, `js/`, `data/` | 앱 스타일 / 모듈 / 인과 그래프 데이터(변수·엣지·사례·루프) + 상황판 스냅샷(situation.js, 수동 갱신·기준일 필수) |
| `vendor/` | 로컬 vendored 라이브러리 (three.js + addons) |
| `scripts/` | 데이터 정합성 검증 등 유틸 스크립트 |

## Quick Start

- 로컬 실행: `python -m http.server 5230` (프로젝트 루트에서) 후 `http://localhost:5230`
- 한 눈에 현황: PLAN.md (제일 먼저, 매 작업 갱신)
- 작업 재개: docs/session-log.md 읽고 마지막 next actions 확인
- 계획 변경: docs/plan.md 갱신
- 표준 폴더 룰: `rules/project-folder-structure_260509.md` 참조
