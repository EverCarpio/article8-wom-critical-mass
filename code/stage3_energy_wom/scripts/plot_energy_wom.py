"""Scientific figures exported in PNG, SVG and PDF; all 18 cells retained."""
import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


def read(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


def save(fig,out,name):
    for ext in ('png','svg','pdf'):fig.savefig(out/f'{name}.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)


def plot(source,out):
    out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    rows=read(source/'cell_summary.csv');by={(int(r['count']),float(r['positive_energy']),float(r['negative_weight'])):r for r in rows}
    energy=(.3,.6,.9);weights=(0.,1.,2.)
    fig,axes=plt.subplots(1,2,figsize=(12,5.3),layout='constrained')
    for p,ax in zip((1,2),axes):
        data=np.array([[100*float(by[p,e,w]['sustained_v02_rate']) for w in weights] for e in energy])
        im=ax.imshow(data,vmin=0,vmax=100,cmap='YlGnBu',aspect='auto')
        for i,e in enumerate(energy):
            for j,w in enumerate(weights):
                r=by[p,e,w];v=data[i,j];lo=100*float(r['sustained_v02_low']);hi=100*float(r['sustained_v02_high'])
                ax.text(j,i,f'{v:.0f} %\n[{lo:.1f}, {hi:.1f}]',ha='center',va='center',fontsize=13,color='white' if v>=65 else '#102b45')
        ax.set(xticks=range(3),xticklabels=['0 · neutralizado','1 · referencia','2 · doble peso'],yticks=range(3),yticklabels=['0,3','0,6','0,9'],
            xlabel='Peso del WOM negativo (λ)',ylabel='Energía de promotores iniciales',title=f'{p} promotor'+('es' if p==2 else '')+' inicial'+('es' if p==2 else ''))
    fig.colorbar(im,ax=axes,label='Difusión sostenida (%)',shrink=.82)
    fig.suptitle('Energía inicial y WOM negativo: probabilidad de difusión sostenida',fontsize=16)
    fig.supxlabel('100 réplicas por celda · 120 períodos · IC Wilson 95 % entre corchetes · Criterio v0.2',fontsize=10)
    save(fig,out,'Article_8_Energia_WOM_F1_Despegue')
    fig,axes=plt.subplots(1,3,figsize=(12,4.7),sharey=True,layout='constrained')
    colors={1:'#be5d22',2:'#176a92'}
    for w,ax in zip(weights,axes):
        for p in (1,2):
            cell=[by[p,e,w] for e in energy]
            means=[float(r['sales_mean']) for r in cell];med=[float(r['sales_median']) for r in cell]
            ax.plot(energy,means,marker='o',color=colors[p],label=f'{p} promotor'+('es' if p==2 else ''))
            ax.plot(energy,med,marker='x',linestyle='--',alpha=.7,color=colors[p])
        ax.set(xlabel='Energía inicial',title=f'Peso negativo λ = {int(w)}',xticks=energy,xticklabels=['0,3','0,6','0,9'],ylim=(0,480))
        ax.grid(axis='y',alpha=.18)
    axes[0].set_ylabel('Compras nuevas al período 120');axes[-1].legend(loc='lower right')
    fig.suptitle('Volumen de difusión: media y mediana de compras',fontsize=16)
    fig.supxlabel('Línea continua: media · Línea discontinua: mediana · Mercado susceptible inicial: 480 personas',fontsize=10)
    save(fig,out,'Article_8_Energia_WOM_F2_Compras')
    effects=[r for r in read(source/'paired_summary.csv') if r['kind']=='promoters']
    fig,axes=plt.subplots(1,2,figsize=(12,5.8),layout='constrained')
    labels=[f'E={str(e).replace(".",",")} · λ={int(w)}' for e in energy for w in weights]
    for ax,metric,title,scale in zip(axes,('sustained_v02','new_purchases'),('Difusión sostenida (puntos porcentuales)','Compras nuevas al período 120'),(100,1)):
        group=[r for r in effects if r['metric']==metric]
        for i,r in enumerate(group):
            mean=float(r['mean'])*scale;lo=float(r['low'])*scale;hi=float(r['high'])*scale
            ax.errorbar(mean,i,xerr=[[mean-lo],[hi-mean]],fmt='o',color='#176a92',capsize=3)
        ax.axvline(0,color='#666',lw=.8);ax.set(yticks=range(9),yticklabels=labels,xlabel=title);ax.invert_yaxis();ax.grid(axis='x',alpha=.18)
    fig.suptitle('Efecto de pasar de uno a dos promotores',fontsize=16)
    fig.supxlabel('Diferencias dentro de cada semilla · IC bootstrap 95 % · 20.000 remuestras de 100 parejas',fontsize=10)
    save(fig,out,'Article_8_Energia_WOM_F3_Efecto_Segundo_Promotor')
    incidence=read(source/'incidence.csv')
    fig,axes=plt.subplots(2,3,figsize=(12,7),sharex=True,sharey=True,layout='constrained')
    ecolors={.3:'#c56937',.6:'#19847c',.9:'#4256a7'}
    for i,p in enumerate((1,2)):
        for j,w in enumerate(weights):
            ax=axes[i,j]
            for e in energy:
                block=[r for r in incidence if int(r['count'])==p and float(r['positive_energy'])==e and float(r['negative_weight'])==w and r['event']=='sustained_confirmation']
                ax.step([int(r['time']) for r in block],[float(r['rate']) for r in block],where='post',color=ecolors[e],label=f'E={str(e).replace(".",",")}')
            ax.set(title=f'P0={p} · λ={int(w)}',xlim=(0,120),ylim=(0,1.02));ax.yaxis.set_major_formatter(PercentFormatter(1));ax.grid(alpha=.18)
    axes[0,0].legend(loc='lower right');fig.supylabel('Réplicas con difusión sostenida confirmada');fig.supxlabel('Período · Denominador constante de 100; sin eliminar casos sin evento')
    fig.suptitle('Cuándo se confirma la difusión sostenida',fontsize=16)
    save(fig,out,'Article_8_Energia_WOM_F4_Incidencia')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();plot(a.source,a.out)
