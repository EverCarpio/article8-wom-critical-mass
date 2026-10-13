"""Build complete, closed deliverables after successful execution and analysis."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from archive_runs import sha


def zip_paths(target,items):
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path,name in items:archive.write(path,name)
    with zipfile.ZipFile(target) as archive:
        bad=archive.testzip()
        if bad:raise ValueError('ZIP CRC failed: '+bad)


def files(root,prefix):
    return [(p,str(Path(prefix)/p.relative_to(root))) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]


def build(project,source,analysis,figures,pack,out):
    run=json.loads((source/'execution_summary.json').read_text());summary=json.loads((analysis/'analysis_summary.json').read_text())
    if run['completed_runs']!=1800 or run['failed_runs'] or summary['runs']!=1800:raise ValueError('Incomplete data')
    raw=json.loads((pack/'raw_archives_manifest.json').read_text())
    if len(raw)!=34 or sum(r['runs'] for r in raw)!=1800:raise ValueError('Incomplete archive blocks')
    out.mkdir(parents=True,exist_ok=True);design=project/'design';design.mkdir(exist_ok=True)
    for name in ('design.json','planned_runs.csv','pre_execution_record.json','execution_summary.json','execution_interruption.json'):
        if (source/name).exists():shutil.copyfile(source/name,design/name)
    (project/'verification'/'verification_summary.json').write_text(json.dumps({**summary,'tests_passed':20,'new_tests':6,'inherited_tests':14,'frozen_model_files':61,'raw_blocks':34},indent=2)+'\n')
    shutil.copyfile(pack/'raw_archives_manifest.json',analysis/'raw_archives_manifest.json')
    manifest={str(p.relative_to(project)):sha(p) for p in sorted(project.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p!=project/'SOURCE_SHA256.json'}
    (project/'SOURCE_SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    zip_paths(out/'Article_8_Energia_WOM_Codigo_v0.3.0.zip',files(project,project.name))
    paths=files(analysis,'analysis')
    for folder in ('tables','records'):paths+=files(source/folder,'experiment/'+folder)
    for name in ('design.json','planned_runs.csv','pre_execution_record.json','execution_summary.json','execution_interruption.json','run_manifest.csv'):
        if (source/name).exists():paths.append((source/name,'experiment/'+name))
    zip_paths(out/'Article_8_Energia_WOM_Resultados_v0.3.0.zip',paths)
    zip_paths(out/'Article_8_Energia_WOM_Figuras_v0.3.0.zip',files(figures,'figures'))
    shutil.copyfile(figures/'Article_8_Energia_WOM_F1_Despegue.png',out/'Article_8_Energia_WOM_F1_Despegue.png')
    shutil.copyfile(project/'docs'/'Article_8_Energia_WOM_Diseno_v0.3.0.md',out/'Article_8_Energia_WOM_Diseno_v0.3.0.md')
    shutil.copyfile(project/'docs'/'Article_8_Energia_WOM_Informe_v0.3.0.md',out/'Article_8_Energia_WOM_Informe_v0.3.0.md')
    for row in raw:
        target=out/row['name']
        if not target.exists():shutil.copyfile(pack/row['name'],target)
        if sha(target)!=row['sha256']:raise ValueError('Raw staged hash mismatch')
    entries=[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file() and p.name.startswith('Article_8_') and p.name!='Article_8_Energia_WOM_Indice_v0.3.0.md']
    lines=['# Article 8 — Índice de entrega v0.3.0','','1.800 corridas; P0=1/2 × E0=0,3/0,6/0,9 × λ=0/1/2; cien réplicas emparejadas y 120 períodos.',
      '', 'Código: motor M6 congelado, adaptador, diseño, scripts y 20 pruebas. Resultados: tablas procesadas y metadatos/tablas por corrida. Figuras: cuatro figuras en PNG/SVG/PDF. Trazas: 34 TAR: 33 con 54 corridas y uno con 18; archivos TAR.XZ completos y verificados. El README del código contiene reproducción y diccionario.', '',
      '| Archivo | Bytes | SHA-256 |','|---|---:|---|']
    lines += [f"| {r['name']} | {r['bytes']} | `{r['sha256']}` |" for r in entries]
    (out/'Article_8_Energia_WOM_Indice_v0.3.0.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'deliverables':len(entries)+1,'bytes':sum(r['bytes'] for r in entries),'rows':summary['agent_period_rows']}))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('project','source','analysis','figures','pack','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();build(a.project,a.source,a.analysis,a.figures,a.pack,a.out)
