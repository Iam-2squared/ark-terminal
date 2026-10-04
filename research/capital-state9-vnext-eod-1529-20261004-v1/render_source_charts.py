"""Aggregate actual source-admission counts; no prices, identities or Portfolio curves."""
import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

pub=Path(sys.argv[1]);data=json.loads((pub/'SESSION_COVERAGE_AGGREGATE.json').read_text());out=pub/'charts';out.mkdir(exist_ok=True)
x=[r['session_ordinal'] for r in data];old=[r['old39_unresolved_N'] for r in data];late=[r['EOD_needed_N']-r['old39_unresolved_N'] for r in data]
fig,ax=plt.subplots(figsize=(12,4.5));ax.bar(x,late,label='Frozen auction exit after deadline',color='#587ba3');ax.bar(x,old,bottom=late,label='Frozen unresolved (39)',color='#b54a48')
ax.set(xlabel='Session ordinal (dates and symbols withheld)',ylabel='Candidate count',title='15:29 EOD needed: 1,113 candidates / 58 sessions; admissible source = 0')
ax.set_xlim(0,59);ax.grid(axis='y',alpha=.25);ax.set_axisbelow(True);ax.legend(frameon=False,loc='upper left');fig.tight_layout()
fig.savefig(out/'eod_needed_by_session.svg',metadata={'Date':None});fig.savefig(out/'eod_needed_by_session.png',dpi=150);plt.close(fig)
print('Actual aggregate chart written; no Portfolio curve.')
