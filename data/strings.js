// UI string dictionary (EN) for the i18n kit. Keys are the Korean source strings.
// Node/edge/case/loop content is bilingual in its own data files; this covers chrome copy.

export const UI_DICT_EN = {
  // shell
  '본문(설명 패널)으로 건너뛰기': 'Skip to the explanation panel',
  '경제 인과관계 지도 · 시스템 사고 훈련장': 'Causal map of the economy · a systems-thinking gym',
  '탐색': 'Explore',
  '지금': 'Now',
  '시뮬레이터': 'Simulator',
  '역사 사례': 'Cases',
  '루프': 'Loops',
  '모션 줄이기': 'Reduce motion',
  '도움말': 'Help',
  '검색': 'Search',
  '검색 (Ctrl+K)': 'Search (Ctrl+K)',
  '검색어': 'Search query',
  '검색 결과': 'Search results',
  '변수·사례·루프 검색 (초성 가능)': 'Search variables, cases, and loops',
  '↑↓ 이동 · Enter 선택 · Esc 닫기': '↑↓ move · Enter select · Esc close',
  '결과가 없습니다. 다른 검색어를 시도해 보세요.': 'No results. Try a different query.',
  '이 변수로 이동': 'Jump to this variable',
  '처음 화면': 'Reset view',
  '접기': 'Collapse',
  '펼치기': 'Expand',
  '범례': 'Legend',
  '출처와 한계': 'Sources & limits',
  '인과 지도를 그리는 중…': 'Drawing the causal map…',
  '문제가 발생했습니다': 'Something went wrong',
  '화면을 그리는 중 오류가 났습니다. 새로고침하면 대부분 해결됩니다.': 'A rendering error occurred. A refresh usually fixes it.',
  '새로고침': 'Reload',
  'MacroScope 홈': 'MacroScope home',
  '모드': 'Modes',
  '설명 패널': 'Explanation panel',

  // shared badges
  '같은 방향': 'same direction',
  '반대 방향': 'opposite direction',
  '영향 강도': 'strength',
  '확실성': 'certainty',
  '시뮬레이터 레버': 'Simulator lever',

  // explore
  '변수를 선택하세요': 'Pick a variable',
  '지도의 점 하나가 변수 하나입니다. 변수를 클릭하면 그 변화가 어디로 번져가는지 1차 → 2차 → 3차 파급 경로가 켜집니다.':
    'Each dot is a variable. Click one and the map lights up where a change spreads: 1st, 2nd, then 3rd-order ripples.',
  '추천 시작점': 'Good starting points',
  '드래그로 회전, 휠이나 두 손가락으로 확대·축소할 수 있습니다.': 'Drag to rotate; scroll or pinch to zoom.',
  '변수 분류': 'Variable categories',
  '탐색 방향': 'Direction',
  '영향 보기': 'Effects',
  '원인 보기': 'Drivers',
  '가정': 'Assumption',
  '올랐을 때': 'If it rises',
  '내렸을 때': 'If it falls',
  '파급 깊이': 'Ripple depth',
  '1차까지': 'Depth 1',
  '2차까지': 'Depth 2',
  '3차까지': 'Depth 3',
  '1차': '1st order',
  '2차': '2nd order',
  '3차': '3rd order',
  '1차 · 직접 효과': '1st order · direct effects',
  '2차 · 한 다리 건너': '2nd order · one step removed',
  '3차 · 두 다리 건너': '3rd order · two steps removed',
  '1차 · 직접 원인': '1st order · direct drivers',
  '2차 · 상류 원인': '2nd order · upstream drivers',
  '3차 · 더 먼 원인': '3rd order · further upstream',
  '이 방향으로 연결된 경로가 없습니다.': 'No connected paths in this direction.',

  // simulator
  '시나리오 시뮬레이터': 'Scenario simulator',
  '레버를 움직이면 충격이 연쇄 경로를 타고 번지는 모습을 봅니다. 숫자는 예측이 아니라 방향과 상대적 세기입니다.':
    'Move a lever and watch the shock travel through the chains. Numbers show direction and relative size, not forecasts.',
  '프리셋 적용': 'preset applied',
  '초기화': 'Reset',
  '아직 충격이 없습니다. 레버를 움직이거나 프리셋을 눌러 보세요.': 'No shock yet. Move a lever or tap a preset.',
  '예상 파급 (세기 순)': 'Expected ripple (largest first)',
  '충격이 너무 약해 뚜렷한 파급이 없습니다.': 'The shock is too small to produce a visible ripple.',
  '경로 상충': 'conflicting paths',
  '올리는 경로와 내리는 경로가 동시에 작동합니다. 순효과는 조건에 따라 달라질 수 있습니다.':
    'Paths pushing up and paths pushing down are both active. The net effect depends on conditions.',
  '이 모형은 교과서 메커니즘을 단순화한 것입니다. 실제 경제는 초기 조건과 정책 대응에 따라 다르게 움직입니다.':
    'This model simplifies textbook mechanisms. The real economy responds differently depending on initial conditions and policy.',

  // cases
  '역사 사례 재생': 'Case replay',
  '과거의 큰 사건을 원인 → 확산 → 정책 대응 → 시장 심리 → 결과의 5단계로 지도 위에 재생합니다.':
    'Replay major historical episodes on the map in five acts: cause → spread → policy → psychology → outcome.',
  '사례 목록': 'All cases',
  '단계': 'Steps',
  '이전': 'Back',
  '다음': 'Next',
  '일시정지': 'Pause',
  '자동 재생': 'Auto play',
  '지금과 비교하면?': 'Compared with today?',
  '공통점': 'In common',
  '다른 점': 'What differs',
  '출처': 'Sources',

  // loops
  '피드백 루프': 'Feedback loops',
  '시스템 사고의 핵심은 한 방향 화살표가 아니라 되먹임 고리입니다. 강화 루프는 눈덩이처럼 스스로 커지고, 균형 루프는 온도조절기처럼 되돌립니다.':
    'Systems thinking is about feedback, not one-way arrows. Reinforcing loops snowball; balancing loops pull things back like a thermostat.',
  '강화 루프': 'Reinforcing',
  '균형 루프': 'Balancing',
  '루프 목록': 'All loops',
  '실제 사례': 'Real-world example',
  '강화 루프: 한 바퀴 돌 때마다 같은 방향으로 커집니다. 부호를 곱하면 (+)가 됩니다.':
    'Reinforcing loop: each turn pushes further in the same direction. Multiply the signs and you get (+).',
  '균형 루프: 한 바퀴 돌면 원래 방향을 되돌립니다. 부호를 곱하면 (−)가 됩니다.':
    'Balancing loop: each turn pushes back toward where it started. Multiply the signs and you get (−).',

  // legend
  '높이 = 심리·기대(위) ↔ 실물·원자재(아래)': 'Height = sentiment & expectations (top) ↔ real economy & commodities (bottom)',
  '중심에서 멀수록 해외·글로벌 변수': 'Farther from center = more global',
  '같은 방향으로 민다 (+)': 'Pushes the same way (+)',
  '반대 방향으로 민다 (−)': 'Pushes the opposite way (−)',
  '점선 = 확실성 낮음': 'Dashed = lower certainty',
  '흐르는 점 = 인과 방향, 점 개수 = 강도': 'Flowing dots = direction; dot count = strength',
  '고리 달린 노드 = 시뮬레이터 레버': 'Ringed node = simulator lever',
  '상승 압력': 'Upward pressure',
  '하락 압력': 'Downward pressure',

  // onboarding
  '연결로 경제 읽기': 'Read the economy as connections',
  '점 하나가 변수(금리, 물가, 환율…)이고, 선은 인과관계입니다. 청록 선은 같은 방향, 주황 선은 반대 방향으로 밉니다. 위치에도 의미가 있습니다. 위층일수록 사람들의 마음(심리·기대)과 정책, 아래층일수록 실물과 원자재이고, 중심에서 멀수록 해외 변수입니다.':
    'Each dot is a variable (rates, prices, FX…) and each line a causal link. Cyan pushes the same way; orange pushes the opposite way. Position carries meaning too: upper layers hold minds (sentiment, expectations) and policy, lower layers the real economy and raw materials, and the farther from center, the more global the variable.',
  '2차·3차 파급을 따라가기': 'Follow 2nd and 3rd-order ripples',
  '변수를 클릭하면 직접 효과(1차)만이 아니라 한 다리, 두 다리 건너의 파급(2차·3차)까지 경로가 차례로 켜집니다. 화살표 방향과 시차, 확실성을 함께 확인하세요.':
    'Click a variable and the map lights up not just direct effects but ripples one and two steps removed. Check direction, time lag, and certainty as you go.',
  '시뮬레이터 · 사례 · 루프': 'Now · Simulator · Cases · Loops',
  '지금 탭은 오늘의 경제 상황(출처·기준일 포함)을 지도 위에 색으로 비춥니다. 시뮬레이터에서 금리·유가·환율 레버를 움직이면 파급 경로가 실시간으로 바뀌고, 역사 사례 탭은 1970년대 인플레이션, 1997 외환위기, 2008 금융위기를 5단계로 재생하며, 루프 탭은 되먹임 고리를 보여줍니다.':
    'The Now tab projects today\'s economic conditions (with sources and dates) onto the map. In the simulator, move the rate, oil, and FX levers and watch the ripple change live. The Cases tab replays the 1970s inflation, the 1997 crisis, and 2008 in five acts; the Loops tab shows feedback cycles.',
  '읽는 법 요약': 'How to read the map',
  '선의 색 = 방향, 흐르는 점 = 인과의 흐름과 강도, 점선 = 확실성 낮음. 이 지도는 교과서 메커니즘의 단순화 모형이며 예측 도구가 아닙니다. 단축키: Ctrl+K 또는 / 검색, Esc 닫기·선택 해제, ← → 사례 단계 이동. 경로 속 변수 이름을 클릭하면 그 변수로 바로 이동합니다.':
    'Line color = direction, flowing dots = causal flow and strength, dashed = lower certainty. This map simplifies textbook mechanisms and is not a forecasting tool. Shortcuts: Ctrl+K or / to search, Esc to close or deselect, left/right arrows to step through a case. Click any variable name inside a path to jump straight to it.',
  '시작하기': 'Start exploring',

  // sources dialog
  '메커니즘 출처': 'Mechanism sources',
  '한국은행, 통화정책 파급경로 (금리·자산가격·환율·기대 경로)': 'Bank of Korea, Monetary policy transmission channels (rates, asset prices, FX, expectations)',
  'IMF·BIS 공개 보고서 (자본이동, 신용 사이클)': 'IMF and BIS public reports (capital flows, credit cycles)',
  '역사 사례 출처': 'Case sources',
  '이 지도의 한계': 'Limits of this map',
  '교과서 메커니즘의 단순화 모형입니다. 강도·시차·확실성은 정성적 구간이지 측정치가 아닙니다.':
    'A simplified model of textbook mechanisms. Strength, lag, and certainty are qualitative bands, not measurements.',
  '실제 경제는 초기 조건, 기대, 정책 대응에 따라 같은 충격에도 다르게 반응합니다.':
    'The real economy responds differently to the same shock depending on initial conditions, expectations, and policy.',
  '예측이나 투자 판단의 근거가 아니라, 연결을 보는 훈련 도구입니다.':
    'A training tool for seeing connections, not a basis for forecasts or investment decisions.',
  '닫기': 'Close',

  // NOW situation board
  '지금의 경제, 한눈에': 'The economy right now, at a glance',
  '아래 지표의 최근 방향(약 6개월)을 지도 위 색으로 비춥니다. 예측이 아니라, 오늘의 배치도입니다.':
    'The recent direction (about 6 months) of each indicator is projected onto the map as color. Not a forecast: a layout of today.',
  '기준': 'as of',
  '지도에 비추기': 'Project onto the map',
  '지도 비추기 끄기': 'Turn off projection',
  '이 상황판은': 'This board is a snapshot from about',
  '개월 전 스냅샷입니다. 최신 수치는 각 출처에서 확인하세요.': ' months ago. Check each source for the latest numbers.',
  '주요 지표': 'Key indicators',
  '지금 주요 흐름': 'Current storylines',
  '지금 목록': 'Back to Now',
  '닮은꼴 사례': 'Rhyming case',
  '관련 루프': 'Related loop',
  '상승': 'rising',
  '하락': 'falling',
  '보합': 'flat',
  '이 상황판은 자동 갱신되지 않는 수동 스냅샷입니다. 각 항목의 출처와 기준일을 함께 표기했습니다.':
    'This board is a manually updated snapshot, not a live feed. Every item carries its source and data date.',

  // toasts + fallbacks
  '모션을 줄였습니다': 'Motion reduced',
  '모션을 켰습니다': 'Motion on',
  '이 기기에서는 3D를 사용할 수 없어 목록 모드로 표시합니다. 모든 설명은 아래 패널에서 그대로 볼 수 있습니다.':
    'This device cannot run 3D, so the map is shown in list mode. Every explanation is still available in the panel below.',
  '정부가 지출을 늘리거나 줄입니다': 'The government expands or cuts spending',
  '전쟁·분쟁 등 지정학 긴장이 높아지거나 낮아집니다': 'Geopolitical tension rises or eases',
};

export const UI_META = {
  ko: {
    title: '매크로스코프 · 경제 인과관계 3D 지도',
    description: '금리·물가·환율 등 30개 거시 변수의 연결과 2차·3차 파급효과를 탐색하며 시스템 사고를 훈련하는 인터랙티브 3D 인과관계 지도.',
    ogLocale: 'ko_KR',
    ogTitle: '매크로스코프 MacroScope',
  },
  en: {
    title: 'MacroScope: a 3D Causal Map of the Economy',
    description: 'An interactive 3D causal map of the economy: explore how 30 macro variables connect, trace 2nd and 3rd-order ripple effects, and train systems thinking.',
    ogLocale: 'en_US',
    ogTitle: 'MacroScope: Causal Map of the Economy',
  },
};
