# DESIGN.md — 매크로스코프 MacroScope 디자인 DNA

> **이 파일이 이 서비스 시각 정체성의 단일 진실원이다.** 이 서비스의 화면을 스타일링하는 모든 세션은 작업 전 이 파일을 먼저 읽는다.
>
> **잠금 원칙 — 서비스 간 발산, 서비스 내 고정.** 새 서비스는 대담하게 다른 방향을 탐색하지만, 이 파일이 확정된 순간 이 서비스의 방향은 잠긴다. 이 파일과 다른 방향의 재스타일링은 Marcus의 명시적 승인 없이 금지. 확장은 언제나 이 DNA 안에서.
>
> 포맷 정본: `scripts/web-templates/design-dna-kit/` · 게이트: `rules/web-service-quality_260602.md` §1 (P0)

- **서비스**: 매크로스코프 MacroScope (econ-systems-map.vercel.app · PLAN.md 기준 라이브 v2.4.0, 로컬 launch `econ-map`:5230)
- **소속 패밀리**: 독립
- **확정일**: 260712 · **최종 갱신**: 260712
- **스택**: Vanilla JS 정적 사이트(빌드 없음) + three.js(vendored, `vendor/`) · **토큰 파일**: `css/main.css` `:root`

> 데이터 주의: `data/edges.js`·`cases.js`·`loops.js`·`descs.js`는 `scripts/build-data.py` 생성물, `data/situation.js`는 "지금" 파이프라인 생성물 — 디자인 표면이 아니다. 단, `data/nodes.js`의 `CATEGORIES` 9색과 `LAYERS`는 수저작 정본이며 이 DNA의 일부다(§7).

---

## 0. 헌장 (Charter)

한 줄 은유가 모든 시각 결정의 시금석이다. 결정이 흔들릴 때 여기로 돌아온다.

- **컨셉 은유**: "심우주 관제 데크 — 어두운 홀로그램 위 읽기 우선" (`css/main.css` 헤더 주석 원문: "Deep-space operations deck. Dark, holographic, readable-first.")
- **슬로건/보이스**: "경제 인과관계 지도 · 시스템 사고 훈련장" (헤더 브랜드 서브라인) / "변수 사이의 연결로 경제를 읽는 시스템 사고 훈련장" (og:description). 보이스: 합니다체 통일(PLAN v1.0.0), 교과서 수준 정형화 메커니즘만 수록, 예측·투자조언 문구 금지(AGENTS.md 콘텐츠 원칙).
- **무엇이 이 서비스를 잊을 수 없게 하는가**: 검은 우주에 떠 있는 발광 인과 그래프. 인과의 부호가 색으로 즉독되고(청록 +, 주황 −, 금색 국면반전), 파급효과가 시차에 비례하는 펄스로 눈에 보인다.
- **형제 서비스와의 거리**: 독립 서비스. 이 워크스페이스의 VH 계열(웜 페이퍼·라이트 문서 톤)과 정반대 극점 — 문서가 아니라 계기(instrument)이고, 종이가 아니라 심우주다.

## 1. 시그니처 (Signature) — 최대 3개

서비스를 알아보게 하는 요소. 값만이 아니라 **왜(why)** 를 기록한다 — 이유 없는 시그니처는 다음 세션이 복원할 수 없다.

