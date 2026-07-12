# econ-systems-map_personal_260710

인터랙티브 3D 경제 인과관계 지도 웹앱. 금리·물가·환율 등 30개 거시 변수를 노드로, 인과관계를 방향성 있는 엣지로 표현하고, 2차·3차 파급효과 탐색, 시나리오 시뮬레이터, 역사 사례 재생, 피드백 루프 뷰로 "시스템 사고"를 훈련하는 도구. Three.js 기반 홀로그램 관제실 스타일, KO/EN.

v2.5.0부터 30개 변수는 각각 다른 Blender 5.1.2 정밀 계기로 표현된다. 형상은 변수의 경제적 성격, 범주색 인레이는 역할, 반지름 0.82~1.28은 1~3홉 인과 허브성을 전달한다. GLB가 실패하거나 일부 모델이 유효하지 않으면 해당 변수만 즉시 구체 폴백으로 복구된다.

정식 자산은 30 IDs, 60 primitives, 63,428 triangles, 1,752,492 bytes이며 Blender 계약 35개와 Node.js 회귀 74개를 통과한다. 107개 passive edge는 현재 데이터에서 3개 배치로 렌더되고, contested edge의 점선 위상은 엣지별로 독립 누적된다.

## Folder Structure

| 폴더/파일 | 용도 |
|---|---|
| `PLAN.md` | 현황 보드 (한 눈에: 지금/다음/블로커). 제일 먼저 본다 |
| `docs/` | plan.md (깊은 계획), session-log.md (연속성·결정) |
| `archives/` | 보관 (삭제 X) |
| `.claude/skills/project-manager/` | PM 작업 sub-skill |
| `index.html` | 앱 진입점 (정적 사이트, 빌드 불필요) |
| `css/`, `js/`, `data/` | 앱 스타일 / 모듈 / 인과 그래프 데이터(변수·엣지·사례·루프) + 상황판 스냅샷(situation.js, 수동 갱신·기준일 필수) |
| `data/models/` | 브라우저용 검증 완료 단일 GLB 모델 라이브러리 |
| `scripts/blender/` | 30개 모델의 `.blend` 정본, 재현 가능한 저작·검증·원자적 내보내기 파이프라인 |
| `vendor/` | 로컬 vendored 라이브러리 (three.js + addons) |
| `scripts/` | 데이터 정합성 검증 등 유틸 스크립트 |

## Quick Start

- 로컬 실행: `python -m http.server 5230` (프로젝트 루트에서) 후 `http://localhost:5230`
- 웹 회귀 테스트: `npm test`
- Blender 전체 검증·재생성: `scripts/blender/README.md`의 Blender 5.1.2 명령 사용
- 한 눈에 현황: PLAN.md (제일 먼저, 매 작업 갱신)
- 작업 재개: docs/session-log.md 읽고 마지막 next actions 확인
- 계획 변경: docs/plan.md 갱신
- 표준 폴더 룰: `rules/project-folder-structure_260509.md` 참조
