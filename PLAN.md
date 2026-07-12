# PLAN: econ-systems-map (현황 보드)

> 5초 컷 살아있는 시트. 매 작업마다 갱신(상태·체크·마일스톤). 세부 체크리스트=task 리스트, 마일스톤 정의=docs/plan.md.

## 한 줄
2차·3차 파급효과를 탐색하는 3D 경제 인과관계 지도로 시스템 사고를 훈련하는 웹앱.

## 지금 단계
**v2.6.0 시각 존재감 개편 배포** (https://econ-systems-map.vercel.app). Marcus 지적 두 가지("3D인데 평면형이라 사이드 뷰에서 안 읽힘", "범주색이 다 같은 색으로 보임")를 해결: 노드마다 범주색 가산 헤일로(림 글로우, 각도 불변 실루엣) + 오버레이 링 4종 카메라 빌보드 + 계기 유휴 자전·장동(모션 축소 시 정지), accent 인레이 emissive 0.07→0.55(선택 0.9) + 바디 범주 틴트로 지도 스케일에서 범주색 즉독, 팔레트 4색 색각이상 재조정(protan 최악 ΔE 1.7→10.5, validate_palette.js 기록), 범례 '변수 분류' 최상단 이동, 칩 보더 범주 틴트, lang-toggle 드리프트 해소. "지금" 자동화 파이프라인은 시크릿 **3/6 등록 완료** 상태로 병행 대기한다.

## Milestones  (상태는 매 작업·도달 시 갱신)
- [x] M1 스캐폴드 + canonical 데이터 스키마/노드 정의
- [x] M2 콘텐츠 저작 (엣지 107 + 사례 4 + 루프 7 + 설명 30, KO/EN, 저작→리뷰 파이프라인)
- [x] M3 앱 구현 (Three.js 씬 + 탐색/시뮬레이터/사례/루프/온보딩/범례/i18n)
- [x] M4 검증 (실 Chrome: 전 모드 + EN + 모바일 390px + 모션 + 키보드, 콘솔 에러 0)
- [x] M5 멀티에이전트 리뷰(33 에이전트, 확정 24건) + 전건 수정 + 재검증
- [x] M6 A2 정밀 거시경제 계기 (서면 스펙 승인 → Blender·PBR 골격 → 대표 6개 → 30개 확장 → 성능·회귀 검증)

## 지금 체크리스트
- [x] 리뷰 확정 결함 수정 (로직 7, 씬 4, 품질 9, 콘텐츠 4)
- [x] 재검증 스모크 (레버 6종, 원인 보기 부호 앵커, stale 하이라이트, Escape, EN 타이틀)
- [x] (AI, 260711) GH 시크릿 3/6 등록: `VERCEL_TOKEN`·`VERCEL_ORG_ID`·`VERCEL_PROJECT_ID` (repo cusgong/econ-systems-map)
- [x] (Marcus·AI, 260711) A2 방향 확정: 30개 고유 오브제, 범주색 인레이, 인과 허브 크기, Blender + 단일 GLB
- [x] (AI, 260711) 서면 설계 스펙 작성: `docs/superpowers/specs/2026-07-11-precision-macro-instruments-design.md`
- [x] (Marcus, 260711) 서면 설계 스펙 승인
- [x] (AI, 260711) Store판 Blender 5.1.2 설치 확인 + WindowsApps CLI 제약 확인
- [x] (AI, 260711) 구현 계획 작성: `docs/superpowers/plans/2026-07-11-precision-macro-instruments-implementation.md`
- [x] (Marcus, 260711) 실행 방식 선택: subagent-driven
- [x] (AI, 260712) 허브 점수 TDD → Blender 수직 슬라이스 → 대표 6개 → 30개 고유 계기 완성
- [x] (AI, 260712) Blender 전체 게이트: 30 ready, fallback 0, 60 primitives, 63,428 triangles, GLB 1.75MB
- [x] (AI, 260712) 렌더 예산: 107개 passive edge를 3개 populated 배치로 축소, Three.js r170 행동 테스트 통과
- [x] (AI, 260712) 릴리스 회귀: Blender 계약 35개, Node.js 74개, Python 구문 20개 파일, Chrome 데스크톱·390px 모바일·KO/EN·모션 축소·구체 폴백·GLB 실패 복구 통과
- [x] (AI, 260712) 독립 최종 감사: Critical 0, Important 0, 두 번의 신규 GLB export가 배포 자산과 바이트 단위 일치
- [ ] (Marcus) ECOS 키 발급 → api-keys.local.env에 `ECOS_API_KEY=` 추가
- [ ] (Marcus) FRED 키 발급 → `FRED_API_KEY=` 추가
- [ ] (Marcus) `claude setup-token` 실행 → `CLAUDE_CODE_OAUTH_TOKEN=` 추가
- [ ] (AI, 키 도착 후) 나머지 시크릿 3개 등록 → workflow_dispatch 첫 실행 → 라이브 검증
- [ ] (대기) albaaam 등록 여부: Marcus 결정

## 블로커
- 없음. (해결됨 260711: 배포 BLOCKED 원인은 커밋 author의 GitHub noreply 이메일을 Vercel이 무효로 판단→차단. author를 globin0806@gmail.com으로 filter-branch 재작성+force push+재배포로 해제. 커밋 author는 앞으로 globin0806@gmail.com 고정.)
- (참고) GitHub 자동배포 연결은 GitHub App 미설치라 미연결. 현재는 CLI 토큰 배포(push 후 CLI 재배포 필요).

## 배포
- **라이브: https://econ-systems-map.vercel.app** (개인 Vercel `cusgong`, 로그인 globin0806@gmail.com)
- GitHub: https://github.com/cusgong/econ-systems-map (public, main). **author=Marcus Gong <globin0806@gmail.com>** (noreply 형식은 Vercel이 차단하므로 금지)
- 배포 방식: CLI 토큰 업로드. 토큰=`VERCEL_TOKEN_PERSONAL`(scripts/env/api-keys.local.env). 재배포:
  `npx vercel deploy --prod --yes --token=$VERCEL_TOKEN_PERSONAL` (프로젝트 폴더에서)
- 라이브에 앱만 노출되게 `.vercelignore` 유지(Vercel CLI는 .gitignore 무시). GitHub push: cusgong 전환 + `git -c credential.helper= -c credential.helper="!gh auth git-credential" push` 후 5bu-gainge 복구.

## 최근 완료
- v2.6.0 시각 존재감 개편 (Marcus: "평면형이라 사이드 뷰에서 안 띄고, 색깔이 다 같아 보임 + 그 밖에 개선"): ①범주 헤일로 — 노드당 범주색 가산 스프라이트(스케일 3.0×, opacity 기본 0.30/선택 0.52/딤 0.05, 브리딩 ±8%), depth-test 유지로 계기 본체가 중심을 가려 림 글로우로 읽힘(헌장 "발광 인과 그래프" 복원) ②오버레이 링 4종(선택·압력·도착·레버)을 매 프레임 카메라 빌보드 — 사이드 뷰에서 선으로 붕괴하던 문제 해결 ③계기 유휴 자전(yaw 0.07~0.13 rad/s, 노드별 해시 위상)+미세 장동(x±0.10/z±0.07) — 납작한 계기도 시간이 지나면 식별 가능, loadedRoot에만 적용(호버 틸트 감쇠와 충돌 없음), reduced-motion 정지 ④accent emissive 0.07→0.55(선택 0.9)·바디 범주 틴트 lerp 0.14·바디 emissive 범주색화 ⑤팔레트 재조정: 정책 #2ff0c4·실물 #62d97e·외생 #e26bff·대외환율 #4d73ff(protan 최악 ΔE 1.7→10.5, cat-chip 텍스트 전색 ≥4.5:1, validate_palette.js 실행 기록 DESIGN §7) ⑥범례 '변수 분류' 헤딩 신설+최상단 이동, 온보딩 SVG 구색 갱신, 칩 보더 범주 틴트(color-mix 42%+구형 브라우저 폴백), lang-toggle 활성색 시안 계열 오버라이드. 검증: 테스트 77/77, CDP 실렌더 6뷰+EN+모바일390+콘솔 에러 0(프리뷰 팬은 백그라운드 스로틀로 스크린샷 불가 → verification-environment-safety 따라 headless Chrome CDP 하네스 신설, scratchpad). 멀티에이전트 감사 4렌즈(사전)+적대 리뷰 4렌즈·검증 2건(사후): 확정 결함 0. 헤일로 +30 드로콜은 문서화(README).
- v2.5.0 렌더 폴리시 + 라이브 배포 (Marcus: "modeled/rendered 변수들 잘 작동되게, 계획한 거 다 하고 배포까지"): A2 빌드가 남긴 uncommitted 폴리시 패스(화면 크기 클램프 displayRadius, 밝은 PBR+hemisphere 조명+exposure 1.08, trimEdgeEndpoints 엣지 트림, labelOpacityForState 라벨 정책)를 실브라우저로 검증·확정하고, 층 이름표가 노드 라벨과 겹치면 0.22 고스트로 양보하는 declutterLayerTags(15프레임 스로틀, 콘텐츠 우선)를 추가. 실측: GLB 30모델 로드, 노드 라벨 겹침 0(레이아웃 솔버 정상), 선택 프레이밍+트림 엣지, 시뮬레이터 압력 링 24노드, KO/EN(층 태그 번역·충돌분만 고스트), 모바일, 콘솔 앱 에러 0, 테스트 77/77. 로컬 main 25커밋(A2 전체 라인)을 origin에 push 후 Vercel CLI prod 배포, 라이브 v2.5.0+GLB(200)+신규 모듈 서빙 확인.
- v2.5.0 A2 정밀 거시경제 계기: 30개 변수별 고유 Blender 하드서피스 모델, dark titanium PBR + 범주색 10~20% 인레이, 1~3홉 허브성 반지름 0.82~1.28, 선택·전파 상태 링과 서명 동작, reduced-motion 정지, ID별 구체 폴백. Blender 저작 체인은 6→12→18→24→30을 매 배치 전후 검증하고, 직렬화된 임시 `.blend`가 unrelated root·PBR node graph·bevel·custom-normal 동결 SHA-256 계약을 모두 통과한 뒤에만 원본을 원자 교체한다. 최종 자산은 30 IDs, 60 primitives, 63,428 triangles, accent 10.96~18.74%, GLB 1,752,492 bytes다. 107개 passive edge는 3개 populated LineSegments 배치로 줄였고, contested edge의 점선 거리는 엣지 내부 40개 세그먼트에 누적한다. Blender 계약 35개와 Node.js 74개, Chrome 데스크톱·모바일·폴백 경로를 통과했고 독립 감사 결과 Critical 0, Important 0이다.
- v2.4.0 UX 전면 개보수 (Marcus: "못다한 UI/UX 개선도 마저 해"): 7차원 멀티에이전트 감사(에이전트 8, 발견 57건) + 실브라우저 감사 → 확정 40여 건 구현. ①AI 채팅 견고화: 자동 스크롤 실제 스크롤러로 수정(stick-to-bottom), 한글 IME Enter 가드, 스트리밍 중 초안 보존, 오류 턴 히스토리 제외+다시 시도 버튼, 스트림 중 제공자 에러 표면화, 네트워크 오류 한국어 카피, 타 탭 하이재킹 방지, 대화 지우기·키 삭제 2탭 확인+진행 중 요청 중단, 입력창 자동 확장, 제공자 라벨 이중언어 ②온보딩 개편: 3단계를 라벨 4행(개념당 한 줄)으로, 금색 국면반전 설명+스와치 추가, 건너뛰기, 점 클릭 이동, 단축키는 파인 포인터만, 딥링크 방문자는 모달 대신 토스트, 리스트 모드는 3D 투어 생략 ③탐색 IA: 홈 섹션 퀵내비 칩, 변수 뷰 ←탐색 버튼+레버 드래그 힌트, 추천 시작점 카테고리 점, 서브뷰 제목 EXPLORE·SIM/CASE/LOOP, 범례 3그룹+스크롤 캡, 검색 빈 상태 큐레이션+백드롭 닫기, 크로스 점프 정크 히스토리 제거, 죽은 딥링크 안내, 테마 검색 결과 이름 공백 버그 수정 ④모바일: 범례를 실측 헤더 높이(--hud-real-h, ResizeObserver)로 배치(래핑 헤더에 묻힘 해소), 언어 토글·btn.sm·슬라이더 터치 타깃 확대, AI 입력 16px(iOS 줌 방지), :active 피드백+hover 게이트, 레버 드래그 pointercancel 복원 ⑤a11y: 탭 aria-current, 사례 스테퍼·AI 툴바 포커스 보존, 패널 포커스 앵커, 루프·테마·AI 답변 announce, fx-row 중첩 인터랙티브 해소(전용 토글), 로딩 오버레이 a11y 트리 제거, 층 이름표 AA, 모션 토글이 OS 설정 위에 작동, 도움말 버튼 라벨 ⑥아이덴티티: og-image(1200x630)+og:url+트위터 카드, apple-touch-icon, 브랜드 404.html, 버전 단일 소스, 부트 워치독 오탐 자가 복구, 이모지 글리프를 텍스트 표현형으로 ⑦i18n: 사전 기계 교차검증(죽은 키 12 제거·24 추가), EN asOf 칩 어순, 테마 프리뷰 단어 경계 말줄임. 검증: 실브라우저 전 항목(온보딩 4단계·홈·변수·사례 히스토리·검색·AI 오류경로·EN·모바일 하네스·404·라이브 v2.4.0), 콘솔 에러 0. 보류: NOW 지표 출처명 이중언어(파이프라인 변경 필요), 3D 라벨 겹침 정리, 모바일 헤더 행 병합.
- v2.3.0 "지금" 무인 자동 업데이트 파이프라인 (Marcus 선택: "전부 무인 자동"): situation.js를 **생성 파일**로 전환(정본 = scripts/now/readings-live.json 기계층 + editorial.json 편집층, build_situation.py가 검증 후 병합·생성). ①매일 19:05 KST GH Actions 크론이 ECOS 13종+FRED 2종 공식 시리즈를 fetch(시리즈 정의 = series-map.json, 전부 2026-07-11 샘플키/공개CSV 라이브 검증, 변환 검산 일치) → 수치·기준일·트렌드 갱신 → 커밋 → Vercel CLI 배포. sanity bounds 위반·4개 이상 실패 시 발행 차단. ②주간(월 07:00 KST) claude-code-action@v1 에이전트가 EDITORIAL-PROTOCOL.md(웹 검증 2출처+, 예측·투자조언 금지, editorial.json만 수정) 수행 → 독립 재빌드 검증 스텝 통과 시에만 커밋·배포. ③앱: asOf를 수치/해설로 분리(칩 병기, 해설 4개월 경고 + 수치 피드 1개월 정지 경고 신설), 고지 카피 갱신. 표시 의미 변경: 부동산→KB 서울 아파트 월간(부동산원 ECOS 5개월 지연), 가계부채→예금취급기관, GDP→분기 실적(전망은 note), 연준·유가→FRED 일별. **CI 커밋 author=globin0806(Vercel이 CLI 배포에도 author 검증)**. 함정 파악: ECOS 적재 지연 워치리스트(수출 익월 중순, 임금 수개월), 60일 크론 비활성은 일일 커밋이 자체 keepalive. 리서치 = Workflow 6 에이전트(ECOS 라이브 프로브 15/15 확정, claude-in-CI 사실 검증: setup-token 1년 토큰·OAuth WebSearch 버그는 오진으로 종결)
- v2.2.0 멀티 제공자 AI 키 (Marcus: "Anthropic 말고 다른 주요 AI API key도 받게"): AI 채팅이 Anthropic(Claude)·Google(Gemini)·OpenAI 호환(OpenRouter·xAI/Grok·Groq·DeepSeek·Mistral·직접입력 Base URL) 키를 받음. `AI_PROVIDERS` 레지스트리 + 제공자별 build()/extract() 어댑터 + 통합 SSE 파서. 편집 가능한 모델 필드(datalist, 모델명 드리프트 대응). 제공자별 키 저장(`macroscope.key.<id>`, 구 `macroscope.apikey`에서 자동 마이그레이션). 셋업 UI = 제공자 선택 + (openai_compat일 때) 프리셋·Base URL + 제공자별 키 힌트/발급 링크. **OpenAI 본체 API는 브라우저 CORS 차단**이라 GPT는 OpenRouter 경유 안내. 검증: Gemini 어댑터를 라이브 API로 확인(gemini-2.5-flash HTTP 200, SSE 형식=extract 일치), 4개 셋업 상태 전부 렌더·콘솔 에러 0, Anthropic 경로 v2.0.0과 동일. 라이브 v2.2.0 확인.
- v2.1.0 탐색 중심 IA 개편 (Marcus 지적: 사례·루프를 탐색하며 보게 했으면 상단 탭이 없어야 맞다 → 이전 크로스링크는 탭 갈아타기라 반쪽): 원칙 = **상단 탭은 도구/렌즈, 콘텐츠 아님**. 탭 3개(탐색·지금·AI)로 축소, 역사 사례·루프·시뮬레이터 탭 제거. 탐색이 허브: 홈에서 사례·루프 전체 브라우징 + 시뮬레이터 열기, 변수 선택 시 관련 사례·루프 인라인. 이 셋은 탐색 안의 뷰(탐색 탭 유지 + "← 탐색" 백, 지도 안 벗어남). 변수에서 연 사례는 백이 그 변수로 복귀, 홈에서 연 건 홈으로. 홈버튼·Esc·온보딩·i18n 반영. 실브라우저 전 흐름 검증.
- v2.0.0 라이브 배포 해제(260711): Vercel BLOCKED 실사유 = 커밋 author의 noreply 이메일 무효 판정(개인 Hobby도 git-author 검사 적용, Pro전용 아님). author를 globin0806@gmail.com으로 재작성해 통과. 라이브 v2.0.0 확인.
- v2.0.0 (Marcus 피드백 5건): ①탐색↔사례·루프 크로스링크(변수 선택 시 등장 사례·루프 버튼 + NOW 계기 스트립) ②핵심 변수 계기판(3D 라벨 실측값 6종) ③전파 시각화 혁신(시차 비례 펄스 파동, 도착 밀당 바운스, 레버 노드 상하 드래그 즉석 충격→시뮬레이터 자동 전환) ④국면 반전 8건(금색 엣지+⇄배지, 예: 성장발 금리 상승은 주가 호재) ⑤AI 채팅 탭(BYO Anthropic 키·스트리밍·프롬프트 캐시, 답변의 map 블록이 지도 하이라이트/시나리오 착색/사례·루프 점프 자동 실행) ⑥콘텐츠 추가: 닷컴 버블 사례(AI 슈퍼사이클 테마와 상호 연결)+자산효과 루프 — 저작→회의적 팩트체크 파이프라인(정정 10+건)
- v1.3.1 다이얼로그 스크롤바 중복 수정 (Marcus 제보 "출처와 한계 창 스크롤바 2개"): `dialog`와 `.dlg-body`가 같은 `max-height: min(80dvh,720px)`를 가져 테두리(2px)만큼 내부가 넘쳐 둘 다 스크롤러가 됐다. 스크롤러를 하나(`.dlg-body`)로만: `dialog`에 `overflow:hidden`, 내부 상한을 `calc(var(--dlg-maxh) - 2*var(--dlg-border))`로 다이얼로그 안쪽에 정확히 맞춤. `min(80dvh,720px)`를 `--dlg-maxh` 변수로 뽑아 값 드리프트 방지. flex/퍼센트-높이 방식은 자동높이 부모에서 붕괴해 폐기. 온보딩 다이얼로그도 함께 수정, 검색 팔레트 무영향. 검증: 프리뷰 탭 0×0 뷰포트 아티팩트(dvh=0) 우회 위해 `--dlg-maxh`만 500px로 치환해 스크롤 메커니즘 실측 → dialog 스크롤 안 함(overflow hidden), body만 15px 스크롤바(단일 스크롤러) 확인.
- v1.3.0 "지금" 모드 (Marcus 피드백 "실제 지금 정세 기반"): 검증 지표 17개(리서치 3 에이전트 + 독립 교차검증 1, 전부 출처·기준일 명기) + 지도 투영(최근 6개월 방향 틴트) + 현재 흐름 테마 5개(호르무즈 유가, AI 반도체, 미 관세, 집값·가계부채, 중국)와 인과 경로 하이라이트·닮은꼴 사례·관련 루프 연결. 스냅샷 4개월 경과 시 자동 경고. 갱신 경로 = data/situation.js 단일 파일
- v1.2.0 편의 패키지 (Marcus 피드백 "검색 + UX"): Ctrl+K·/ 검색 팔레트(변수·사례·루프 통합, 초성 검색, 키보드 완결), URL 해시 딥링크+뒤로가기(#/v·#/case·#/loop·#/sim), 경로 체인 변수명 클릭 점프, 라벨 호버 툴팁(변수 설명), 처음 화면(⌖) 버튼, 도움말 단축키 안내
- v1.1.0 공간 의미 체계 (Marcus 피드백 "z축 활용 + 위치의 의미"): 높이 = 심리·기대/정책·외생/돈·자산/실물/원자재 5층, 반경 = 국내↔글로벌(GDP 중심, 연준·지정학·유가 외곽), 각도 = 도메인 섹터 + 수직 정렬(기대인플레는 물가 위, 투자심리는 주가 위). 층 가이드 링 + 이름표, 범례·온보딩 갱신. 292°는 이름표 전용 빈 섹터
- v1.0.0 리뷰 반영: 원인 보기 방향 부호 앵커, 시뮬레이터 stale 하이라이트 제거, 재정지출·지정학 레버 추가(6종), 부트 워치독, 포커스 보존, 모바일 출처 버튼, 문체 합니다체 통일, 1980 한국 성장률 귀속 정정

## 실행
- 로컬: preview `econ-map` (127.0.0.1:5230) 또는 `python -m http.server 5230` (프로젝트 루트)
- 데이터 수정: 스크래치 JSON → `python scripts/build-data.py <dir>` (data/*.js 직접 편집 금지)

업데이트: 260713 (v2.6.0 시각 존재감 개편)
