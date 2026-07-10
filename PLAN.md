# PLAN: econ-systems-map (현황 보드)

> 5초 컷 살아있는 시트. 매 작업마다 갱신(상태·체크·마일스톤). 세부 체크리스트=task 리스트, 마일스톤 정의=docs/plan.md.

## 한 줄
2차·3차 파급효과를 탐색하는 3D 경제 인과관계 지도로 시스템 사고를 훈련하는 웹앱.

## 지금 단계
v2.0.0 완성·GitHub push 완료. 라이브는 v1.3.0에 멈춤: Vercel이 신규 계정 배포를 일괄 BLOCKED(20:24 이후 전부) — 대시보드 인증 해제 대기.

## Milestones  (상태는 매 작업·도달 시 갱신)
- [x] M1 스캐폴드 + canonical 데이터 스키마/노드 정의
- [x] M2 콘텐츠 저작 (엣지 107 + 사례 4 + 루프 7 + 설명 30, KO/EN, 저작→리뷰 파이프라인)
- [x] M3 앱 구현 (Three.js 씬 + 탐색/시뮬레이터/사례/루프/온보딩/범례/i18n)
- [x] M4 검증 (실 Chrome: 전 모드 + EN + 모바일 390px + 모션 + 키보드, 콘솔 에러 0)
- [x] M5 멀티에이전트 리뷰(33 에이전트, 확정 24건) + 전건 수정 + 재검증

## 지금 체크리스트
- [x] 리뷰 확정 결함 수정 (로직 7, 씬 4, 품질 9, 콘텐츠 4)
- [x] 재검증 스모크 (레버 6종, 원인 보기 부호 앵커, stale 하이라이트, Escape, EN 타이틀)
- [ ] (대기) Vercel 배포 / albaaam 등록 여부: Marcus 결정

## 블로커
- **Vercel 배포 BLOCKED**: 첫 배포(v1.3.0, 20:14)만 성공, 20:24 이후 모든 배포가 readyState=BLOCKED (계정 softBlock은 아님 = 신규 Hobby 계정 자동 검증). 해제: Marcus가 globin0806 로그인으로 vercel.com/cusgongs-projects 접속 → 차단 배너의 인증(전화 인증 등) 1회 → 이후 `npx vercel deploy --prod --yes --token=$VERCEL_TOKEN_PERSONAL` 재실행하면 v2.0.0 라이브.
- (참고) GitHub 자동배포 연결은 GitHub App 미설치라 미연결. 현재는 CLI 토큰 배포.

## 배포
- **라이브: https://econ-systems-map.vercel.app** (개인 Vercel `cusgong`, 로그인 globin0806@gmail.com)
- GitHub: https://github.com/cusgong/econ-systems-map (public, main). author=Marcus Gong(cusgong noreply)
- 배포 방식: CLI 토큰 업로드. 토큰=`VERCEL_TOKEN_PERSONAL`(scripts/env/api-keys.local.env). 재배포:
  `npx vercel deploy --prod --yes --token=$VERCEL_TOKEN_PERSONAL` (프로젝트 폴더에서)
- 라이브에 앱만 노출되게 `.vercelignore` 유지(Vercel CLI는 .gitignore 무시). GitHub push: cusgong 전환 + `git -c credential.helper= -c credential.helper="!gh auth git-credential" push` 후 5bu-gainge 복구.

## 최근 완료
- v2.0.0 (Marcus 피드백 5건): ①탐색↔사례·루프 크로스링크(변수 선택 시 등장 사례·루프 버튼 + NOW 계기 스트립) ②핵심 변수 계기판(3D 라벨 실측값 6종) ③전파 시각화 혁신(시차 비례 펄스 파동, 도착 밀당 바운스, 레버 노드 상하 드래그 즉석 충격→시뮬레이터 자동 전환) ④국면 반전 8건(금색 엣지+⇄배지, 예: 성장발 금리 상승은 주가 호재) ⑤AI 채팅 탭(BYO Anthropic 키·스트리밍·프롬프트 캐시, 답변의 map 블록이 지도 하이라이트/시나리오 착색/사례·루프 점프 자동 실행) ⑥콘텐츠 추가: 닷컴 버블 사례(AI 슈퍼사이클 테마와 상호 연결)+자산효과 루프 — 저작→회의적 팩트체크 파이프라인(정정 10+건)
- v1.3.1 다이얼로그 스크롤바 중복 수정 (Marcus 제보 "출처와 한계 창 스크롤바 2개"): `dialog`와 `.dlg-body`가 같은 `max-height: min(80dvh,720px)`를 가져 테두리(2px)만큼 내부가 넘쳐 둘 다 스크롤러가 됐다. 스크롤러를 하나(`.dlg-body`)로만: `dialog`에 `overflow:hidden`, 내부 상한을 `calc(var(--dlg-maxh) - 2*var(--dlg-border))`로 다이얼로그 안쪽에 정확히 맞춤. `min(80dvh,720px)`를 `--dlg-maxh` 변수로 뽑아 값 드리프트 방지. flex/퍼센트-높이 방식은 자동높이 부모에서 붕괴해 폐기. 온보딩 다이얼로그도 함께 수정, 검색 팔레트 무영향. 검증: 프리뷰 탭 0×0 뷰포트 아티팩트(dvh=0) 우회 위해 `--dlg-maxh`만 500px로 치환해 스크롤 메커니즘 실측 → dialog 스크롤 안 함(overflow hidden), body만 15px 스크롤바(단일 스크롤러) 확인.
- v1.3.0 "지금" 모드 (Marcus 피드백 "실제 지금 정세 기반"): 검증 지표 17개(리서치 3 에이전트 + 독립 교차검증 1, 전부 출처·기준일 명기) + 지도 투영(최근 6개월 방향 틴트) + 현재 흐름 테마 5개(호르무즈 유가, AI 반도체, 미 관세, 집값·가계부채, 중국)와 인과 경로 하이라이트·닮은꼴 사례·관련 루프 연결. 스냅샷 4개월 경과 시 자동 경고. 갱신 경로 = data/situation.js 단일 파일
- v1.2.0 편의 패키지 (Marcus 피드백 "검색 + UX"): Ctrl+K·/ 검색 팔레트(변수·사례·루프 통합, 초성 검색, 키보드 완결), URL 해시 딥링크+뒤로가기(#/v·#/case·#/loop·#/sim), 경로 체인 변수명 클릭 점프, 라벨 호버 툴팁(변수 설명), 처음 화면(⌖) 버튼, 도움말 단축키 안내
- v1.1.0 공간 의미 체계 (Marcus 피드백 "z축 활용 + 위치의 의미"): 높이 = 심리·기대/정책·외생/돈·자산/실물/원자재 5층, 반경 = 국내↔글로벌(GDP 중심, 연준·지정학·유가 외곽), 각도 = 도메인 섹터 + 수직 정렬(기대인플레는 물가 위, 투자심리는 주가 위). 층 가이드 링 + 이름표, 범례·온보딩 갱신. 292°는 이름표 전용 빈 섹터
- v1.0.0 리뷰 반영: 원인 보기 방향 부호 앵커, 시뮬레이터 stale 하이라이트 제거, 재정지출·지정학 레버 추가(6종), 부트 워치독, 포커스 보존, 모바일 출처 버튼, 문체 합니다체 통일, 1980 한국 성장률 귀속 정정

## 실행
- 로컬: preview `econ-map` (127.0.0.1:5230) 또는 `python -m http.server 5230` (프로젝트 루트)
- 데이터 수정: 스크래치 JSON → `python scripts/build-data.py <dir>` (data/*.js 직접 편집 금지)

업데이트: 260710
