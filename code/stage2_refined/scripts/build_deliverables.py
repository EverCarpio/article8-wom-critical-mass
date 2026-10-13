"""Build the report and compact, reproducible deliverables after verification."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    with path.open() as f:return list(csv.DictReader(f))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])


def archive(path,items):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,name in sorted(items,key=lambda x:x[1]):z.write(p,name)
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('Invalid ZIP')


def main(source,analysis,figures,out):
    s=json.loads((analysis/'analysis_summary.json').read_text());sc=s['scenarios']
    if s['plan_sha256']!='8379eeb9074402a056ce47181a67fc5474f66daf8806944be2aa505537d98790':
        raise ValueError('The report interpretation is specific to the frozen v0.2.0 experiment')
    recovery=json.loads((source/'export_recovery.json').read_text())
    traces=json.loads((out/'trace_archives.json').read_text())
    if len(traces)!=10 or sum(t['runs'] for t in traces)!=400:raise ValueError('Missing trace archives')
    if any(sha(out/t['file'])!=t['sha256'] for t in traces):raise ValueError('Trace archive changed')
    baseline=table(['P0','% de C0','v0.2 / 100','IC 95 % v0.2','M6 / 100','Compras: media','Mediana','Mín.–máx.'],[
        [r['count'],f"{100*r['share']:.3f}",r['sustained_v02_count'],f"{100*r['sustained_v02_low']:.1f}–{100*r['sustained_v02_high']:.1f} %",
         r['m6_takeoff_count'],f"{r['sales_mean']:.2f}",f"{r['sales_median']:.1f}",f"{r['sales_min']}–{r['sales_max']}"] for r in sc])
    pairs=table(['Contraste','Δ compras media','IC bootstrap 95 %','Pares con menos compras'],[
        [r['contrast'],f"{r['mean']:.2f}",f"{r['low']:.2f} a {r['high']:.2f}",r['negative_pairs']] for r in s['paired'] if r['metric']=='sales_difference'])
    cross=read(analysis/'classification_cross_table.csv')
    crosstab=table(['P0','Ambos criterios','Solo v0.2','Solo M6','Ninguno'],[
        [n]+[next(r['runs'] for r in cross if int(r['count'])==n and r['m6_takeoff']==str(old) and r['sustained_v02']==str(new))
             for old,new in ((True,True),(False,True),(True,False),(False,False))] for n in range(4)])
    sensitivity=read(analysis/'classification_sensitivity_summary.csv')
    senskeys=[f'd{d}_f{f:03d}' for d in (4,6,8) for f in (25,50,100)]+['M6','M6_growth110','M6_growth150']
    senstable=table(['Definición','P0=0','P0=1','P0=2','P0=3'],[[key]+[next(r['events'] for r in sensitivity if r['setting']==key and int(r['count'])==n) for n in range(4)] for key in senskeys])
    horizon=table(['P0','Compras medias t60','Compras medias t120','Corridas con compras t61–120','Sin fuentes de compras al cierre'],[
        [r['count'],f"{r['purchases60_mean']:.2f}",f"{r['sales_mean']:.2f}",r['runs_with_late_purchases'],r['absorbed_count']] for r in sc])
    reach=table(['P0','Alcanzan 10 %','Alcanzan 25 %','Alcanzan 50 %','Alcanzan 75 %','Mediana t50 entre quienes lo alcanzan'],[
        [r['count']]+[f"{r[f'reach{level}_events']}/100" for level in (10,25,50,75)]+[r['reach50_median_among_events'] if r['reach50_median_among_events'] is not None else 'No alcanzado'] for r in sc])
    frontier=table(['Criterio','Frecuencia objetivo','Menor P0 ensayado','Menor P0 cuyo límite Wilson inferior supera el objetivo'],[
        [r['endpoint'],f"{100*r['target']:.0f} %",r['minimum_tested_count'] if r['minimum_tested_count'] is not None else 'No alcanzado',
         r['minimum_count_with_pointwise_lower_bound_at_target'] if r['minimum_count_with_pointwise_lower_bound_at_target'] is not None else 'No alcanzado'] for r in s['frontier']])
    unresolved=', '.join(s['unabsorbed_run_ids']) or 'Ninguna'
    report=f'''# Article 8 — Informe del piloto refinado v0.2.0

Fecha: 27 de septiembre de 2026. Alcance: simulación teórica en Python, sin datos empíricos. **400 corridas nuevas de 120 períodos**, 100 réplicas por condición y 100 entornos emparejados.

## Resultado y alcance

Se completaron las cuatro condiciones con 0, 1, 2 y 3 promotores iniciales. El porcentaje usa los **120 clientes iniciales**, no las 600 personas de la población. Las compras nuevas se producen entre los 480 susceptibles iniciales. Las cifras de este informe pertenecen exclusivamente a estas 400 corridas; las 150 del piloto anterior y sus seis seguimientos permanecen separados.

{baseline}

**Hallazgo central:** un solo promotor produjo difusión sostenida en 83/100 réplicas, frente a 100/100 con dos y con tres. El IC Wilson del 95 % para un promotor es 74,45–89,11 %: incluye una probabilidad de 75 %, por lo que el cruce observado de ese nivel conserva incertidumbre. Para dos y tres el intervalo es 96,30–100 %; cien éxitos observados no garantizan éxito universal.

Con un promotor existe una dispersión considerable entre corridas: la media de compras es 348,59 y la mediana 414,5. El promedio combina cascadas amplias con trayectorias de poca difusión. Con dos y tres se reducen los resultados de muy baja adquisición en estas semillas.

Los intervalos Wilson son marginales por condición, no bandas simultáneas ni intervalos de un umbral continuo. El criterio principal es difusión sostenida v0.2. M6 se conserva como referencia de aceleración y reposición. Cualquier mínimo observado está condicionado al entorno basal y a la política de selección repartida.

## Diseño y revisión previa del despegue

Se fijaron 100 semillas nuevas, 820001–820100, y cuatro conteos por semilla. Se mantienen N=600, seis comunidades, C0=120, seis detractores iniciales, energías iniciales 0,6, calidad 0,7 y WOM negativo activo con peso 1. Los promotores nuevos conservan energía 0,6. Red, rasgos, clientes, detractores y sorteos indexados se emparejan dentro de cada réplica; los conjuntos de promotores están anidados.

El adaptador `CountConfig` permite introducir uno y dos promotores como enteros exactos. Evita el problema de representar 1/120 y 2/120 mediante decimales finitos sin redondear personas. El motor M6 y sus reglas de compra, experiencia, contactos, formación, energía y fatiga permanecen intactos.

La revisión utiliza el diagnóstico del piloto anterior y se fijó antes de observar estas nuevas trayectorias. **No es una preinscripción externa**. La huella del plan es `{s['plan_sha256']}`; se entrega el registro temporal local previo a la ejecución.

M6 exige que las compras de la segunda mitad de una ventana de seis períodos superen en al menos 25 % a las de la primera. Esa razón puede dejar sin etiqueta una expansión inicialmente rápida. La definición revisada separa la persistencia y el volumen de la aceleración relativa.

**Difusión sostenida v0.2** exige simultáneamente, dentro de seis períodos consecutivos completos: compras en cada período; al menos 24 compras en total (5 % de los 480 susceptibles iniciales); presión neta positiva en cada período; stock promotor final positivo y no menor que al comienzo; al menos un promotor nuevo en la segunda mitad y activaciones que cubran sus salidas; compras en dos o más comunidades; y ausencia de entradas externas.

El umbral de 24 es operativo y exploratorio. No se escogió después de observar estas 400 corridas. Una trayectoria estable que se reproduce puede calificar sin acelerar; una expansión pequeña que acelera puede calificar bajo M6 y no bajo v0.2. Ninguno de los criterios es una ampliación automática del otro. La persistencia observada en seis períodos **no significa crecimiento perpetuo**.

## Diferencias entre uno, dos y tres promotores

{pairs}

Pasar de uno a dos se asocia con **70,81 compras adicionales en promedio** (IC 95 %: 41,55 a 102,82) y 17 puntos porcentuales más de difusión sostenida. La mediana de la diferencia de compras es solo cinco: la ganancia media recoge especialmente la prevención de trayectorias con poca difusión. En 41 de las 100 parejas, agregar el segundo promotor produjo menos compras al 120, aun cuando mejoró el promedio y la frecuencia de despegue.

Pasar de dos a tres añade una media de **2,69 compras** (IC 95 %: −1,17 a 6,48); esta comparación no distingue con claridad una ganancia de volumen al 120. Sí se observa una llegada más temprana al 50 % del mercado: medianas de 30 frente a 35 períodos, descriptivas y con el nivel alcanzado en las 100 corridas de ambos grupos.

Cada contraste conserva las 100 parejas de red y semilla. Los intervalos percentiles usan 20.000 remuestras de bloques y semillas 88201–88204. Son exploratorios, sin ajuste por comparaciones múltiples. Las diferencias binarias de clasificación y sus intervalos también están en `paired_summary.csv`; un intervalo bootstrap degenerado no demuestra certeza.

Con la selección repartida, agregar el segundo o tercer promotor incorpora otra comunidad. Los resultados estiman ese cambio conjunto de cantidad y cobertura bajo la política especificada. **No identifican por separado el efecto de cantidad y el de ubicación**. Tampoco requieren que cada réplica produzca más compras al agregar un promotor.

## Desacuerdos y sensibilidad de clasificación

Hubo **{s['discordant_classifications']} desacuerdos entre M6 y v0.2** en el conjunto diseñado de 400 corridas.

{crosstab}

El único desacuerdo es `r098_P1`: termina con 54 compras nuevas; M6 confirma despegue y v0.2 no. La coincidencia de presencia del evento no implica coincidencia de su fecha: con un promotor las medianas de confirmación entre los eventos observados son 15 períodos para M6 y 23 para v0.2; con dos, 12 y 16; con tres, 11 y 12,5. Las medianas usan el subconjunto de eventos de cada definición, no una estimación emparejada de diferencias temporales.

`classification_disagreements.csv` identifica cada caso, compras finales y tiempos de confirmación. Los conteos históricos pueden coexistir con saturación o cese posterior de actividad. Las categorías terminales, el colapso y la saturación siguen siendo las de M6; no se presentan como una nueva clasificación terminal derivada de v0.2.

{senstable}

En `d6_f050`, d6 significa seis períodos y f050 significa el 5 % del mercado susceptible inicial adquirido **dentro de la ventana**. f025 y f100 corresponden a 12 y 48 compras. Los volúmenes no se reescalan con la duración. Las nueve variantes v0.2 y las tres M6 producen **4.800 evaluaciones de clasificación sobre las mismas 400 trayectorias**, no nuevas simulaciones. Las conclusiones deben considerar la matriz completa; no se elige posteriormente la fila más favorable.

Las nueve variantes v0.2 producen 81–84 eventos con un promotor, 97–100 con dos y 99–100 con tres. La comparación basal es bastante estable en este rango de definiciones. Los tres factores de crecimiento M6 mantienen los mismos conteos, lo que no demuestra insensibilidad general del modelo fuera de estas condiciones.

## Horizonte y tiempos de difusión

{horizon}

Entre los períodos 61 y 120 se registraron **{s['late_purchases']} compras adicionales en {s['runs_with_late_purchases']} corridas**. Al cierre, {s['absorbed_count']}/400 carecían de promotores activos, experiencias pendientes y activaciones positivas pendientes. Esta condición de ausencia de futuras fuentes de compras se mide separadamente de la etiqueta terminal M6.

Corridas que aún conservan alguna de esas fuentes al 120: **{unresolved}**. Se mantiene el horizonte común de 120 fijado para este diseño; una trayectoria abierta no se declara extinguida ni se extiende selectivamente para mejorar una comparación.

En `r005_P1` se registran 319 compras al 120, frente a 34 al 60, y aún quedan 15 promotores activos, siete experiencias pendientes y una activación positiva pendiente. Las 319 son compras al horizonte fijado, no el tamaño definitivo de esa cascada.

{reach}

El tiempo a alcanzar un porcentaje se cuenta desde t=0. Las medianas de tiempo de la tabla se calculan solo entre quienes alcanzan ese nivel y se identifican como condicionales. Las curvas de incidencia acumulada mantienen siempre 100 réplicas como denominador y conservan como censurados al 120 los casos sin evento; no se eliminan fracasos para dibujar trayectorias aparentemente más rápidas.

## Frontera discreta e incertidumbre

{frontier}

El mínimo es únicamente el menor **conteo entero ensayado** que cruza la frecuencia indicada. No se interpola entre cero y uno ni se estima un porcentaje universal. La columna de límites inferiores ayuda a evaluar la incertidumbre de cada condición, pero no constituye un intervalo de confianza de una frontera ajustada. `discrete_frontier.csv` conserva también los límites superiores por condición.

La interpretación corresponde al escenario basal: estas corridas no identifican todavía una frontera condicionada por energía, intensidad del WOM negativo, calidad o estructura de la red. El resultado no se ajusta para reproducir el 15 % de la tesis. Tampoco es una recomendación porcentual validada para empresas reales.

## Verificación, integridad y reproducción

Pasaron **14 pruebas nuevas** de entrada por conteo, equivalencia con M6 para tres promotores, serialización, emparejamiento, integridad de trazas y trayectorias sintéticas para el criterio revisado. Los 61 archivos del motor coinciden con el manifiesto de M6, cuya suite de 229 pruebas se verificó en la etapa previa. No se presenta esa suite como una nueva ejecución en esta entrega.

Las 400 corridas pasaron invariantes y las exportaciones finales fueron verificadas. Se conservaron **{s['agent_period_rows']:,} registros agente–período**, {s['cohort_windows_checked']:,} reconciliaciones independientes de ventanas de cohorte y las trazas de eventos, decisiones y genealogía. Cada archivo comprimido se leyó y contrastó íntegramente con las huellas de los archivos originales, sin muestrear agentes o períodos.

Durante la comprobación de exportaciones se detectaron nueve copias de trazas incompletas. Se reconstruyeron con la misma semilla y las mismas reglas. Hubo además una repetición al ajustar el lector de integridad al nombre del campo `period`: **{recovery['regenerated_runs']} reconstrucciones en total**, todas con resultados idénticos y 29 archivos determinísticos coincidentes con el manifiesto original. Se entregan los detalles en `export_recovery.json`. Estas reconstrucciones no son réplicas adicionales ni reemplazos seleccionados según el resultado.

Tiempo de la ejecución original registrado: {s['wall_seconds']:.1f} segundos con cuatro procesos, sin sumar duraciones concurrentes. No incluye análisis, recuperación de exportaciones, compresión o transferencia. Python {platform.python_version()}; NumPy y Matplotlib se fijan en el archivo de dependencias. Consulte `README.md` para reconstrucción desde código o desde las trazas completas.

## Alcance de la próxima etapa

El siguiente experimento debe concentrarse alrededor de **uno y dos promotores**, variando energía y WOM negativo, con una referencia de tres y controles apropiados. Esto permitirá evaluar condiciones que desplazan la probabilidad de éxito, porque el escenario basal ya presenta frecuencias altas con conteos muy pequeños. Posteriormente deben contrastarse ubicación, calidad y fatiga. No hay fundamento para volver por defecto a un factorial centrado en 15 % ni para declarar universales los porcentajes bajos de este piloto.

Los métodos y estos resultados ya pueden incorporarse a un borrador como experimentos basales. La frontera condicional completa y la sensibilidad sustantiva siguen pendientes.
'''
    report_path=out/'Article_8_Refinado_Informe_v0.2.0.md';report_path.write_text(report)
    shutil.copy2(ROOT/'docs/Article_8_Refinado_Diseno_v0.2.0.md',out/'Article_8_Refinado_Diseno_v0.2.0.md')
    shutil.copy2(figures/'F1_Despegue_y_compras.png',out/'Article_8_Refinado_F1_Despegue.png')
    shutil.copy2(source/'export_recovery.json',ROOT/'design/export_recovery.json')
    for name in ('design.json','planned_runs.csv','pre_execution_record.json','execution_summary.json'):
        shutil.copy2(source/name,ROOT/'design'/name)
    verification={'new_tests_passed':14,'unchanged_m6_source_files':61,'previous_m6_tests':229,
        'invariants_passed':s['invariants_passed'],'exports_verified':recovery['exports_verified'],
        'regenerated_exports':recovery['regenerated_runs'],'full_agent_period_rows':s['agent_period_rows'],
        'cohort_windows_checked':s['cohort_windows_checked'],'paired_environments':100,
        'trace_blocks_verified':len(traces),'simulation_runs':400,'classification_evaluations':4800}
    (ROOT/'design/verification_summary.json').write_text(json.dumps(verification,indent=2)+'\n')
    source_files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.parts for x in ('outputs','__pycache__')) and p.name!='REFINED_SOURCE_SHA256.json']
    (ROOT/'REFINED_SOURCE_SHA256.json').write_text(json.dumps({str(p.relative_to(ROOT)):sha(p) for p in sorted(source_files)},indent=2)+'\n')
    source_files.append(ROOT/'REFINED_SOURCE_SHA256.json')
    archive(out/'Article_8_Refinado_Codigo_v0.2.0.zip',[(p,'article8_refined_v0.2.0/'+str(p.relative_to(ROOT))) for p in source_files])
    metadata=['design.json','planned_runs.csv','pre_execution_record.json','execution_summary.json','run_manifest.csv','export_recovery.json']
    items=[(p,'analysis/'+p.name) for p in analysis.iterdir() if p.is_file()]+[(source/n,'experiment_metadata/'+n) for n in metadata]
    items += [(ROOT/'design/verification_summary.json','verification_summary.json'),(ROOT/'design/verification_tests.log','verification_tests.log'),(out/'trace_archives.json','trace_archives.json')]
    archive(out/'Article_8_Refinado_Resultados_v0.2.0.zip',items)
    archive(out/'Article_8_Refinado_Figuras_v0.2.0.zip',[(p,p.name) for p in figures.iterdir() if p.is_file()])
    delivered=[out/'Article_8_Refinado_Informe_v0.2.0.md',out/'Article_8_Refinado_Diseno_v0.2.0.md',out/'Article_8_Refinado_Codigo_v0.2.0.zip',
        out/'Article_8_Refinado_Resultados_v0.2.0.zip',out/'Article_8_Refinado_Figuras_v0.2.0.zip',out/'Article_8_Refinado_F1_Despegue.png']+[out/t['file'] for t in traces]
    index='# Article 8 — Índice del piloto refinado v0.2.0\n\n400 corridas a 120 períodos; 100 réplicas por conteo inicial (0, 1, 2, 3).\n\n'
    index+=table(['Archivo','MB','SHA-256'],[[p.name,f'{p.stat().st_size/1e6:.3f}',sha(p)] for p in delivered])
    index+='\n\nLos diez TAR.XZ contienen todas las trazas, diez réplicas emparejadas por archivo (40 corridas). Extraiga todos en un mismo directorio; los cinco metadatos comunes son idénticos. Consulte el README del código.\n\n'
    index+='[Datos brutos en Drive](https://drive.google.com/drive/folders/13tBdG7wGcFkQaqWN01iseX_J10tGwBBT) · [Datos procesados en Drive](https://drive.google.com/drive/folders/1l8NhwmCJdL47P5B4cabfUlpJBL1TMecD)\n'
    index_path=out/'Article_8_Refinado_Indice_v0.2.0.md';index_path.write_text(index);delivered.append(index_path)
    request={'uploads':[{'local_path':str(p.resolve()),'purpose':'create_library_file'} for p in delivered]}
    (out/'upload_request.json').write_text(json.dumps(request,indent=2)+'\n')
    print(json.dumps({'files':len(delivered),'total_bytes':sum(p.stat().st_size for p in delivered),'out':str(out)},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','analysis','figures','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();main(a.source,a.analysis,a.figures,a.out)
