# Plan

## Goal

단편 경제 상식이 아니라 변수 간 연결과 2차·3차 파급효과를 탐색하게 하는 인터랙티브 3D 인과관계 지도 웹앱. 시스템 사고(연쇄 경로, 상충 경로, 강화/균형 피드백 루프) 훈련이 목적.

## Success Criteria

- 변수 선택 시 1·2·3차 파급 경로가 3D 지도 위에 단계적으로 강조되고, 각 경로가 쉬운 한국어(및 영어)로 설명된다.
- 시나리오 시뮬레이터(기준금리·유가·환율·미국금리)가 조작 즉시 파급 결과를 갱신하고, 상충 경로를 명시한다.
- 역사 사례 4건(1970s 인플레이션, 1997 외환위기, 2008 금융위기, 2020-22 팬데믹 유동성)이 원인→확산→정책 대응→시장 심리→결과 단계로 지도 위에 재생된다.
- 초보자 온보딩·범례·모션 감소·반응형·출처 패널 포함, web-service-quality P0 전부 통과.

## Current Status

M1 스캐폴드 완료, 데이터 설계 진행 중.

## Stakeholders

- Marcus (소유자, 학습 도구 사용자)

## Constraints

- 정적 사이트, 빌드 없음, CDN 없음(three.js 로컬 vendored).
- 콘텐츠는 정형화된 교과서 메커니즘 + 출처 태그. 예측/투자조언 금지.
- KO 기본 + EN 토글 (i18n-kit 재사용).

## Risks

- 3D 가독성 vs 밀도: 노드 30개 상한, 라벨 거리 페이드, 선택 시 딤아웃으로 관리.
- 경제 메커니즘 단순화의 오해 소지: confidence 표기 + "모형 한계" 고지로 관리.

## Milestones

- M1 스캐폴드 + canonical 스키마
- M2 콘텐츠 저작 (Workflow 병렬, KO/EN)
- M3 앱 구현
- M4 검증
- M5 리뷰 + 수정 + 보고

## Next Actions

- 노드 30개 canonical 정의
- 콘텐츠 Workflow 실행
- three.js vendoring

## Open Questions

- 추후 배포(Vercel) 여부, albaaam 등록 여부는 Marcus 결정 대기.
