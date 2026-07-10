// Canonical node/category definitions. Single source of truth: docs/data-spec.md
// Node descriptions live in data/descs.js (merged at runtime by id).
//
// SPATIAL SEMANTICS (every coordinate means something):
//   layer  (Y, height)      : 관념 -> 실물 스펙트럼. 심리·기대(맨 위) / 정책·외생 충격 /
//                             돈·자산 시장 / 실물경제 / 원자재(맨 아래)
//   radius (dist. to center): 국내 <-> 글로벌. GDP가 중심, 연준·지정학·유가는 바깥 궤도
//   angle  (sector)         : 도메인 군집 + 수직 정렬(기대인플레이션은 소비자물가 위,
//                             투자심리는 주가 위, 기준금리는 시장금리 위, 지정학은 유가 위)

export const CATEGORIES = [
  { id: 'policy',      name: { ko: '정책',      en: 'Policy' },          color: '#35d0b0' },
  { id: 'monetary',    name: { ko: '통화·금융', en: 'Money & Credit' },  color: '#4fd8ff' },
  { id: 'assets',      name: { ko: '자산시장',  en: 'Asset Markets' },   color: '#9d8cff' },
  { id: 'psychology',  name: { ko: '시장 심리', en: 'Psychology' },      color: '#ff9ecb' },
  { id: 'real',        name: { ko: '실물경제',  en: 'Real Economy' },    color: '#6fe38a' },
  { id: 'prices',      name: { ko: '물가·임금', en: 'Prices & Wages' },  color: '#ff7666' },
  { id: 'commodities', name: { ko: '원자재',    en: 'Commodities' },     color: '#ffc857' },
  { id: 'exogenous',   name: { ko: '외생 변수', en: 'Exogenous' },       color: '#c678ff' },
  { id: 'external',    name: { ko: '대외·환율', en: 'External & FX' },   color: '#5f8dff' },
];

export const LAYERS = [
  { id: 'mind',     y: 26,  name: { ko: '심리·기대',     en: 'Sentiment & Expectations' } },
  { id: 'policy',   y: 13,  name: { ko: '정책·외생 충격', en: 'Policy & External Shocks' } },
  { id: 'finance',  y: 0,   name: { ko: '돈·자산 시장',   en: 'Money & Asset Markets' } },
  { id: 'real',     y: -13, name: { ko: '실물경제',       en: 'Real Economy' } },
  { id: 'resource', y: -24, name: { ko: '원자재·에너지',  en: 'Commodities & Energy' } },
];