| 시그니처 | 정의(정확한 값/CSS) | 왜 | 사용처/금지처 |
|---|---|---|---|
| 심우주 배경 스택 | `body`: `radial-gradient(1200px 700px at 70% 20%, #0a1a33 0%, transparent 55%)` + `radial-gradient(900px 600px at 20% 85%, #081226 0%, transparent 60%)` + `--bg0 #030610`; 씬: 별 파티클 650개(`0x9fc9ff`), 플로어 링 5개(`0x3a6ea8`), `THREE.Fog('#050a16', 110, 320)` | CSS 헤더 주석 "Deep-space operations deck"; 씬의 발광 요소가 전부 `AdditiveBlending`이라 어두운 무대 위에서만 성립(코드 구조에서 관찰) | 전 화면 기본 무대. 라이트 배경 도입 금지 |
| 인과 부호 색 문법 | + 청록(`--pos #3bd6f0`, 씬 `#2fb9d8`/HL `#7deeff`) / − 주황(`--neg #ff9257`, 씬 `#ff8a55`/HL `#ffb184`) / 국면반전 금색 `#ffdf8e` / 상승 틴트 `--up #ffb36b` / 하락 틴트 `--down #6fb5ff` | scene.js 주석 "regime-flip edges glow gold: the sign can invert depending on the macro regime"; 부호·방향이 텍스트를 읽기 전에 색으로 먼저 읽히게 하는 정보 설계 (근거는 금색만 주석 기록, 나머지는 코드에서 관찰됨) | 엣지·배지·틴트·범례 등 의미 전달 전용. 장식 사용 금지(§10) |
| HUD 계기 문법 | `--mono "Cascadia Mono", Consolas` 대문자 라벨(10–13px, tracking 0.06–0.14em: `.ph-title`·`.lg-h`·`.layer-tag`·배지·버전칩·수치), `#panel::before/::after` 14px 모서리 브래킷 틱, pill 칩(999px)·`LEVER` 마크·`◈`/`▸` 글리프 | (근거 미기록 — 코드에서 관찰됨; 관제 데크 은유를 UI 크롬에서 구현하는 일관 장치) | 라벨·수치·메타 전용. 한국어 본문에 mono 금지(본문은 Pretendard) |

## 2. 색 (Color)

| 토큰 | 값 | 역할 | 사용 제약 |
|---|---|---|---|
| `--bg0` | `#030610` | 최심 배경·로딩 오버레이 | — |
| `--bg1` | `#071021` | 표면 기준면(대비 계산 기준) | — |
| `--panel` | `rgba(8,15,31,.86)` | 유리 패널(+`backdrop-filter: blur(14px)`) | — |
| `--panel-solid` | `#0a1226` | 다이얼로그·토스트 불투명면 | — |
| `--chip` | `rgba(90,150,230,.10)` | 칩·버튼 채움 | — |
| `--line` | `rgba(120,180,255,.16)` | 헤어라인 보더 | — |
| `--line-strong` | `rgba(130,200,255,.38)` | 호버·강조 보더 | — |
| `--ink` | `#eaf3ff` | 본문 잉크 | CSS 주석: bg1 위 ~15:1 |
| `--ink-2` | `#aabfdd` | 보조 텍스트 | CSS 주석: ~9:1 |
| `--ink-3` | `#7288a8` | 장식 전용 | CSS 주석 "decorative only" — 본문 금지(의도적 sub-AA) |
| `--cy` | `#54e0ff` | 프라이머리 액센트·포커스 링 | — |
| `--cy-deep` | `#1a8fb5` | 딥 시안(파비콘 스트로크 계열) | — |
| `--pos` | `#3bd6f0` | 엣지: 같은 방향(+) | 의미 전용 |
| `--neg` | `#ff9257` | 엣지: 반대 방향(−) | 의미 전용 |
| `--up` | `#ffb36b` | 노드 틴트: 상승 | 의미 전용 |
| `--down` | `#6fb5ff` | 노드 틴트: 하락 | 의미 전용 |
| `--ok` | `#57e39a` | 균형 루프·성공 | — |
| `--warn` | `#ffd166` | 경고(stale 등) | — |

