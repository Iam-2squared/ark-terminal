from datetime import date
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from io_utils import *

def main():
    r=read(OUT/'FINAL_COMPARISON.json');wins=r['windows'];x=[date.fromisoformat(w['start_session']) for w in wins]
    colors=['#2563eb','#ea580c'];plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,(ax,bottom)=plt.subplots(2,1,figsize=(12,7.5),sharex=True,gridspec_kw={'height_ratios':[2.3,1]})
    for field,label,col in zip(['V5_final_cash','V51_final_cash'],['V5 reset','V5.1 reset'],colors):
        values=[float(w[field]) if w[field] is not None else np.nan for w in wins];ax.plot(x,values,marker='o',label=label,color=col,linewidth=2,markersize=5)
    ax.axhline(2_000_000,color='#15803d',linestyle='--',label='JPY2m target');ax.set_ylim(950000,2100000);ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f'{v/1e6:.2f}m'));ax.set_ylabel('20-session endpoint cash (JPY)')
    ax.set_title('Literal JPY1m account resets | 9 of 21 planned windows measurable\nIterative Development; 12 windows retain unknown coverage')
    for axis in [ax,bottom]:
        axis.axvspan(x[0],x[11],color='#e5e7eb',alpha=.65);axis.grid(axis='y',alpha=.2)
    ax.text(x[5],1750000,'12 BLOCKED_COVERAGE windows\nNo endpoint inferred',ha='center',color='#4b5563');ax.legend(loc='upper left',frameon=False)
    delta=[float(w['delta_jpy']) if w['delta_jpy'] is not None else np.nan for w in wins];bottom.bar(x,delta,width=.75,color=['#15803d' if v>0 else '#b91c1c' for v in delta]);bottom.axhline(0,color='#6b7280',linewidth=.7);bottom.set_ylabel('V5.1 - V5 (JPY)');bottom.set_xlabel('Window start session');bottom.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO));bottom.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    bottom.text(.02,.07,'Median(final cash) difference: -JPY4,729.80\nMedian(paired differences): +JPY1,245.95',transform=bottom.transAxes,ha='left',va='bottom',fontsize=9)
    fig.tight_layout();fig.savefig(OUT/'wealth_reset20.png',dpi=160);plt.close(fig)
    aux=r['auxiliary_by_window'];bins=['LE0','GT0_LT5','GE5_LT10','GE10'];names=['<=0%','(0%,5%)','[5%,10%)','>=10%'];fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for policy,col,offset in [('V5',colors[0],-.18),('V51',colors[1],.18)]:
        for axis,field in zip(axes,['buy_debit_jpy','net_pnl_jpy']):
            values=[sum(float(w[policy]['net_bins'][b][field]) for w in aux)/len(aux) for b in bins];axis.bar(np.arange(4)+offset,values,width=.35,label=policy,color=col);axis.set_xticks(range(4),names);axis.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f'{v/1000:,.0f}k'));axis.axhline(0,color='#6b7280',linewidth=.7);axis.grid(axis='y',alpha=.2)
    axes[0].set_title('BUY debit / turnover by exact net-return bin');axes[1].set_title('Realized net PnL by exact net-return bin')
    for ax in axes:ax.set_ylabel('JPY per measured reset account (mean)');ax.legend(frameon=False)
    fig.suptitle('9 overlapping reset accounts | Mean account flows, not unique market opportunities',fontsize=11);fig.tight_layout();fig.savefig(OUT/'capital_net_bins.png',dpi=160);plt.close(fig)

if __name__=='__main__':main()
