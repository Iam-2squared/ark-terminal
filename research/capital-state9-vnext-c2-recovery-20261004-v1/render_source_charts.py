"""Anonymized, measured source coverage only; no Portfolio curve."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/evidence/phase57-capital-state9-vnext-c2-recovery-20261004-v1'
rows = json.loads((OUT / 'ANONYMIZED_SESSION_SOURCE_COUNTS.json').read_text())['rows']
assert len(rows) == 58 and sum(r.get('unresolved', 0) for r in rows) == 39
assert sum(r['incomplete_1m_candidates'] for r in rows) == 1420
path = OUT / 'charts'
path.mkdir(exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'svg.hashsalt': 'ark-c2-source-recovery-v1'})
fig, axes = plt.subplots(2, 1, figsize=(11, 5.4), sharex=True, layout='constrained', gridspec_kw={'height_ratios': [1, 1.1]})
x = [r['session_index'] for r in rows]
axes[0].bar(x, [r.get('unresolved', 0) for r in rows], color='#bf6249', width=.72)
axes[0].set_title('39 unresolved EXITs across 29 of 58 sessions', loc='left', weight='bold')
axes[0].set_ylabel('Candidates')
axes[0].yaxis.set_major_locator(MaxNLocator(integer=True))
axes[0].grid(axis='y', alpha=.16)
rate = [100 * (r['candidates'] - r['incomplete_1m_candidates']) / r['candidates'] for r in rows]
axes[1].plot(x, rate, color='#386b95', marker='o', markersize=3, linewidth=1.3)
axes[1].set_title('Complete candidate regular1m windows: 180 / 1,600 (11.25%)', loc='left', weight='bold')
axes[1].set_ylim(0, 100)
axes[1].set_ylabel('Candidates (%)')
axes[1].set_xlabel('Chronological session index; dates and symbols withheld')
axes[1].set_xticks([1, 10, 20, 30, 40, 50, 58], ['S01', 'S10', 'S20', 'S30', 'S40', 'S50', 'S58'])
axes[1].grid(axis='y', alpha=.16)
fig.suptitle('Frozen Development source diagnostics — no allocation or performance replay', fontsize=11)
fig.savefig(path / 'source_coverage_by_session.png', dpi=120, metadata={'Software': 'Ark C2 source audit'})
fig.savefig(path / 'source_coverage_by_session.svg', metadata={'Date': None})
plt.close(fig)
print(json.dumps({'chart':'source_coverage_by_session','sessions_N':58,'unresolved_N':39,'complete1m_candidates_N':180,'Portfolio_curve':False}))
