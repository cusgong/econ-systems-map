// NOW situation board snapshot. Manually updated; every item carries its source + data date.
// Provenance: 3 parallel web researchers + independent cross-check verifier, 2026-07-10
// (see docs/session-log.md). Update path: edit this file, keep asOf honest.
export const SITUATION = {
  asOf: '2026-07-10',

  readings: [
    {
      node: 'policy_rate', trend: 0,
      value: { ko: '연 2.50%', en: '2.50%' },
      note: {
        ko: '2025년 5월 인하 후 8회 연속 동결. 다만 5월 금통위에서 2명이 인상 소수의견을 냈습니다.',
        en: 'On hold for 8 straight meetings since the May 2025 cut, but two board members dissented for a hike in May.',
      },
      source: '한국은행 금융통화위원회', date: '2026-05-28',
    },
    {
      node: 'fed_rate', trend: 0,
      value: { ko: '상단 3.75%', en: '3.75% upper' },
      note: {
        ko: '4회 연속 동결. 미국 물가가 5월 4.2%로 다시 뛰며 6월 점도표에서는 인하 전망이 사라지고 인상 가능성이 시사됐습니다.',
        en: 'Held for a 4th meeting. With US CPI back up to 4.2% in May, the June dot plot dropped cuts and hinted at hikes.',
      },
      source: 'Fed FOMC · BLS', date: '2026-06-17',
    },
    {
      node: 'market_rate', trend: 1,
      value: { ko: '국고 10년 약 4.2%', en: '10y KTB ~4.2%' },
      note: {
        ko: '1년 전보다 약 1.4%p 높고, 6월 초 4.33%까지 올라 2023년 11월 이후 최고치를 기록했습니다.',
        en: 'About 1.4%p higher than a year ago; touched 4.33% in early June, the highest since Nov 2023.',
      },
      source: 'Trading Economics', date: '2026-07-06',
    },
    {
      node: 'cpi', trend: 1,
      value: { ko: '3.2% (6월, 전년比)', en: '3.2% YoY (Jun)' },
      note: {
        ko: '석유류가 24.7% 급등하며 두 달 연속 3%대, 2년 6개월 만의 최고 상승률입니다.',
        en: 'Fuel prices jumped 24.7%, keeping inflation in the 3% range for a 2nd month, a 2.5-year high.',
      },
      source: '통계청 소비자물가동향', date: '2026-06',
    },
    {
      node: 'inflation_exp', trend: 1,
      value: { ko: '2.8% (향후 1년)', en: '2.8% (1y ahead)' },
      note: {
        ko: '3월 2.7%에서 오른 뒤 두 달 연속 2.8%로, 기대가 조금씩 높아진 상태입니다.',
        en: 'Up from 2.7% in March and holding at 2.8%, expectations have crept higher.',
      },
      source: '한국은행 소비자동향조사', date: '2026-06',
    },
    {
      node: 'fx', trend: 1,
      value: { ko: '약 1,506원', en: '~1,506 KRW/USD' },
      note: {
        ko: '1월 1,420원대에서 올라 1,500원 안팎의 고환율이 이어지고 있습니다. 중동발 유가 상승이 원화 약세 압력입니다.',
        en: 'Up from the 1,420s in January to around 1,500. Middle East oil pressure is weighing on the won.',
      },
      source: '서울외환시장 종가', date: '2026-07-09',
    },
    {
      node: 'oil', trend: 1,
      value: { ko: '브렌트 약 77달러', en: 'Brent ~$77' },
      note: {
        ko: '3월 호르무즈 봉쇄로 120달러 선까지 치솟았다가 6월 종전 합의 후 내렸지만, 7월 초 충돌 재점화로 73~79달러 사이에서 출렁입니다.',
        en: 'Spiked to ~$120 during the March Hormuz blockade, fell after the June accord, now swinging $73-79 on renewed clashes.',
      },
      source: 'Trading Economics', date: '2026-07-09',
    },
    {
      node: 'geopolitics', trend: 1,
      value: { ko: '높음 (중동 전쟁 진행)', en: 'Elevated (Mideast war)' },
      note: {
        ko: '2월 말 시작된 미국·이스라엘-이란 전쟁이 6월 종전 합의에도 불씨가 남아 있고, 러시아-우크라이나 전쟁도 계속 중입니다.',
        en: 'The US/Israel-Iran war that began in late February still smolders despite the June accord; Russia-Ukraine grinds on.',
      },
      source: 'IEA · CRS · Al Jazeera', date: '2026-07',
    },
    {
      node: 'stocks', trend: 1,
      value: { ko: 'KOSPI 약 7,290', en: 'KOSPI ~7,290' },
      note: {
        ko: '1월 사상 첫 5,000 돌파 후 8,200선까지 올랐다가, 중동 리스크와 외국인 13거래일 연속 순매도로 7,200선대로 조정됐습니다.',
        en: 'First-ever 5,000 in January, ran past 8,200, then corrected to the 7,200s on Mideast risk and 13 straight days of foreign selling.',
      },
      source: '한국거래소 종가', date: '2026-07-09',
    },
    {
      node: 'housing', trend: 1,
      value: { ko: '서울 주간 +0.25%', en: 'Seoul +0.25%/wk' },
      note: {
        ko: '서울 아파트값이 16주 연속 상승, 최근 1년간 약 15% 올랐습니다. 지방은 보합입니다.',
        en: 'Seoul apartments up 16 weeks in a row, roughly +15% over the past year; the rest of the country is flat.',
      },
      source: '한국부동산원', date: '2026-06',
    },
    {
      node: 'household_debt', trend: 1,
      value: { ko: '6월 +8.3조 원', en: '+8.3tn KRW (Jun)' },
      note: {
        ko: '전 금융권 가계대출이 6개월 연속 증가했고, 은행권 증가폭은 22개월 만에 최대입니다.',
        en: 'Household lending rose for a 6th straight month; the bank-sector increase was the largest in 22 months.',
      },
      source: '금융위원회', date: '2026-06',
    },
    {
      node: 'exports', trend: 1,
      value: { ko: '6월 +70.9%', en: '+70.9% YoY (Jun)' },
      note: {
        ko: '반도체 수출이 3배(+199.5%)로 뛰며 사상 첫 월 1,000억 달러를 돌파했습니다. 무역흑자도 사상 최대입니다.',
        en: 'Chip exports tripled (+199.5%), pushing monthly exports past $100B for the first time ever, with a record trade surplus.',
      },
      source: '산업통상자원부', date: '2026-06',
    },
    {
      node: 'current_account', trend: 1,
      value: { ko: '5월 +386억 달러', en: '+$38.6B (May)' },
      note: {
        ko: '역대 최대 월간 흑자로 37개월 연속 흑자입니다. 연간 흑자가 전망치 2,500억 달러를 넘을 가능성이 커졌습니다.',
        en: 'A record monthly surplus, the 37th in a row; the annual surplus may exceed the $250B forecast.',
      },
      source: '한국은행 국제수지(잠정)', date: '2026-05',
    },
    {
      node: 'employment', trend: -1,
      value: { ko: '취업자 -4만 명 (5월)', en: '-40k jobs (May)' },
      note: {
        ko: '취업자 수가 1년 5개월 만에 감소로 돌아섰습니다. 광공업·건설 부진에 청년 고용률도 하락했습니다.',
        en: 'Employment fell for the first time in 17 months, dragged by manufacturing and construction; youth employment slipped too.',
      },
      source: '통계청 고용동향', date: '2026-05',
    },
    {
      node: 'wages', trend: -1,
      value: { ko: '+1.5% (4월, 명목)', en: '+1.5% nominal (Apr)' },
      note: {
        ko: '임금 상승률이 물가 상승률(3% 안팎)을 크게 밑돌아, 실질임금은 줄어드는 국면입니다.',
        en: 'Wage growth is running well below ~3% inflation, so real wages are shrinking.',
      },
      source: '고용노동부 사업체노동력조사', date: '2026-04',
    },
    {
      node: 'gdp', trend: 1,
      value: { ko: '올해 2.6% 전망', en: '2.6% forecast (2026)' },
      note: {
        ko: '1분기 성장률이 전기 대비 1.8%로 강했고, IMF와 한국은행 모두 올해 전망을 2.6%로 올렸습니다. 다만 반도체 쏠림이 큽니다.',
        en: 'Q1 grew 1.8% QoQ, and both the IMF and BOK raised this year\'s forecast to 2.6%, though heavily chip-driven.',
      },
      source: 'IMF 7월 수정전망 · 한국은행', date: '2026-07',
    },
    {
      node: 'global_growth', trend: -1,
      value: { ko: '세계 3.0% 전망', en: 'World 3.0% forecast' },
      note: {
        ko: 'IMF가 중동 전쟁 충격을 반영해 4월보다 0.1%p 낮췄습니다. AI 투자 붐이 충격을 일부 상쇄하고 있습니다.',
        en: 'The IMF trimmed 0.1%p from April on the Mideast war, partly offset by the AI investment boom.',
      },
      source: 'IMF WEO 7월 수정', date: '2026-07',
    },
  ],

  themes: [
    {
      id: 'hormuz-oil-shock',
      title: { ko: '중동 전쟁과 유가 충격', en: 'The Mideast War and the Oil Shock' },
      body: {
        ko: '2026년 2월 말 미국·이스라엘의 이란 공습으로 전쟁이 시작됐고, 이란은 세계 원유 해상 수송의 핵심 통로인 호르무즈 해협을 봉쇄했습니다. 3월 브렌트유는 배럴당 120달러 선까지 치솟았고 IEA는 역사상 최대의 원유 공급 차질로 평가했습니다. 6월 17일 종전 합의에도 충돌이 이어져 7월 초 유가는 73~79달러 사이에서 출렁이고 있습니다. 기름값이 오르면 한국의 수입 물가와 소비자물가가 함께 오르기 때문에, 6월 물가 3.2%의 가장 큰 원인이 바로 이 경로였습니다. 지도에서 지정학 리스크 → 유가 → 소비자물가 → 기준금리로 이어지는 사슬을 따라가 보세요.',
        en: 'War began in late February 2026 with US-Israeli strikes on Iran, and Iran blockaded the Strait of Hormuz, the key artery of seaborne oil. Brent spiked to about $120 in March, which the IEA called the largest supply disruption in oil-market history. Despite the June 17 accord, clashes continue and oil now swings between $73 and $79. Costlier oil feeds straight into Korean import and consumer prices; it was the biggest driver of June\'s 3.2% inflation. Trace the chain on the map: geopolitical risk into oil, into consumer prices, into the policy rate.',
      },
      nodes: ['geopolitics', 'oil', 'cpi', 'fx', 'policy_rate'],
      edges: [['geopolitics', 'oil'], ['oil', 'cpi'], ['geopolitics', 'fx'], ['fx', 'cpi'], ['cpi', 'policy_rate']],
      relatedCase: 'oil_shock_stagflation_1973',
      relatedLoop: null,
      sources: [
        'IEA Oil Market Report (2026-03): 하루 800만 배럴 공급 차질 평가',
        '미 의회조사국(CRS) · Britannica: 2026 이란 전쟁 및 호르무즈 위기 경과',
        'Al Jazeera · CNBC (2026-07-08): 종전 합의 이후 충돌 재점화와 유가 반등',
      ],
    },
    {
      id: 'ai-chip-supercycle',
      title: { ko: 'AI 반도체 슈퍼사이클', en: 'The AI Chip Supercycle' },
      body: {
        ko: '전 세계가 AI 데이터센터에 돈을 쏟아부으면서 한국산 메모리 반도체(HBM 등) 주문이 폭발했습니다. 6월 한국 수출은 1년 전보다 70.9% 늘어난 1,022억 달러로 사상 처음 월 1,000억 달러를 넘었고(세계 4번째), 그중 반도체가 448억 달러로 1년 전의 약 3배가 됐습니다. 한국은행이 올해 성장률 전망을 2.0%에서 2.6%로 올린 것도 이 힘입니다. 다만 성장의 대부분이 반도체 한 품목에 쏠려 있고, 메모리는 호황과 불황을 오가는 산업이라 과열 경계론도 나옵니다. 지도에서 기술·생산성 → 기업실적 → 주가, 그리고 수출 → 성장의 경로가 지금 가장 뜨거운 사슬입니다.',
        en: 'A global AI datacenter buildout has set off explosive demand for Korean memory chips (HBM above all). June exports hit $102.2B, up 70.9% and the first $100B month ever (4th country to do so), with semiconductors nearly tripling to $44.8B. This is why the Bank of Korea raised its growth forecast from 2.0% to 2.6%. But the boom is concentrated in one product, and memory is a famously cyclical business, so overheating warnings are out. On the map, tech into earnings into stocks, and exports into growth, are the hottest chains right now.',
      },
      nodes: ['tech', 'exports', 'earnings', 'stocks', 'gdp'],
      edges: [['tech', 'earnings'], ['exports', 'earnings'], ['earnings', 'stocks'], ['exports', 'gdp'], ['tech', 'gdp']],
      relatedCase: 'dotcom-bubble-2000',
      relatedLoop: 'growth_engine',
      sources: [
        '산업통상자원부 수출입 동향 (2026-07-01): 6월 수출 1,022.5억 달러, 반도체 +199.5%',
        'TrendForce · DigiTimes (2025-12): HBM3E 약 20% 가격 인상, HBM4 스택당 약 500달러',
        '한국은행 경제전망 (2026-05): 성장률 2.0→2.6%, 물가 2.2→2.7% 상향',
      ],
    },
    {
      id: 'us-tariff-upheaval',
      title: { ko: '미국 관세 대격변', en: 'The US Tariff Upheaval' },
      body: {
        ko: '2026년 2월 미국 연방대법원이 IEEPA 관세를 위법으로 판결해 2025년부터 걷힌 관세의 환급(400억 달러 이상 지급)이 시작됐습니다. 미국 정부는 곧바로 무역법 122조로 10% 보편관세를 다시 매겼는데 이 역시 위법 판정을 받고 항소 중이며 7월 24일이 법정 시한입니다. 반도체에는 1월부터 232조 25% 관세가 고성능 AI 칩 중심으로 적용되고 있고, 한국은 2025년 7월 관세율 15% 상한 합의로 완충을 확보한 상태입니다. 미중 관세 휴전은 11월 초 만료를 앞두고 연장 협상 중입니다. 규칙이 몇 달 단위로 바뀌는 것 자체가 기업 투자를 망설이게 하는 불확실성입니다.',
        en: 'In February 2026 the US Supreme Court struck down the IEEPA tariffs, triggering refunds (over $40B paid so far). The administration immediately re-imposed a 10% universal tariff under Section 122, which was also ruled unlawful and is on appeal, with July 24 as the statutory deadline. Since January, Section 232 puts 25% on advanced AI chips, while Korea\'s July 2025 deal caps its tariff rate at 15%. The US-China truce expires in early November and extension talks are underway. Rules that change every few months are themselves a tax on business investment.',
      },
      nodes: ['geopolitics', 'exports', 'global_growth', 'investment'],
      edges: [['geopolitics', 'exports'], ['geopolitics', 'global_growth'], ['global_growth', 'exports'], ['exports', 'gdp']],
      relatedCase: null,
      relatedLoop: null,
      sources: [
        'Learning Resources v. United States (2026-02-20) 및 CBP CAPE 환급 집계 (Holland & Knight · Skadden 분석)',
        '백악관 232조 반도체 관세 포고문 (2026-01-14 발령, 01-15 발효)',
        'Bloomberg · China Briefing: 부산 합의(2025-10-30)와 2026-11-09 휴전 시한',
      ],
    },
    {
      id: 'housing-debt-rate-turn',
      title: { ko: '집값·가계부채와 금리 인상 신호', en: 'Housing, Debt, and the Turn Toward Hikes' },
      body: {
        ko: '서울 아파트값이 1년 새 약 15% 오르며 빚내서 집 사는 흐름이 되살아났습니다. 6월 은행 가계대출은 7조 6천억 원 늘어 22개월 만의 최대 증가폭입니다. 은행들은 주담대 한도를 줄이고 금융당국은 관리계획 재제출을 지시하는 등 대출 조이기가 시작됐습니다. 한국은행은 금리를 2.50%로 동결 중이지만 6월 금융안정보고서에서 "적절한 시기에 인상할 필요"를 명시했고, 5월 금통위에서는 인상 소수의견도 나왔습니다. 지도의 "집값과 대출의 눈덩이" 루프가 실제로 굴러가는 중이고, 중앙은행이 그 고리를 끊을지 고민하는 국면입니다.',
        en: 'Seoul apartment prices are up about 15% in a year, reviving leveraged home buying. Bank household loans grew 7.6 trillion won in June, the most in 22 months. Banks are cutting mortgage limits and regulators demanded new lending plans. The Bank of Korea is holding at 2.50% but its June Financial Stability Report explicitly flagged the need to hike "at an appropriate time," and two board members dissented for a hike in May. The map\'s "credit snowball" loop is literally rolling; the central bank is deciding whether to cut the wire.',
      },
      nodes: ['housing', 'household_debt', 'bank_lending', 'policy_rate'],
      edges: [['bank_lending', 'housing'], ['housing', 'bank_lending'], ['housing', 'household_debt'], ['household_debt', 'consumption']],
      relatedCase: 'gfc-2008',
      relatedLoop: 'credit_cycle',
      sources: [
        '한국은행 2026년 6월 금융시장 동향 (2026-07-09): 은행 가계대출 +7.6조 원',
        '한국은행 금융안정보고서 (2026-06-24): 금융불균형 경고와 금리 인상 필요 명시',
        '금융위원회 가계대출 동향 (2026-06): 전 금융권 +8.3조 원, 주담대 +4.5조 원',
      ],
    },
    {
      id: 'china-two-speed',
      title: { ko: '중국: 수출 강세, 내수 부진', en: 'China: Strong Exports, Weak Home Demand' },
      body: {
        ko: '중국의 1분기 성장률은 5.0%로 예상(4.8%)을 웃돌았지만, 성장의 대부분이 수출에서 나왔고 소비와 부동산은 여전히 약합니다. 신규 주택 착공은 2021년 고점 대비 약 72% 줄었고, 소비자물가 상승률은 1%대 초반에 머물러 디플레이션 우려가 완전히 가시지 않았습니다. 한국의 최대 교역 상대 중 하나인 중국의 내수가 살아나지 않으면 한국의 대중 수출과 원자재 시장에도 부담이 됩니다. 지도에서 글로벌 경기 → 수출 경로의 "글로벌" 쪽 절반이 바로 이 이야기입니다.',
        en: 'China grew 5.0% in Q1, beating the 4.8% consensus, but almost all of it came from exports while consumption and property stay weak. New housing starts are down about 72% from the 2021 peak, and CPI inflation lingers in the low 1% range, so deflation worries have not fully lifted. If domestic demand in Korea\'s biggest trading partner stays soft, Korean exports and commodity markets feel it. On the map, this is the global half of the global growth into exports chain.',
      },
      nodes: ['global_growth', 'exports', 'commodity'],
      edges: [['global_growth', 'exports'], ['global_growth', 'commodity'], ['exports', 'earnings']],
      relatedCase: null,
      relatedLoop: null,
      sources: [
        '중국 국가통계국 1분기 발표 (2026-04-16): GDP +5.0%, 소매판매 +1.7%',
        'Rhodium Group · 인민은행: 신규 착공 -72% (2021 고점 대비), 가계 주택대출 잔액 축소 지속',
        'Capital Economics (2026-04): PPI 상승 전환, CPI 1%대 초반',
      ],
    },
  ],
};
