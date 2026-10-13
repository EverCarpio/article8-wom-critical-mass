"""Publication-editable exploratory figures; requires matplotlib and numpy."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


def save(fig,root,name):
    for extension in ('png','svg','pdf'):
        fig.savefig(root/(name+'.'+extension),dpi=180,bbox_inches='tight')
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(); root=args.out.resolve(); root.mkdir(parents=True,exist_ok=True)
    data=json.loads((args.analysis/'analysis_summary.json').read_text())
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#243746',
        'text.color':'#243746','axes.edgecolor':'#afbac3','grid.color':'#dfe5e8','grid.alpha':.7,
        'svg.fonttype':'none','pdf.fonttype':42})
    blue='#176b91'; orange='#b86128'; green='#21806c'
    baseline=sorted([r for r in data['scenario_results'] if r['group']=='baseline'],key=lambda r:r['share'])
    x=np.array([r['share']*100 for r in baseline]); y=np.array([r['takeoff_rate'] for r in baseline])
    err=np.array([[r['takeoff_rate']-r['takeoff_wilson_low'] for r in baseline],
                  [r['takeoff_wilson_high']-r['takeoff_rate'] for r in baseline]])
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    axes[0].errorbar(x,y,yerr=err,color=blue,marker='o',capsize=3,lw=1.6)
    axes[0].set_ylim(-.04,1.13); axes[0].set_yticks([0,.25,.5,.75,1]); axes[0].yaxis.set_major_formatter(PercentFormatter(1))
    axes[0].set_title('Despegue observado'); axes[0].set_ylabel('Corridas con despegue · IC Wilson 95 %')
    for xx,r in zip(x,baseline): axes[0].text(xx,r['takeoff_rate']+.055,str(r['takeoffs'])+'/10',ha='center',fontsize=8)
    with (args.analysis/'run_summary.csv').open() as f: runs=list(csv.DictReader(f))
    for r in baseline:
        vals=[float(z['new_purchases']) for z in runs if z['scenario']==r['scenario']]
        jitter=np.linspace(-.32,.32,len(vals))
        axes[1].scatter(np.array([r['share']*100]*len(vals))+jitter,vals,s=16,color=orange,alpha=.55)
    axes[1].plot(x,[r['sales_mean'] for r in baseline],color=orange,marker='o',lw=1.6,label='Media; puntos = réplicas')
    axes[1].set_ylim(-15,495); axes[1].set_title('Compras nuevas al período 60'); axes[1].set_ylabel('Personas · mercado inicial de 480'); axes[1].legend(loc='lower right',frameon=False)
    for ax in axes:
        ax.set_xlabel('Promotores iniciales / 120 clientes (%)'); ax.set_xticks(x); ax.set_xticklabels([f'{v:g}' for v in x],fontsize=8); ax.grid(axis='y'); ax.set_axisbelow(True)
    fig.suptitle('Article 8 · Piloto base: 110 corridas, diez por condición',fontsize=14)
    save(fig,root,'Article_8_Piloto_F1_Barrido')

    labels=['E 0,3 − 0,6 · repartida','E 0,9 − 0,6 · repartida',
            'Concentrada − repartida · E 0,3','Concentrada − repartida · E 0,9',
            'E 0,9 − 0,3 · repartida','E 0,9 − 0,3 · concentrada']
    pairs=data['paired_results']; vals=np.array([r['mean_sales_difference'] for r in pairs])
    err=np.array([[r['mean_sales_difference']-r['sales_bootstrap_low'] for r in pairs],
                  [r['sales_bootstrap_high']-r['mean_sales_difference'] for r in pairs]])
    fig,ax=plt.subplots(figsize=(10,4.6),layout='constrained')
    ax.errorbar(vals,np.arange(len(pairs)),xerr=err,fmt='o',color=green,capsize=4)
    ax.axvline(0,color='#52636e',lw=1); ax.set_yticks(range(len(pairs)),labels); ax.invert_yaxis()
    ax.set_xlabel('Diferencia media de compras nuevas · IC bootstrap emparejado 95 %')
    ax.set_title('Contrastes al 15 % · Diez pares por comparación')
    ax.grid(axis='x'); ax.set_axisbelow(True)
    save(fig,root,'Article_8_Piloto_F2_Contrastes')

    with (args.analysis/'classification_sensitivity_summary.csv').open() as f: rows=list(csv.DictReader(f))
    settings=['base','duration4','duration8','growth1_10','growth1_50','without_pressure','limits05_15','limits15_30']
    names=['Base: 6 períodos; crecimiento 1,25','Duración: 4 períodos','Duración: 8 períodos',
           'Factor de crecimiento: 1,10','Factor de crecimiento: 1,50','Sin requisito de presión positiva',
           'Límites de mercado: 5 % / 15 %','Límites de mercado: 15 % / 30 %']
    matrix=np.array([[sum(int(r[k]) for r in rows if r['setting']==s) for k in ('takeoffs','collapses','saturations')] for s in settings])
    fig,ax=plt.subplots(figsize=(9.5,5.4),layout='constrained')
    im=ax.imshow(matrix,cmap='Blues',vmin=0,vmax=150,aspect='auto')
    ax.set_xticks(range(3),['Despegue','Colapso','Saturación']); ax.set_yticks(range(8),names)
    for i in range(8):
        for j in range(3): ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>80 else '#163849',fontsize=12)
    fig.colorbar(im,ax=ax,label='Corridas con el evento observado',shrink=.8)
    ax.set_title('Sensibilidad de clasificación sobre las mismas 150 trayectorias')
    ax.set_xlabel('Banderas históricas; pueden coexistir en una corrida')
    save(fig,root,'Article_8_Piloto_F3_Clasificacion')

    with (args.analysis/'system_period_compact.csv').open() as f: series=list(csv.DictReader(f))
    fig,axes=plt.subplots(1,2,figsize=(11.8,4.5),layout='constrained')
    for scenario,color,label in [('B01',blue,'2,5 %'),('B06',orange,'15 %'),('B10',green,'30 %')]:
        subset=[r for r in series if r['scenario']==scenario]
        for ax,key in zip(axes,['cumulative_new_purchases','promoter_active']):
            values=np.array([[float(next(r for r in subset if int(r['replicate'])==rep and float(r['time'])==t)[key])
                              for t in range(61)] for rep in range(1,11)])
            ax.fill_between(range(61),values.min(axis=0),values.max(axis=0),alpha=.12,color=color)
            ax.plot(range(61),values.mean(axis=0),color=color,label=label,lw=1.8)
    axes[0].set_title('Compras nuevas acumuladas'); axes[0].set_ylabel('Personas')
    axes[1].set_title('Promotores activos'); axes[1].set_ylabel('Personas al cierre')
    for ax in axes:
        ax.set_xlabel('Período simulado'); ax.grid(axis='y'); ax.set_axisbelow(True); ax.legend(frameon=False,title='Proporción inicial')
    fig.suptitle('Trayectorias base · Media y rango entre diez réplicas',fontsize=14)
    save(fig,root,'Article_8_Piloto_F4_Trayectorias')
    print('Four figures exported as PNG, SVG and PDF')


if __name__=='__main__': main()
