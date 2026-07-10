# Data Spec (canonical, v1)

이 문서가 인과 그래프 데이터의 단일 진실원 스키마다. 모든 콘텐츠 저작(엣지·사례·루프)은 여기 정의된 노드 ID만 참조한다.

## Spatial semantics (v1.1, 260710)

노드 좌표는 장식이 아니라 의미다. `data/nodes.js`의 노드별 `layer`/`angle`/`radius` 필드가 위치를 결정한다.

- 높이(layer, Y): 관념 → 실물 스펙트럼 5층. 심리·기대(+26) / 정책·외생 충격(+13) / 돈·자산 시장(0) / 실물경제(-13) / 원자재·에너지(-24)
- 반경(radius): 국내 ↔ 글로벌. GDP가 중심(r6), 연준·글로벌 경기·지정학·유가는 바깥 궤도(r46~54)
- 각도(angle): 도메인 섹터 + 수직 정렬. 기대인플레이션은 소비자물가 위, 투자심리는 주가 위, 기준금리는 시장금리 위, 재정지출은 GDP 위, 지정학은 유가 위, 연준은 환율·자본유입 위
- 292° 방향은 층 이름표 전용 빈 섹터로 비워 둔다 (새 노드 배치 금지)

## Categories (9)

| id | ko | en | hue |
|---|---|---|---|
| monetary | 통화·금융 | Money & Credit | cyan |
| prices | 물가·임금 | Prices & Wages | red-orange |
| external | 대외·환율 | External & FX | blue |
| real | 실물경제 | Real Economy | green |
| assets | 자산시장 | Asset Markets | violet |
| commodities | 원자재 | Commodities | amber |
| policy | 정책 | Policy | teal |
| exogenous | 외생 변수 | Exogenous Forces | magenta |
| psychology | 시장 심리 | Market Psychology | pink |

## Nodes (30) — canonical IDs

| id | ko | en | cat | lever |
|---|---|---|---|---|
| policy_rate | 기준금리 | Policy Rate (BOK) | monetary | Y |
| market_rate | 시장금리 (국채 10년) | Long-term Market Rate | monetary | |
| liquidity | 유동성 (M2) | Liquidity (M2) | monetary | |
| credit_spread | 신용스프레드 | Credit Spread | monetary | |
| bank_lending | 은행 대출 | Bank Lending | monetary | |
| cpi | 소비자물가 | Consumer Prices (CPI) | prices | |
| inflation_exp | 기대인플레이션 | Inflation Expectations | prices | |
| wages | 임금 | Wages | prices | |
| fx | 원/달러 환율 | KRW/USD Exchange Rate | external | Y |
| exports | 수출 | Exports | external | |
| current_account | 경상수지 | Current Account | external | |
| capital_flows | 외국인 자본 유입 | Foreign Capital Inflows | external | |
| fed_rate | 미국 기준금리 | US Fed Funds Rate | external | Y |
| global_growth | 글로벌 경기 | Global Growth | external | |
| consumption | 가계 소비 | Household Consumption | real | |
| investment | 기업 투자 | Business Investment | real | |
| employment | 고용 | Employment | real | |
| earnings | 기업실적 | Corporate Earnings | real | |
| defaults | 부도·연체 | Defaults & Delinquencies | real | |
| gdp | 경제성장 (GDP) | GDP Growth | real | |
| stocks | 주가 | Stock Prices | assets | |
| housing | 부동산 가격 | Housing Prices | assets | |
| household_debt | 가계부채 | Household Debt | assets | |
| oil | 유가 | Oil Price | commodities | Y |
| commodity | 원자재 (금속·곡물) | Commodities (Metals & Grains) | commodities | |
| fiscal | 재정지출 | Fiscal Spending | policy | Y |
| geopolitics | 지정학 리스크 | Geopolitical Risk | exogenous | Y |
| tech | 기술·생산성 | Technology & Productivity | exogenous | |
| risk_sentiment | 투자심리 (탐욕과 공포) | Investor Sentiment (Greed & Fear) | psychology | |
| consumer_conf | 소비자심리 | Consumer Confidence | psychology | |

주의: `fx`의 방향 관례 = "원/달러 환율 상승 = 원화 약세". `capital_flows`의 방향 관례 = "값 상승 = 유입 증가".

## Edge schema

```
{
  from: <node id>, to: <node id>,
  sign: 1 | -1,          // from 상승 시 to에 미치는 방향
  strength: 1 | 2 | 3,   // 약함 / 중간 / 강함
  lag: 0 | 1 | 2 | 3,    // 즉시~1개월 / 1~6개월 / 6~18개월 / 18개월+
  confidence: 1 | 2 | 3, // 논쟁적 / 일반적 / 교과서 합의
  mech: { ko, en },      // 쉬운 언어 한 문장 (KO 40~90자). 중학생도 이해할 것
  source: "BOK" | "Mishkin" | "Mankiw" | "IMF" | "BIS" | "Dalio" | "Shiller" | "Minsky" | "Empirical",
  note?: { ko, en },     // 조건·뉘앙스 (J커브, 단기/장기 반전 등). 선택
  flip?: { ko, en }      // 국면 반전: 부호가 뒤집히는 조건 (v2, flips.json에서 병합). UI에 ⇄배지+금색 강조
}
```

## Case schema (역사 사례)

```
{
  id, title: {ko,en}, period: "1973-1982",
  phases: [  // 정확히 5단계: cause / spread / policy / psychology / outcome
    { key: "cause", title: {ko,en}, narration: {ko,en},  // 2~4문장, 쉬운 언어
      focusNodes: [ids], activeEdges: [[from,to],...], shocks: { nodeId: -1..1 } }
  ],
  comparison: { common: {ko,en}, differences: {ko,en} },  // 구조적 비교, 시점 표기 "2026년 초 기준"
  sources: [ "실제 문헌·데이터 출처 문자열" ]
}
```

## Loop schema (피드백 루프)

```
{ id, name: {ko,en}, type: "reinforcing" | "balancing",
  nodes: [ordered cycle ids],  // 마지막→처음으로 닫힘
  story: {ko,en},              // 3~4문장
  example: {ko,en} }           // 역사적 사례 1~2문장
```

## Content principles

- 교과서 수준의 정형화된 메커니즘만. 논쟁적 관계는 confidence 1 + note로 정직하게.
- 수치는 널리 알려진 것만 (예: 1997년 원/달러 800원대→1,960원대). 불확실하면 수치 생략.
- 예측·투자조언 문구 금지. 비유 환영 ("돈줄을 조인다", "달러가 비싸진다").
- 한국 경제 관점 기본 (원유 수입국, 수출 주도, 소규모 개방경제).
