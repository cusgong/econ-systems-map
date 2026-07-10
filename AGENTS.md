# AGENTS.md: econ-systems-map

## Source of Truth

- 현황 보드(제일 먼저): `PLAN.md`
- 전략·계획: `docs/plan.md`
- 연속성·결정: `docs/session-log.md`
- 보관: `archives/`

## Project Delta

- 정적 사이트다. 빌드 스텝 없음. `index.html` + ES modules + `vendor/` 로컬 three.js. CDN 의존 금지(오프라인 동작 보장).
- 인과 그래프 데이터(`data/*.js`)가 단일 진실원이다. 노드 ID는 ASCII snake_case, 모든 텍스트 필드는 `{ko, en}` 이중언어. 엣지·사례·루프가 참조하는 ID는 `scripts/validate-data.py`로 정합성 검증 후 커밋한다.
- 콘텐츠 원칙: 교과서 수준의 정형화된 메커니즘만 수록(출처 태그 필수), 확실성(confidence)을 정직하게 표기, 예측·투자조언 문구 금지.
- 한국어 CSS 기본선: `word-break: keep-all` + `overflow-wrap: break-word` (rules/cjk-rendering-safety §5).
