import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { UI_DICT_EN } from '../../data/strings.js';

const uiModule = await import('../../js/ui.js');
const uiSource = readFileSync(new URL('../../js/ui.js', import.meta.url), 'utf8');
const mainSource = readFileSync(new URL('../../js/main.js', import.meta.url), 'utf8');
const cssSource = readFileSync(new URL('../../css/main.css', import.meta.url), 'utf8');

test('hub presentation maps score, band, and fallback status without DOM dependencies', () => {
  assert.equal(typeof uiModule.hubMetricPresentation, 'function');
  assert.deepEqual(
    uiModule.hubMetricPresentation({ hubScore: 0.2, score100: 20, band: 'low' }, 'fallback'),
    { score100: 20, band: 'low', bandKey: '낮음', showFallback: true },
  );
  assert.deepEqual(
    uiModule.hubMetricPresentation({ hubScore: 0.5, score100: 50, band: 'medium' }, 'ready'),
    { score100: 50, band: 'medium', bandKey: '중간', showFallback: false },
  );
  assert.deepEqual(
    uiModule.hubMetricPresentation({ hubScore: 0.9, score100: 90, band: 'high' }, null),
    { score100: 90, band: 'high', bandKey: '높음', showFallback: false },
  );
});

test('legend samples use the exact 0, 50, and 100 hub radius scales', () => {
  assert.equal(typeof uiModule.hubLegendSamples, 'function');
  assert.deepEqual(uiModule.hubLegendSamples(), [
    { score100: 0, radiusScale: 0.82 },
    { score100: 50, radiusScale: 1.074895 },
    { score100: 100, radiusScale: 1.28 },
  ]);
});

test('required hub and fallback copy is bilingual', () => {
  assert.deepEqual(
    Object.fromEntries([
      '인과 허브',
      '낮음',
      '중간',
      '높음',
      '강한 직·간접 경로, 최대 3단계',
      '모델을 불러오지 못해 기본 형상으로 표시합니다',
    ].map((key) => [key, UI_DICT_EN[key]])),
    {
      '인과 허브': 'Causal hub',
      '낮음': 'Low',
      '중간': 'Medium',
      '높음': 'High',
      '강한 직·간접 경로, 최대 3단계': 'Strong direct and indirect paths, up to 3 steps',
      '모델을 불러오지 못해 기본 형상으로 표시합니다': 'The default shape is shown because the model could not be loaded',
    },
  );
});

test('panel, legend, and settled model callback integrate the hub presentation contract', () => {
  assert.match(uiSource, /const\s*{\s*graph,\s*hubMetrics,\s*scene,/);
  assert.match(uiSource, /scene\?\.getNodeModelStatus\?\.\(\s*n\.id\s*\)/);
  assert.match(uiSource, /class:\s*['"]hub-summary['"]/);
  assert.match(uiSource, /class:\s*['"]hub-score['"]/);
  assert.match(uiSource, /class:\s*['"]model-fallback-note['"]/);
  assert.match(uiSource, /class:\s*['"]hub-legend-samples['"]/);
  assert.match(uiSource, /['"]data-score['"]:\s*String\(sample\.score100\)/);
  assert.match(uiSource, /t\(\s*['"]강한 직·간접 경로, 최대 3단계['"]\s*\)/);
  assert.doesNotMatch(uiSource, /setNodeTints/);
  assert.match(mainSource, /onModelStatusChange:\s*\(\)\s*=>\s*uiRef\?\.onModelStatusChange\?\.\(\)/);
  assert.match(
    uiSource,
    /function\s+setPanelCollapsed\s*\(\s*collapsed\s*\)\s*{\s*if\s*\(\s*isMobile\(\)\s*&&\s*!collapsed\s*\)\s*els\.legend\.removeAttribute\(\s*['"]open['"]\s*\)/,
    'expanding the mobile panel must close the overlapping legend',
  );
});

test('hub UI CSS preserves contrast and fits the existing 390px legend', () => {
  for (const selector of [
    '.hub-summary', '.hub-score', '.hub-band', '.model-fallback-note',
    '.hub-legend-samples', '.hub-legend-sample', '.hub-legend-dot', '.hub-legend-help',
  ]) {
    assert.match(cssSource, new RegExp(`\\${selector}\\s*\\{`), `missing ${selector}`);
  }
  assert.match(cssSource, /\.hub-legend-dot\s*{[^}]*width:\s*calc\(22px\s*\*\s*var\(--hub-scale\)\)/s);
  assert.match(cssSource, /@media\s*\(max-width:\s*900px\)[\s\S]*?\.hub-summary\s*{[^}]*width:\s*100%/);
  assert.match(cssSource, /#legend\s*{[^}]*width:\s*220px/s);
  assert.match(cssSource, /\.hub-score\s*{[^}]*color:\s*var\(--ink\)/s);
  assert.match(cssSource, /\.hub-legend-help\s*{[^}]*color:\s*var\(--ink-2\)/s);
});
