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
  '변수·사례·루프·지금 흐름 검색 (초성 가능)': 'Search variables, cases, loops, and storylines',
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
  '실제 사례': 'Real-world example',
  '강화 루프: 한 바퀴 돌 때마다 같은 방향으로 커집니다. 부호를 곱하면 (+)가 됩니다.':
    'Reinforcing loop: each turn pushes further in the same direction. Multiply the signs and you get (+).',
  '균형 루프: 한 바퀴 돌면 원래 방향을 되돌립니다. 부호를 곱하면 (−)가 됩니다.':
    'Balancing loop: each turn pushes back toward where it started. Multiply the signs and you get (−).',

  // legend
  '선과 연결': 'Lines & links',
  '노드와 압력': 'Nodes & pressure',
  '공간과 조작': 'Space & gestures',
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
  '읽는 법 요약': 'How to read the map',
  '선의 색 = 방향, 흐르는 점 = 인과의 흐름과 강도, 점선 = 확실성 낮음. 금색 선은 국면에 따라 방향이 뒤집힐 수 있는 관계입니다. 이 지도는 교과서 메커니즘의 단순화 모형이며 예측 도구가 아닙니다.':
    'Line color = direction, flowing dots = causal flow and strength, dashed = lower certainty. Gold lines are links whose sign can flip with the regime. This map simplifies textbook mechanisms and is not a forecasting tool.',
  '검색은 상단의 검색 버튼으로 열고, 경로 속 변수 이름을 클릭하면 그 변수로 바로 이동합니다.':
    'Open search with the search button at the top; click any variable name inside a path to jump straight to it.',
  '단축키: Ctrl+K 또는 / 검색, Esc 닫기·선택 해제, ← → 사례 단계 이동.':
    'Shortcuts: Ctrl+K or / to search, Esc to close or deselect, left/right arrows to step through a case.',
  '건너뛰기': 'Skip',
  '시작하기': 'Start exploring',
  '변수를 고르면 관련 역사 사례·피드백 루프가 그 자리에서 열리고, 시뮬레이터도 지도를 벗어나지 않고 열립니다.':
    'Pick a variable and its related cases and feedback loops open right there; the simulator opens without leaving the map.',
  '오늘의 경제 지표를 지도 위 색으로 비춥니다.': 'Projects today\'s indicators onto the map as color.',
  '지도를 아는 AI와 대화하면 답변의 근거 경로가 지도에 켜집니다.':
    'Chat with an AI that knows the map; the paths behind each answer light up.',
  '레버': 'Lever',
  '고리 달린 레버 노드를 위아래로 잡아끌면 즉석 충격을 줍니다.':
    'Grab a ringed lever node and drag it up or down for an instant shock.',
  '처음이시면 오른쪽 위 ? 버튼에서 읽는 법을 볼 수 있습니다.':
    'First time here? The ? button (top right) shows how to read the map.',

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
  // asOf chip: EN reads "data as of DATE · analysis as of DATE" (기준 folds into the labels)
  '기준': '',
  '수치': 'data as of',
  '해설': 'analysis as of',
  '지도에 비추기': 'Project onto the map',
  '지도 비추기 끄기': 'Turn off projection',
  '흐름 해설이': 'The storyline analysis is about',
  '개월 전 것입니다. 그 사이의 사건은 반영되지 않았을 수 있습니다.': ' months old. Events since then may not be reflected.',
  '지표 수치의 자동 갱신이': 'Automatic indicator updates have been stalled for about',
  '개월째 멈춰 있습니다. 각 출처에서 직접 확인하세요.': ' months. Check each source directly.',
  '주요 지표': 'Key indicators',
  '지금 주요 흐름': 'Current storylines',
  '지금 목록': 'Back to Now',
  '닮은꼴 사례': 'Rhyming case',
  '관련 루프': 'Related loop',
  '상승': 'rising',
  '하락': 'falling',
  '보합': 'flat',
  '지표 수치는 공식 통계에서 자동 갱신되고, 흐름 해설은 주간 검증 파이프라인이 갱신합니다. 각 항목에 출처와 기준일을 표기했습니다.':
    'Indicator values refresh automatically from official statistics; the storylines are refreshed by a weekly verification pipeline. Every item carries its source and data date.',

  // v2: regime flips, cross-links, instrument strip
  '국면 반전': 'Regime flip',
  '지금 탭에서 전체 상황 보기': 'See the full board in the Now tab',
  '금색 강조 = 국면 따라 방향 반전 가능': 'Gold = sign can flip with the regime',
  '레버 노드 위아래 드래그 = 즉석 충격': 'Drag a lever node up/down = instant shock',

  // v2.1: exploration-centric hub
  '시뮬레이터 열기': 'Open the simulator',
  '금리·유가·환율 레버를 움직여 파급을 실험합니다. 지도에서 고리 달린 레버 노드를 위아래로 잡아끌어도 됩니다.':
    'Move the rate, oil, and FX levers to experiment with ripples. You can also grab a ringed lever node on the map and drag it up or down.',
  '한 곳에서: 탐색 · 지금 · AI': 'One place: Explore · Now · AI',
  '섹션 이동': 'Sections',
  '지도에서 이 노드를 위아래로 잡아끌면 즉석 충격을 줄 수 있습니다.':
    'Drag this node up or down on the map for an instant shock.',
  '경로 상세': 'path details',
  '링크가 가리키던 항목을 찾을 수 없어 처음 화면을 보여드립니다.':
    'The item this link pointed to no longer exists, so here is the start screen.',

  // v2: AI chat
  '지도와 대화하기': 'Talk to the map',
  '이 지도에 담긴 변수·인과·역사 사례·현재 상황을 아는 AI에게 투자 환경, 비즈니스, 사회 현상 질문을 던져 보세요. 답변과 동시에 관련 인과 경로가 지도에 켜집니다.':
    'Ask an AI that knows this map\'s variables, causal links, historical cases, and current conditions about investing environments, business, or social questions. As it answers, the relevant causal paths light up on the map.',
  'AI 제공자': 'AI provider',
  '서비스': 'Service',
  'AI 제공자와 API 키': 'AI provider & API key',
  '서버가 없는 앱이라 본인의 API 키로 브라우저에서 제공자에 직접 요청합니다. 키는 이 브라우저에만 저장되고 해당 제공자 외 어디로도 전송되지 않으며, 사용량은 본인 계정에 과금됩니다.':
    'This app has no server: your browser calls the provider directly with your own API key. The key is stored only in this browser, sent nowhere but that provider, and usage is billed to your account.',
  '모델 ID': 'Model ID',
  '키 형식이 올바르지 않습니다': 'That key format looks wrong',
  '모델 이름을 찾을 수 없습니다. 모델 ID를 확인해 주세요.': 'Model not found. Check the model ID.',
  '참고: OpenAI 본체 API는 브라우저 직접 호출을 막아(CORS) 이 앱에서 직접 쓸 수 없습니다. GPT는 OpenRouter로 이용하세요.':
    'Note: OpenAI\'s own API blocks direct browser calls (CORS), so it can\'t be used directly here. Use GPT models via OpenRouter.',
  '저장하고 시작': 'Save & start',
  '키 발급': 'Get a key',
  'API 키를 입력해 주세요': 'Enter your API key first',
  'AI 대화가 준비되었습니다': 'AI chat is ready',
  '모델': 'Model',
  '대화 지우기': 'Clear chat',
  '키 삭제': 'Remove key',
  '무엇이든 물어보세요. 답변의 근거가 되는 인과 경로가 지도에 함께 켜지고, 관련 역사 사례로 바로 건너갈 수 있습니다.':
    'Ask anything. The causal paths behind each answer light up on the map, and you can jump straight to related historical cases.',
  '금리가 오르면 왜 주가가 떨어지나요? 반대로 호재가 되는 경우도 있나요?':
    'Why do stocks fall when rates rise? Are there regimes where it\'s good news instead?',
  '원화 약세가 수입 원자재를 쓰는 사업에 미치는 영향을 경로로 보여주세요.':
    'Show me, as a causal path, how a weak won hits a business that imports raw materials.',
  '지금의 AI 반도체 붐은 2000년 닷컴 버블과 무엇이 같고 무엇이 다른가요?':
    'How does today\'s AI chip boom compare with the 2000 dot-com bubble?',
  '예: 지금 금리가 내리면 부동산은 어떻게 되나요?': 'e.g. If rates fall now, what happens to housing?',
  '질문 입력': 'Type a question',
  '중지': 'Stop',
  '보내기': 'Send',
  '생성 중…': 'Generating…',
  '교육 목적 도구입니다. 투자 조언이 아니며, 답변은 부정확할 수 있습니다.':
    'An educational tool. Not investment advice; answers may be inaccurate.',
  '지도에 다시 표시': 'Show on map again',
  '관련 경로를 지도에 표시했습니다': 'Highlighted the relevant paths on the map',
  '답변 도착': 'Answer ready',
  '다시 시도': 'Retry',
  '한 번 더 누르면 실행': 'Tap again to confirm',
  'API 키가 올바르지 않습니다. 키를 확인해 주세요.': 'Invalid API key. Please check it.',
  '요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.': 'Too many requests. Try again shortly.',
  '네트워크에 연결할 수 없습니다. 인터넷 연결을 확인해 주세요.': 'Cannot reach the network. Check your internet connection.',
  '요청이 실패했습니다': 'Request failed',
  '안전상 이 질문에는 답변이 제한되었습니다.': 'This question was declined for safety reasons.',
  '중단됨': 'stopped',

  // toasts + fallbacks
  '모션을 줄였습니다': 'Motion reduced',
  '모션을 켰습니다': 'Motion on',
  '이 기기에서는 3D를 사용할 수 없어 목록 모드로 표시합니다. 모든 설명은 아래 패널에서 그대로 볼 수 있습니다.':
    'This device cannot run 3D, so the map is shown in list mode. Every explanation is still available in the panel below.',
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
