"""Export scientific figures as PNG, SVG and PDF."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS=['#687783','#197C87','#B2662E','#6848A1']


def read(path):
    with path.open() as f:return list(csv.DictReader(f))


def save(fig,out,name):
    for suffix in ('png','svg','pdf'):fig.savefig(out/(name+'.'+suffix),dpi=200,bbox_inches='tight',facecolor='white')
    plt.close(fig)


def main(source,out):
    out.mkdir(parents=True,exist_ok=True)
    summary=json.loads((source/'analysis_summary.json').read_text());scenarios=summary['scenarios']
    records=read(source/'run_summary.csv')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
        'axes.titleweight':'bold','svg.fonttype':'none','font.family':'DejaVu Sans'})
    fig,axs=plt.subplots(1,2,figsize=(11.8,4.4),layout='constrained')
    x=np.arange(4)
    for offset,field,label,color in [(-.055,'sustained_v02','Difusión sostenida v0.2','#197C87'),(.055,'m6_takeoff','Despegue M6','#B2662E')]:
        y=np.array([r[field+'_rate'] for r in scenarios]);lo=np.array([r[field+'_low'] for r in scenarios]);hi=np.array([r[field+'_high'] for r in scenarios])
        axs[0].errorbar(x+offset,y,yerr=[np.maximum(0,y-lo),np.maximum(0,hi-y)],marker='o',capsize=4,color=color,label=label)
    axs[0].set(title='Frecuencia de despegue observado',ylabel='Proporción de 100 réplicas',ylim=(-.04,1.09),yticks=np.arange(0,1.01,.2))
    axs[0].legend(loc='best',fontsize=9)
    rng=np.random.default_rng(90001)
    for n in range(4):
        values=[int(r['new_purchases']) for r in records if int(r['initial_promoters'])==n]
        axs[1].scatter(n+rng.uniform(-.15,.15,len(values)),values,s=14,alpha=.35,color=COLORS[n],edgecolors='none')
        axs[1].plot([n-.19,n+.19],[np.mean(values)]*2,color='black',lw=2,label='Media' if n==0 else None)
        axs[1].plot(n,np.median(values),marker='D',ms=4,color='white',markeredgecolor='black',label='Mediana' if n==0 else None)
    axs[1].set(title='Compras nuevas al período 120',ylabel='Personas entre 480 susceptibles',ylim=(-15,490))
    axs[1].legend(fontsize=9)
    for ax in axs:
        ax.set_xticks(x,['0\n0 %','1\n0,83 %','2\n1,67 %','3\n2,50 %']);ax.set_xlabel('Promotores iniciales y porcentaje de C0 = 120')
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    fig.suptitle('Piloto refinado · 400 corridas · 120 períodos',fontsize=15)
    fig.supxlabel('IC Wilson del 95 % por condición. Puntos: réplicas individuales. Parámetros basales constantes.',fontsize=9)
    save(fig,out,'F1_Despegue_y_compras')

    sens=read(source/'classification_sensitivity_summary.csv')
    keys=[f'd{d}_f{f:03d}' for d in (4,6,8) for f in (25,50,100)]+['M6','M6_growth110','M6_growth150']
    labels=[f'{d} períodos · {f:g} % del mercado' for d in (4,6,8) for f in (2.5,5,10)]+['M6 · crecimiento 1,25','M6 · crecimiento 1,10','M6 · crecimiento 1,50']
    data=np.array([[int(next(r['events'] for r in sens if r['setting']==key and int(r['count'])==n)) for n in range(4)] for key in keys])
    fig,ax=plt.subplots(figsize=(8.1,6.7),layout='constrained');im=ax.imshow(data,cmap='YlGnBu',vmin=0,vmax=100,aspect='auto')
    for i in range(len(keys)):
        for j in range(4):ax.text(j,i,str(data[i,j]),ha='center',va='center',color='white' if data[i,j]>65 else '#172B36')
    ax.set(xticks=range(4),xticklabels=['0','1','2','3'],yticks=range(len(labels)),yticklabels=labels,xlabel='Promotores iniciales',title='Sensibilidad de la clasificación')
    ax.axhline(8.5,color='white',lw=3);fig.colorbar(im,ax=ax,label='Eventos observados / 100 réplicas',shrink=.75)
    fig.supxlabel('Cada fila reclasifica las mismas 400 trayectorias. Principal: 6 períodos y 5 % (24 compras).',fontsize=9)
    save(fig,out,'F2_Sensibilidad_criterio')

    incidence=read(source/'cumulative_incidence.csv')
    fig,axs=plt.subplots(1,2,figsize=(11.7,4.2),layout='constrained')
    for ax,endpoint,title in zip(axs,('sustained_confirmation','reach50_time'),('Difusión sostenida v0.2','Alcanzar 50 % de los 480 susceptibles')):
        for n in range(4):
            block=[r for r in incidence if r['endpoint']==endpoint and int(r['count'])==n]
            ax.step([int(r['period']) for r in block],[float(r['cumulative_incidence']) for r in block],where='post',color=COLORS[n],label=f'{n} promotor' if n==1 else f'{n} promotores')
        ax.set(title=title,xlabel='Período',ylabel='Fracción acumulada de las 100 réplicas',ylim=(-.025,1.04),xlim=(0,120));ax.grid(alpha=.18)
    axs[1].legend(loc='lower right',fontsize=9)
    fig.supxlabel('Sin evento al cierre: censura al 120. El denominador incluye siempre las 100 réplicas.',fontsize=9)
    save(fig,out,'F3_Tiempos_y_alcance')

    pairs=read(source/'paired_summary.csv');sales=[r for r in pairs if r['metric']=='sales_difference']
    fig,ax=plt.subplots(figsize=(8.6,4.4),layout='constrained');y=np.arange(len(sales))
    means=np.array([float(r['mean']) for r in sales]);lo=np.array([float(r['low']) for r in sales]);hi=np.array([float(r['high']) for r in sales])
    ax.errorbar(means,y,xerr=[means-lo,hi-means],fmt='o',color='#197C87',capsize=5)
    ax.axvline(0,color='#687783',ls='--',lw=1)
    ax.set(yticks=y,yticklabels=[r['contrast'].replace('P','')+' promotores' for r in sales],xlabel='Diferencia media de compras nuevas al período 120',title='Contrastes emparejados por red y semilla')
    ax.invert_yaxis();ax.grid(axis='x',alpha=.18)
    fig.supxlabel('100 pares por contraste; IC bootstrap percentil 95 %, 20.000 remuestras. Sin ajuste múltiple.',fontsize=9)
    save(fig,out,'F4_Contrastes_emparejados')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();main(a.analysis,a.out)