export const NODES = [
  // finance layer (y 0) — the circulation system
  { id: 'policy_rate',    cat: 'monetary',    lever: true,  layer: 'policy',   angle: 15,  radius: 18, name: { ko: '기준금리',           en: 'Policy Rate' } },
  { id: 'market_rate',    cat: 'monetary',    lever: false, layer: 'finance',  angle: 10,  radius: 30, name: { ko: '시장금리',           en: 'Market Rate' } },
  { id: 'liquidity',      cat: 'monetary',    lever: false, layer: 'finance',  angle: 35,  radius: 22, name: { ko: '유동성 (M2)',        en: 'Liquidity (M2)' } },
  { id: 'credit_spread',  cat: 'monetary',    lever: false, layer: 'finance',  angle: 355, radius: 38, name: { ko: '신용스프레드',       en: 'Credit Spread' } },
  { id: 'bank_lending',   cat: 'monetary',    lever: false, layer: 'finance',  angle: 50,  radius: 32, name: { ko: '은행 대출',          en: 'Bank Lending' } },

  // prices: CPI/wages on the ground, expectations in the sky right above them
  { id: 'cpi',            cat: 'prices',      lever: false, layer: 'real',     angle: 238, radius: 24, name: { ko: '소비자물가',         en: 'Consumer Prices' } },
  { id: 'inflation_exp',  cat: 'prices',      lever: false, layer: 'mind',     angle: 230, radius: 26, name: { ko: '기대인플레이션',     en: 'Inflation Expectations' } },
  { id: 'wages',          cat: 'prices',      lever: false, layer: 'real',     angle: 218, radius: 28, name: { ko: '임금',               en: 'Wages' } },

  // external: the boundary and the outer orbit
  { id: 'fx',             cat: 'external',    lever: true,  layer: 'finance',  angle: 335, radius: 38, name: { ko: '원/달러 환율',       en: 'KRW/USD Rate' } },
  { id: 'exports',        cat: 'external',    lever: false, layer: 'real',     angle: 305, radius: 36, name: { ko: '수출',               en: 'Exports' } },
  { id: 'current_account', cat: 'external',   lever: false, layer: 'real',     angle: 322, radius: 28, name: { ko: '경상수지',           en: 'Current Account' } },
  { id: 'capital_flows',  cat: 'external',    lever: false, layer: 'finance',  angle: 315, radius: 40, name: { ko: '외국인 자본 유입',   en: 'Capital Inflows' } },
  { id: 'fed_rate',       cat: 'external',    lever: true,  layer: 'policy',   angle: 330, radius: 50, name: { ko: '미국 기준금리',      en: 'US Fed Rate' } },
  { id: 'global_growth',  cat: 'external',    lever: false, layer: 'real',     angle: 345, radius: 54, name: { ko: '글로벌 경기',        en: 'Global Growth' } },

  // real economy (y -13), GDP at the very center: everything converges into it
  { id: 'consumption',    cat: 'real',        lever: false, layer: 'real',     angle: 145, radius: 24, name: { ko: '가계 소비',          en: 'Consumption' } },
  { id: 'investment',     cat: 'real',        lever: false, layer: 'real',     angle: 193, radius: 26, name: { ko: '기업 투자',          en: 'Investment' } },
  { id: 'employment',     cat: 'real',        lever: false, layer: 'real',     angle: 172, radius: 28, name: { ko: '고용',               en: 'Employment' } },
  { id: 'earnings',       cat: 'real',        lever: false, layer: 'real',     angle: 85,  radius: 26, name: { ko: '기업실적',           en: 'Corporate Earnings' } },
  { id: 'defaults',       cat: 'real',        lever: false, layer: 'real',     angle: 55,  radius: 36, name: { ko: '부도·연체',          en: 'Defaults' } },
  { id: 'gdp',            cat: 'real',        lever: false, layer: 'real',     angle: 160, radius: 6,  name: { ko: '경제성장 (GDP)',     en: 'GDP Growth' } },

  // asset markets (finance layer), sentiment floating right above stocks
  { id: 'stocks',         cat: 'assets',      lever: false, layer: 'finance',  angle: 75,  radius: 30, name: { ko: '주가',               en: 'Stock Prices' } },
  { id: 'housing',        cat: 'assets',      lever: false, layer: 'finance',  angle: 95,  radius: 34, name: { ko: '부동산 가격',        en: 'Housing Prices' } },
  { id: 'household_debt', cat: 'assets',      lever: false, layer: 'finance',  angle: 115, radius: 34, name: { ko: '가계부채',           en: 'Household Debt' } },

  // bedrock (y -24), on the outer half: raw inputs from the world
  { id: 'oil',            cat: 'commodities', lever: true,  layer: 'resource', angle: 265, radius: 46, name: { ko: '유가',               en: 'Oil Price' } },
  { id: 'commodity',      cat: 'commodities', lever: false, layer: 'resource', angle: 243, radius: 40, name: { ko: '원자재',             en: 'Commodities' } },

  // decision layer (y +13): domestic levers near center, foreign forces outside
  { id: 'fiscal',         cat: 'policy',      lever: true,  layer: 'policy',   angle: 165, radius: 18, name: { ko: '재정지출',           en: 'Fiscal Spending' } },
  { id: 'geopolitics',    cat: 'exogenous',   lever: true,  layer: 'policy',   angle: 275, radius: 52, name: { ko: '지정학 리스크',      en: 'Geopolitical Risk' } },
  { id: 'tech',           cat: 'exogenous',   lever: false, layer: 'real',     angle: 205, radius: 40, name: { ko: '기술·생산성',        en: 'Tech & Productivity' } },

  // the sky (y +26): what people feel and expect
  { id: 'risk_sentiment', cat: 'psychology',  lever: false, layer: 'mind',     angle: 70,  radius: 30, name: { ko: '투자심리 (탐욕·공포)', en: 'Investor Sentiment' } },
  { id: 'consumer_conf',  cat: 'psychology',  lever: false, layer: 'mind',     angle: 150, radius: 26, name: { ko: '소비자심리',         en: 'Consumer Confidence' } },
];

// Simulator levers (order = slider order). Values are shock units in [-1, 1].
export const SIM_LEVERS = [
  { id: 'policy_rate', hint: { ko: '한국은행이 금리를 올리거나 내립니다', en: 'The Bank of Korea raises or cuts rates' } },
  { id: 'oil',         hint: { ko: '국제 유가가 급등하거나 급락합니다',   en: 'Global oil prices spike or crash' } },
  { id: 'fx',          hint: { ko: '원/달러 환율이 오르거나(원화 약세) 내립니다', en: 'KRW/USD rises (weaker won) or falls' } },
  { id: 'fed_rate',    hint: { ko: '미국 연준이 금리를 올리거나 내립니다', en: 'The US Fed hikes or cuts' } },
  { id: 'fiscal',      hint: { ko: '정부가 지출을 늘리거나 줄입니다', en: 'The government expands or cuts spending' } },
  { id: 'geopolitics', hint: { ko: '전쟁·분쟁 등 지정학 긴장이 높아지거나 낮아집니다', en: 'Geopolitical tension rises or eases' } },
];

export const SIM_PRESETS = [
  { id: 'tightening', name: { ko: '긴축 사이클', en: 'Tightening Cycle' }, shocks: { policy_rate: 0.75, fed_rate: 0.75 } },
  { id: 'oilshock',   name: { ko: '오일쇼크',    en: 'Oil Shock' },        shocks: { oil: 1 } },
  { id: 'weakwon',    name: { ko: '원화 약세',   en: 'Weak Won' },         shocks: { fx: 0.75 } },
  { id: 'easing',     name: { ko: '완화 전환',   en: 'Easing Pivot' },     shocks: { policy_rate: -0.75, fed_rate: -0.5 } },
];