- **씬 상수(JS, `js/scene.js`)**: `COLOR_POS #2fb9d8` / `COLOR_NEG #ff8a55` / `COLOR_POS_HL #7deeff` / `COLOR_NEG_HL #ffb184` / 금색 반전 `#ffdf8e`. CSS 토큰(`--pos/--neg`)보다 살짝 깊은 값이다 (근거 미기록 — 코드에서 관찰됨; 가산 블렌딩 위 과포화를 피하는 조정으로 추정). CSS와 씬을 맞출 때 이 이중 정의를 함께 갱신할 것.
- **60/30/10 배분**: 지배 = 심연 네이비(`--bg0`/`--bg1`/`--panel` 계열) / 중립 = 얼음 잉크(`--ink`/`--ink-2`)와 하늘 헤어라인(`--line`) / 액센트 = 시안 `--cy`(+ 의미색 주황·금·초록은 신호 전용).
- **다크모드**: dark-only. `:root`에 `color-scheme: dark` 선언, 라이트 테마 없음 — 3D 가산 발광이 다크를 전제한다.
- **이 서비스의 금지 색**: 금색 `#ffdf8e`를 국면반전 외 용도로, `--pos/--neg/--up/--down`을 장식으로(공통 금지는 §10).
- **대비**: `--ink` ~15:1, `--ink-2` ~9:1 (`css/main.css` `:root` 인라인 주석에 계산 근거 명기). 의도적 sub-AA: `--ink-3`(장식 전용). 활성 상태 텍스트는 `#bdf0ff`/`#cdf3ff`(시안 알파 배경 위).

## 3. 타이포그래피 (Typography)

한국어 서비스의 현실: **본문은 Pretendard로 사실상 고정**이므로 본문 서체는 차별화 레버가 아니다. 이 서비스의 차별화는 **모노 계기 서체 + 시그니처 + 씬 모션**이 담당한다.

- **본문**: `--sans: "Pretendard Variable", Pretendard, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif` — **웹폰트 미로딩**(셀프호스트/CDN 없음; 로컬 설치 Pretendard에 의존, 미설치 환경은 Malgun Gothic 폴백). `word-break: keep-all` + `overflow-wrap: break-word` 전역(`:root`·`html,body`·`lang-toggle.css` 삼중, 불변층).
- **디스플레이/브랜드 폰트**: 없음. 워드마크 "MACROSCOPE"는 본문 스택 볼드 + tracking으로 처리(헤더 15px/0.04em, 404 페이지 13px/0.38em). 대신 계기 성격은 `--mono: "Cascadia Mono", Consolas, "Courier New"`가 맡는다(§1 시그니처 3).
- **스케일**: base 15px · line-height 1.55 · 패널 본문 13.5px · 노드명 19px/800 · 다이얼로그 h2 20px. 비율 스케일이 아니라 역할별 고정값(계기판 방식).
- **아이브로우/라벨 스펙**: mono 10–13px, tracking 0.06–0.14em, uppercase (`.ph-title` 13px/0.06em, `.lg-h` 10px/0.12em, `.layer-tag` 10px/0.14em).

## 4. 공간·형태 (Space & Shape)

- **radius 스케일**: `--radius 10px`(패널·범례) / 8px(카드·버튼·인풋) / 9px(검색·AI 인풋) / 14px(다이얼로그·모바일 바텀시트 상단) / 999px(pill·칩·토스트·모드탭) / 4–6px(마이크로 요소). 토큰은 `--radius` 하나뿐, 나머지는 리터럴(§8).
- **shadow 언어**: 드롭섀도 없음 — **발광이 섀도의 자리를 차지한다**. `box-shadow`는 시안 글로우 전용(`0 0 18px rgba(84,224,255,.22)` hl, `0 0 22px rgba(84,224,255,.4)` selected)과 inset 1px 링(활성 탭). 검정 드롭섀도 금지.
- **spacing**: 그리드 시스템 없음. 6/8/10/12/14px 고정 소값 — HUD 밀도 우선. `--hud-h 58px`(모바일에서는 실측 `--hud-real-h`로 대체).
- **카드 분리 정책**: 1px 헤어라인 보더(`--line`) + 반투명 네이비 면(`rgba(10,18,38,.55)`) + 호버 시 보더 발광. 홀로그램 관용구로서의 유색 반투명 헤어라인이며, 회색 보더 카드(AI-slop 신호)와 구별된다. 패널·범례는 `backdrop-filter: blur(14px)` 유리.
- **레이아웃 성격**: 전면 3D 무대(`#stage` fixed inset 0) 위에 HUD가 떠 있는 오버레이 구조. 데스크톱 우측 400px 패널, 모바일(≤900px)에서는 바텀시트(max-height 62dvh, 접기 토글)로 전환.

