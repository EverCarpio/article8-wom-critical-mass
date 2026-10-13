"""Source-grounded report, without mixing prior pilots into this sample."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from analyze_energy_wom import read_csv


def fmt(value,digits=2):
    return f'{float(value):.{digits}f}' if value not in ('',None) else '—'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])


def report(source,analysis,path):
    summary=json.loads((analysis/'analysis_summary.json').read_text());execution=json.loads((source/'execution_summary.json').read_text())
    started=json.loads((source/'pre_execution_record.json').read_text())['prepared_at_utc']
    elapsed_total=(datetime.fromisoformat(execution['completed_at_utc'])-datetime.fromisoformat(started)).total_seconds()
    interruption=json.loads((source/'execution_interruption.json').read_text()) if (source/'execution_interruption.json').exists() else None
    cells=read_csv(analysis/'cell_summary.csv');effects=read_csv(analysis/'paired_summary.csv');sensitivity=read_csv(analysis/'sensitivity_summary.csv')
    frontier=read_csv(analysis/'discrete_frontier.csv');cohorts=read_csv(analysis/'cohort_summary.csv')
    if summary['runs']!=1800 or summary['plan_sha256']!='0ad8021f122d58024ca65fc3f625f61ac2f156eb4643f4606caf5f9c4c72093f':raise ValueError('Unrecognized completed design')
    lines=['# Article 8 — Energía inicial y WOM negativo, v0.3.0','',
        'Fecha: 27 de septiembre de 2026. Simulación teórica en Python. **1.800 corridas nuevas: 18 condiciones × 100 réplicas, con 120 períodos por corrida.**',
        '', '## Diseño y alcance','',
        'Se cruzaron uno o dos promotores iniciales, energía positiva inicial de 0,3/0,6/0,9 y peso negativo λ=0/1/2. Los cien entornos nuevos usan semillas 830001–830100, emparejadas en las dieciocho celdas. Las corridas de los pilotos previos no entran en los promedios ni en los intervalos de esta entrega.',
        '', 'N=600, seis comunidades, C0=120, S0=480 y seis detractores iniciales. La calidad es 0,7. Se mantiene selección repartida y energía negativa inicial y endógena 0,6. E0 modifica solamente los promotores iniciales; los nuevos promotores conservan energía 0,6. P0=1 y P0=2 equivalen a 0,8333 % y 1,6667 % de C0, respectivamente.',
        '', '**λ=0 neutraliza la influencia negativa; conserva mensajes negativos y formación de detractores.** λ=1 es la referencia y λ=2 duplica el peso en la penalización de compra y en la presión neta. Este experimento no varía el número inicial ni la energía de los detractores. Tampoco equivale a comparar ausencia/presencia del módulo negativo.',
        '', 'La política repartida hace que el segundo promotor ocupe otra comunidad. El efecto P2−P1 incluye conjuntamente el aumento de cantidad y de cobertura; no separa ambos mecanismos.',
        '', '## Resultado principal y volumen de compras','',
        'Se conserva difusión sostenida v0.2. Una ventana completa de seis períodos debe tener compras en cada período, al menos 24 compras totales, presión neta positiva siempre, stock final de promotores positivo y no menor al inicial, nacimientos que cubran salidas durante la segunda mitad con al menos un nacimiento, compras en dos o más comunidades y ninguna entrada externa. Se registra la presencia histórica de al menos una ventana hasta t=120.',
        '', 'La etiqueta significa persistencia durante una ventana finita, no crecimiento perpetuo. Como λ también afecta la presión usada por el clasificador, se informa el volumen de compras como resultado independiente. Los intervalos Wilson del 95 % son puntuales, sin corrección por multiplicidad.', '',
        table(['P0','E0','λ','Sostenida /100','IC 95 %','Compras: media','Mediana','M6 /100'],
          [[r['count'],r['positive_energy'],fmt(r['negative_weight'],0),r['sustained_v02_count'],f"{100*float(r['sustained_v02_low']):.1f}–{100*float(r['sustained_v02_high']):.1f} %",fmt(r['sales_mean']),fmt(r['sales_median'],1),r['m6_takeoff_count']] for r in cells]),
        '', '## Efecto emparejado del segundo promotor','',
        'Cada diferencia compara dos corridas del mismo entorno. Los intervalos percentiles se calculan con 20.000 remuestras de las cien parejas. La tabla conserva también las parejas en que el segundo promotor produjo menos compras: un efecto medio no implica monotonicidad en todas las trayectorias.', '']
    es={ (r['contrast'],r['metric']):r for r in effects}
    rows=[]
    for r in effects:
        if r['kind']!='promoters' or r['metric']!='new_purchases':continue
        b=es[r['contrast'],'sustained_v02']
        rows.append([r['contrast'],fmt(r['mean']),f"{fmt(r['low'])} a {fmt(r['high'])}",f"{100*float(b['mean']):+.1f}",f"{100*float(b['low']):+.1f} a {100*float(b['high']):+.1f}",r['negative_pairs']])
    lines += [table(['Contraste','Δ compras','IC 95 %','Δ sostenida (pp)','IC 95 % (pp)','Pares con menos compras'],rows),'',
        '## Efectos de energía y de peso negativo','',
        'Las diferencias de energía usan 0,6−0,3 y 0,9−0,6, manteniendo P0 y λ. Las de peso negativo usan 1−0 y 2−1, manteniendo P0 y E0. Un signo negativo representa reducción del resultado. No se promedian las celdas para ocultar heterogeneidad.', '']
    for kind,title in [('energy','Energía inicial'),('negative_weight','Peso negativo')]:
        rows=[]
        for r in effects:
            if r['kind']!=kind or r['metric']!='new_purchases':continue
            b=es[r['contrast'],'sustained_v02']
            rows.append([r['contrast'],fmt(r['mean']),f"{fmt(r['low'])} a {fmt(r['high'])}",f"{100*float(b['mean']):+.1f}",f"{100*float(b['low']):+.1f} a {100*float(b['high']):+.1f}"])
        lines += [f'### {title}','',table(['Contraste','Δ compras','IC 95 %','Δ sostenida (pp)','IC 95 % (pp)'],rows),'']
    lines += ['La interacción extrema se define como [Y(E0=0,9,λ=2)−Y(0,3,2)]−[Y(0,9,0)−Y(0,3,0)]. Mide cuánto cambia el efecto de elevar energía cuando se pasa del peso negativo cero al doble. La remuestra conserva las cuatro celdas del mismo entorno.', '',
        table(['P0','Resultado','Interacción','IC 95 %'],[[r['contrast'],r['metric'],fmt(float(r['mean'])*(100 if r['metric']=='sustained_v02' else 1)),f"{fmt(float(r['low'])*(100 if r['metric']=='sustained_v02' else 1))} a {fmt(float(r['high'])*(100 if r['metric']=='sustained_v02' else 1))}"] for r in effects if r['kind']=='interaction' and r['metric'] in ('new_purchases','sustained_v02')]),'',
        'Las interacciones del evento binario se expresan en puntos porcentuales. Todos los contrastes son exploratorios y sus intervalos no se ajustan por comparaciones múltiples. Un intervalo bootstrap de ancho cero refleja ausencia de variación en esta muestra; no demuestra certeza poblacional.', '',
        '## Frontera discreta condicionada','',
        'La tabla siguiente muestra el menor conteo ensayado que alcanza una frecuencia observada de difusión sostenida del 75 %. La segunda columna de cruces aplica el mismo objetivo al límite inferior Wilson. Son dos resúmenes diferentes, no intervalos de confianza de un umbral ajustado.', '',
        table(['E0','λ','Menor P0 ensayado ≥75 %','Menor P0 con límite inferior ≥75 %','Estado de la grilla'],
          [[r['positive_energy'],fmt(r['negative_weight'],0),r['minimum_tested_count'] or 'No alcanzado',r['minimum_tested_lower_bound_count'] or 'No alcanzado',{'left_boundary_at_one':'Ya cruza en 1','crossing_at_two':'Cruza en 2','not_reached_in_tested_grid':'Ninguno de {1,2}'}[r['status']]] for r in frontier if r['criterion']=='sustained_v02' and float(r['target'])==.75]),'',
        'Si uno cruza, solo se conoce el mínimo dentro de esta grilla: no se ensayó cero en este factorial. Si ninguno cruza, no se identifica el umbral dentro de {1,2}; no se concluye que tres basten. `discrete_frontier.csv` incluye además objetivos de 25 % y 50 % y el criterio M6. No se interpola ni se declara un porcentaje universal.', '',
        '## Sensibilidad del criterio y seguimiento','',
        f"Se realizaron {summary['classification_evaluations']:,} evaluaciones de clasificación sobre las mismas 1.800 trayectorias: nueve definiciones v0.2 y tres M6. Hubo {summary['classification_disagreements']} desacuerdos entre el criterio principal v0.2 y M6. No son simulaciones adicionales.", '',
        table(['P0','E0','λ','Sostenida principal /100','Rango: nueve variantes /100','Fuentes positivas abiertas al 120'],
          [[r['count'],r['positive_energy'],fmt(r['negative_weight'],0),r['sustained_v02_count'],
            f"{min(int(s['events']) for s in sensitivity if s['scenario']==r['scenario'] and s['setting'].startswith('d'))}–{max(int(s['events']) for s in sensitivity if s['scenario']==r['scenario'] and s['setting'].startswith('d'))}",100-int(r['absorbed_count'])] for r in cells]),'',
        f"Después del período 60 se produjeron {summary['late_purchases']:,} compras adicionales en {summary['runs_with_late_purchases']} corridas. Al 120 quedan {summary['open_trajectories']} trayectorias con promotores activos, experiencias pendientes o activaciones positivas pendientes. No se extienden selectivamente. Sus compras finales son compras al horizonte común, no tamaños definitivos de cascada.", '',
        'Las figuras de incidencia mantienen cien réplicas como denominador. Las medianas de tiempo del archivo `cell_summary.csv` son condicionales a observar el evento y se acompañan de sus conteos. Las etiquetas de colapso, saturación y clase terminal siguen siendo las de M6 y permanecen separadas del criterio histórico v0.2.', '',
        f"Clases terminales M6, acumuladas únicamente como inventario de este diseño: `{json.dumps(summary['terminal_counts'],ensure_ascii=False,sort_keys=True)}`. Esta mezcla deliberada de condiciones no estima una probabilidad de mercado general.", '',
        '## Reproducción de la cohorte inicial','',
        'El archivo `cohort_initial.csv` conserva por corrida las cohortes iniciales para ventanas 3/6/12, sus hijos directos y los cocientes observados. Se respeta el retraso hasta la activación; no se divide por cero ni se declara completa una ventana censurada. El resumen siguiente corresponde a la ventana de seis períodos, observada con el seguimiento necesario.', '',
        table(['P0','E0','λ','R de cohorte: media','Mediana','Réplicas con R≥1'],[[r['count'],r['positive_energy'],fmt(r['negative_weight'],0),fmt(r['ratio_mean']),fmt(r['ratio_median']),r['ratio_at_least_one']] for r in cohorts if r['width']=='6']), '',
        '## Verificación y reproducción','',
        'Pasaron 20 pruebas: seis del nuevo diseño y archivado, junto con las catorce previas del adaptador y observador v0.2. Una primera ejecución de la prueba de corrupción detectó correctamente el archivo truncado pero esperaba otro tipo de excepción; se corrigió la expectativa y la suite final pasó. No fue un fallo de una corrida experimental.', '',
        'Los 61 archivos del motor coinciden con el manifiesto M6. Su suite de 229 pruebas corresponde a la verificación previa; no se presenta como una nueva ejecución. La condición basal E0=0,6, λ=1 se contrastó con el controlador anterior usando la misma semilla, sin diferencias en estados, eventos o historia de agentes.', '',
        f"Las 1.800 corridas pasaron invariantes, reconciliación de mensajes y {summary['cohort_windows_checked']:,} comprobaciones independientes de ventanas de cohorte. Se conservaron y verificaron {summary['agent_period_rows']:,} filas agente–período y {summary['archive_members_verified']:,} miembros de archivos por corrida. Cada traza se leyó completa, comprobando huellas y la secuencia de los 600 agentes en los 121 instantes. No se muestrearon períodos ni se descartaron eventos.", '',
        'Cada corrida tiene un archivo TAR.XZ sin pérdida, leído y contrastado con su manifiesto antes de retirar la copia intermedia. Treinta y cuatro contenedores TAR reúnen tres réplicas completas cada uno (54 corridas), salvo el último con una réplica (18 corridas) y vuelven a verificar las huellas de todos los archivos contenidos. El almacenamiento modifica el empaquetado, no la simulación.', '',
        f"Huella del plan previo: `{summary['plan_sha256']}`. Tiempo de la última invocación, incluyendo reanudación, archivado y comprobaciones: {execution['wall_seconds']:.1f} segundos con {execution['workers']} procesos. Lapso desde la preparación inicial hasta la terminación: {elapsed_total:.1f} segundos, incluyendo la interrupción y la recuperación; no suma tiempos concurrentes. Python {execution['python_version']}. Las figuras y el análisis se ejecutaron después; sus tiempos y las transferencias no se incluyen en esa cifra.", '',
        'Consulte README para reproducir las corridas o reconstruir el análisis desde las trazas. Los archivos incluyen configuración, semillas, red, estados, eventos, compra, experiencia, energía, genealogía, observación, sensibilidad y manifiestos. No se modificaron las reglas M6 ni se recalibró el criterio tras ver resultados.', '',
        '## Límites y siguiente etapa','',
        'Estos resultados evalúan dos conteos y tres niveles específicos de energía y peso negativo en un único tipo de red, calidad y política de colocación. No validan empíricamente una recomendación para empresas ni identifican una frontera completa. Para separar cantidad y ubicación se requiere un experimento de colocación; para ampliar WOM negativo, variar cantidad o energía de detractores de forma independiente. La calidad, fatiga y topología siguen pendientes como sensibilidad sustantiva. El diseño y los resultados presentes pueden incorporarse al primer borrador como un experimento factorial condicionado.'
    ]
    outcome=[
        '## Lectura de los resultados', '',
        'Con WOM negativo de referencia (λ=1), la difusión sostenida fue 69/80/84 % con un promotor y 84/95/97 % con dos, al variar E0 entre 0,3/0,6/0,9. El segundo promotor mejora la frecuencia en las nueve combinaciones de energía y peso: 11–15 puntos porcentuales. Estas son frecuencias simuladas, no probabilidades universales.', '',
        'En la referencia E0=0,6, λ=1, pasar de uno a dos añade 15 puntos porcentuales de difusión sostenida (IC bootstrap 95 %: 8–22) y 61,77 compras medias (34,22–91,95). La mediana de la diferencia de compras es 3,5; 36/100 parejas registran menos compras con dos. La mejora del promedio no implica que todas las cascadas crezcan más.', '',
        'Elevar E0 de 0,3 a 0,6 con λ=1 añade 11 puntos porcentuales en ambos conteos: IC 1–21 con un promotor y 3–19 con dos. En cambio, el incremento de 0,6 a 0,9 produce diferencias de 4 puntos (−5 a 13) y 2 puntos (−3 a 7): estos intervalos no distinguen claramente una mejora adicional. La separación entre medias y medianas muestra la mezcla de cascadas amplias y trayectorias de poca adquisición.', '',
        'El peso negativo produce cambios pequeños en la clasificación dentro del rango ensayado. Al pasar de λ=0 a 1, la frecuencia baja uno o dos puntos con un promotor y permanece igual con dos. Entre λ=1 y 2, la clasificación es idéntica en las 600 parejas correspondientes; las compras sí varían. En E0=0,6, el cambio medio de compras es −0,35 con un promotor (IC −0,73 a 0,11) y −0,70 con dos (−1,88 a 0,27). Esto no demuestra irrelevancia general del WOM negativo: se fijaron cantidad y energía de detractores, calidad y retención de memoria.', '',
        'Para observar al menos 75 % de difusión bajo el criterio principal, el menor conteo ensayado es dos con E0=0,3 y uno con E0=0,6 o 0,9. Si se exige que el límite Wilson inferior también alcance 75 %, con E0=0,6 se requieren dos dentro de esta grilla; con E0=0,9 ya cruza uno. Son cruces puntuales condicionados, no una frontera continua ni una garantía. Ese cruce del límite inferior no se mantiene en todas las definiciones: con un promotor, E0=0,9 y λ=1, las nueve variantes producen 78–84 eventos. La sensibilidad completa aparece más abajo.', '',
        'La nueva referencia da 80/100 y 95/100, frente a 83/100 y 100/100 del piloto refinado previo. Son lotes de semillas distintos y el motor es idéntico; no se mezclan como si fueran la misma muestra. La incertidumbre Monte Carlo acompaña cada resultado.', '',
    ]
    insert=lines.index('## Diseño y alcance')
    lines[insert:insert]=outcome
    if interruption:
        lines += ['', '## Continuidad de la ejecución', '', f"El entorno se reinició durante el cálculo. Se preservaron y comprobaron {interruption['completed_records_preserved']} corridas cerradas antes de reanudar. Se aislaron tres directorios de exportación parcial y dos compresiones incompletas; se reconstruyeron las pendientes con las mismas semillas y el plan intacto. No se sustituyeron réplicas ni se seleccionaron resultados. `execution_interruption.json` conserva el registro. La cifra final sigue siendo 1.800 corridas únicas."]
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();report(a.source,a.analysis,a.out)