## 5. 모션 안무 (Motion Choreography)

토큰 목록이 아니라 **안무**를 기록한다 — 순서·딜레이·이징이 브랜드 감각의 절반이다.

- **duration/ease 토큰**: 없음(리터럴). CSS 전환 0.15–0.28s ease가 UI 기본, `spin` 0.9s linear가 유일한 CSS keyframes(로딩 링).
- **씬 안무(three.js Clock 절차 애니메이션이 본체)**:
  - **단계 파급 리플**: n차 파급 요소가 `(n−1)×0.45s` 지연 후 0.3s 페이드인(`setHighlight`).
  - **시차 펄스**: 하이라이트 엣지를 달리는 펄스의 이동 시간 = `0.4 + lag×0.4s` — scene.js 주석 원문 "시차가 눈에 보인다".
  - **도착 바운스**: 펄스 도착 시 대상 노드가 `1.6·e^(−3.5x)·sin(9x)`로 1.1s 상하 감쇠 진동(+는 밀어올림, −는 끌어내림).
  - **앰비언트**: 흐름 파티클 speed `0.05+0.035×strength`. (v2.6.0) 헤일로 브리딩 `1+sin(t×1.4+φ)×0.08`, 계기 유휴 자전 yaw `0.07~0.13 rad/s`(노드별 해시 위상) + 미세 장동 x±0.10/z±0.07 rad — 납작한 계기도 시간이 지나면 모든 실루엣을 보여준다. reduced-motion 시 전부 정지.
  - **카메라**: 950ms cubic in-out 트윈(`tweenCameraTo`), 사용자 입력 즉시 양보.
- **구현 방식**: CSS transitions + three.js Clock 기반 JS 절차 애니메이션. framer-motion 미사용.
- **reduced-motion 정책**: 전역 킬스위치. OS pref(`@media (prefers-reduced-motion)`) + 인앱 토글(`:root.reduce-motion` 강제 / `.motion-on`으로 OS 설정 위 opt-in 가능). 씬은 `reducedMotion` 플래그로 autoRotate·파티클·펄스·바운스 정지, 하이라이트는 즉시 표시.

## 6. 텍스처·깊이 (Texture & Depth)

- 노이즈/그레인 필름 없음 — 텍스처는 씬이 담당: 별 파티클(650), 플로어 링(5), 층 가이드 링, `Fog('#050a16')`, 캔버스 radial 글로우 스프라이트(`makeGlowTexture` 128px), `AdditiveBlending` 발광.
- (v2.6.0) **범주 헤일로**: 노드마다 범주색 가산 스프라이트(스케일 3.0×, 기본 opacity 0.30 / 선택 0.52 / 딤 0.05). depth-test를 켜 두어 계기 본체가 중심을 가리고 **림 글로우**로 읽힌다 — 어떤 각도에서도 유지되는 발광 실루엣("발광 인과 그래프" 헌장 복원). 오버레이 링 4종(선택·압력·도착·레버)은 매 프레임 카메라를 향해 빌보드(사이드 뷰에서 선으로 붕괴 방지).
- 유리 깊이: `--panel` + `blur(14px)`(패널·범례), `dialog::backdrop rgba(2,5,12,.72)` + `blur(3px)`.
- z-index 레지스트리: stage 0 / labels 1 / statusline 20 / legend 25 / panel 30 / hud-top 40 / toast 90 / loading 100 / fatal 110 / skip-link 200.

## 7. 데이터 시각화 팔레트 (해당 시)

2D 차트는 없으나 3D 그래프의 **변수 범주 9색이 사실상 카테고리 팔레트**다. 정본은 `data/nodes.js` `CATEGORIES`(수저작; 스키마 스펙 `docs/data-spec.md`), 다크 전용:

- 정책 `#2ff0c4` · 통화·금융 `#4fd8ff` · 자산시장 `#9d8cff` · 시장 심리 `#ff9ecb` · 실물경제 `#62d97e` · 물가·임금 `#ff7666` · 원자재 `#ffc857` · 외생 변수 `#e26bff` · 대외·환율 `#4d73ff`
- (260713 재조정) 공간 인접 섹터 간 색각이상 분리를 위해 4색만 이동: 정책 ↑민트(실물 초록과 분리), 실물 ↓초록, 외생 →마젠타, 대외·환율 →인디고(구 `#5f8dff`↔`#c678ff` protan ΔE 1.7이 최악이었음). 앵커 5색 유지.
- 노드 계기 인레이·바디 틴트(0.14 lerp)·헤일로·라벨 도트·칩 보더 틴트(color-mix 42%)·범례·검색 도트가 전부 이 9색에서 파생. 부호색(§1-2)과 역할이 겹치지 않게 유지할 것(범주 = 정체성, 부호 = 관계).
- **검증**: `validate_palette.js` 실행 (260713, dark, surface `#030610`, 씬 인접 링 순서): Chroma PASS · Contrast(≥3:1) PASS · CVD 인접 최악 `#4d73ff`↔`#e26bff` ΔE 10.5 protan = WARN 대역(8–12) — 전 노드 직접 라벨 + 범례의 2차 인코딩으로 허용. Lightness band는 8/9색 초과 — 차트 마크가 아닌 가산 글로우 팔레트의 의도적 특성(원 팔레트도 동일 시그니처), 수용. 텍스트 소비처(.cat-chip 11px)는 전 색 ≥4.5:1 확인(최저 `#4d73ff` 4.56:1).

## 8. 커버리지 정직성 (Coverage Honesty)

이 파일이 실제 CSS를 어디까지 대변하는지 정직하게 기록한다. 거짓 완전성은 다음 세션이 새 리터럴을 발명하게 만든다.

- **토큰화된 범위**: 표면·잉크·신호색 19종 + `--sans/--mono` + `--radius`(1종) + `--hud-h`만 `css/main.css :root` 토큰. 모션 duration·spacing·radius 나머지 단계는 전부 리터럴.
- **리터럴로 남은 범위**:
  - `css/main.css`: hex 25개(토큰 정의 포함). 반복 리터럴: `#bdf0ff` ×5(활성 시안 텍스트), `#cdf3ff` ×2(밝은 활성 텍스트), `rgba(84,224,255,…)` ×23(알파 시안 — 보더 .28–.45 / 채움 .10–.22 / 글로우 .22–.4 대역).
  - `js/scene.js`: 색 상수 8개 — CSS 토큰과 **다른 값**(§2 씬 상수 참조). 이중 정의 주의.
  - `js/ui.js`: hex 14개(온보딩 SVG 도해, 범례 스와치 `#ffdf8e`, 검색 타입 도트 `#ffd166`/`#57e39a`/`#54e0ff`).
  - `data/nodes.js`: 범주 9색(§7 정본).
  - `404.html`: 브랜드 색 인라인 복제(수동 미러 — main.css와 자동 동기화 없음).
  - `css/lang-toggle.css`: 활성 배경 `#2563eb` 드리프트는 **260713 해소** — `main.css`에서 `.lang-toggle { --lt-active-bg/--lt-active-fg/--lt-focus }`를 시안 계열(`rgba(84,224,255,.16)` + `#bdf0ff`)로 오버라이드(키트 파일은 무수정 유지).
- **확장 규칙**: 새 값 발명 전에 위 반복 리터럴 목록(특히 알파 시안 대역)에서 먼저 찾는다. 씬 색을 바꾸면 CSS 토큰·범례·온보딩 SVG·404까지 4곳 동기화.

## 9. 고정 슬롯 — 패밀리·키트 동기화 상태

| 슬롯 | 상태 | 비고 |
|---|---|---|
| maker-card-kit | 미적용 | 마커(`maker-card:css:start`) 없음 |
| i18n-kit (KO/EN) | 적용 | vanilla `js/i18n.js`(kit) + `data-i18n/-ph/-al/-ti` + `I18n.t`, KO 인라인 기본 + EN 사전(`data/strings.js`), meta 스왑. 활성 버튼 색 미치환은 §8 참조 |
| kakao-share-kit | 미적용 | |
| HubBacklink | 해당 없음 | 독립 서비스(VH 허브 비소속) |

## 10. 금지 목록 (Anti-slop)

**공통 금지**(모든 서비스, design-dna-kit README 정본): Inter/Roboto/Arial/Poppins/Space Grotesk를 디스플레이로, 흰 배경 보라-파랑 그라데이션, 회색 보더 카드 기본값, 히어로→3카드→로고 스트립 공식 레이아웃, 근거 없는 트렌드 이펙트, 미테마 스톡 컴포넌트.

**이 서비스 고유 금지**:
- 금색 `#ffdf8e`를 국면반전(⇄) 외 용도로 사용 금지 — 의미 예약색.
- `--pos/--neg/--up/--down`을 장식·브랜딩 용도로 사용 금지 — 부호 문법 전용.
- 라이트 테마·밝은 배경 도입 금지 — 씬 가산 발광이 다크 전제(§2 dark-only).
- 검정 드롭섀도 금지 — 이 서비스의 깊이 언어는 시안 글로우(§4).
- 본문·한국어 문장에 `--mono` 사용 금지(라벨·수치 전용), `--ink-3`를 본문에 사용 금지(장식 전용).
- 씬 렌더 루프에 `document.hidden` 게이트 추가 금지 — scene.js 주석: 숨김 탭 rAF는 브라우저가 이미 스로틀하며, 게이트는 첫 페인트·CSS2D 라벨 부착·백그라운드 검증 스크린샷을 깨뜨린다.

## 11. 근거 포인터 (Evidence)

- 브랜딩 결정 문서: 없음 — 디자인 근거는 코드 주석에만 존재(`css/main.css` 1–4행 헤더, `:root` 대비 주석, `js/scene.js` 금색 반전·시차 펄스·hidden 게이트 주석).
- CSS 계약 테스트: 없음.
- 로고/브랜드 자산 파이프라인: 없음 — 마크(라운드 사각 `#071021` + 지그재그 경로 `#2ba8c8` + 시안/주황/초록 3노드)는 `index.html` 파비콘 data-URI·헤더 인라인 SVG·`404.html`에 3중 인라인 정의(수동 동기화). 정적 자산: `og-image.png`(1200×630), `apple-touch-icon.png`, `theme-color #030610`.
- 브랜드 토큰 JSON: 없음.
- 데이터·콘텐츠 계약: `AGENTS.md`(Project Delta — CDN 금지·이중언어·검증 파이프라인), `docs/data-spec.md`, `scripts/build-data.py`.
- 관련 규칙: web-service-quality §1 (게이트) · visual-contrast-safety (대비) · cjk-rendering-safety (keep-all) · 메모리 `project_econ_systems_map`(생성 파일·전파모형·hidden 게이트 금지).

## 변경 이력

- 260712: DNA 확정 (design-dna 레트로핏 추출)
- 260713 (v2.6.0): 시각 존재감 개편. ①범주 헤일로(림 글로우, §6) + 오버레이 링 카메라 빌보드 — 사이드 뷰에서 평면 요소가 사라지던 문제 해결 ②계기 유휴 자전+장동(§5) ③accent 인레이 emissive 0.07→0.55(선택 0.9), 바디 범주 틴트 0.14 — "다 같은 색" 문제 해결 ④범주 팔레트 4색 재조정 + validate_palette.js 검증 기록(§7) ⑤범례에 '변수 분류' 헤딩 신설·최상단 이동, 라벨 칩 보더 범주 틴트(color-mix 42%), lang-toggle 드리프트 해소(§8)
