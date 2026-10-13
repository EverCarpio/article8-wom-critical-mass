# Article 8 — Energía inicial × WOM negativo, v0.3.0

Experimento teórico en Python: P0={1,2}, E0={0.3,0.6,0.9}, λ={0,1,2}; 100 semillas nuevas emparejadas 830001–830100; 120 períodos; 1.800 corridas. Motor congelado M6 0.6.0-m6. El criterio principal es difusión sostenida v0.2, sin cambios. Véase `docs/Article_8_Energia_WOM_Diseno_v0.3.0.md`.

## Entorno y verificación

Python 3.12.14. El motor usa biblioteca estándar; el análisis y las figuras usan NumPy 2.3.5 y Matplotlib 3.10.8. Desde este directorio:

```bash
python -m pip install -r requirements-analysis.txt
python -m unittest discover -s tests -v
```

La suite de esta entrega contiene 20 pruebas (6 nuevas + 14 heredadas). `verification/tests.log` documenta su ejecución. `model/SOURCE_SHA256.json` conserva las 61 huellas del motor. No modificar archivos del motor para reproducir este experimento.

## Ejecución completa

Usar un directorio de ejecución estable, preferiblemente fuera de cualquier carpeta que sincronice archivos abiertos. El almacenamiento temporal alcanza solo unas pocas exportaciones sin comprimir porque cada corrida se archiva y verifica antes de borrar su copia intermedia. Conservar espacio para aproximadamente 3–4 GB de archivos comprimidos, más copias de empaquetado, tablas y entregables.

```bash
python scripts/run_energy_wom.py --out /tmp/article8_energy_wom_replication --prepare-only
python scripts/run_energy_wom.py --out /tmp/article8_energy_wom_replication --workers 8
python scripts/analyze_energy_wom.py --source /tmp/article8_energy_wom_replication --out /tmp/article8_energy_wom_analysis
python scripts/plot_energy_wom.py --source /tmp/article8_energy_wom_analysis --out /tmp/article8_energy_wom_figures
python scripts/report_energy_wom.py --source /tmp/article8_energy_wom_replication --analysis /tmp/article8_energy_wom_analysis --out /tmp/Article_8_Energia_WOM_Informe_v0.3.0.md
python scripts/pack_energy_wom.py --source /tmp/article8_energy_wom_replication --out /tmp/article8_energy_wom_blocks
```

El controlador congela el plan antes de simular y rechaza cambios al reanudar. Solo reanuda corridas con registros cerrados y huellas válidas. Una exportación parcial genera un error que exige inspección; no se sustituyen semillas. Los scripts `run_refined.py`, `legacy_pilot.py` y `verify_recover_exports.py` se conservan como dependencias y pruebas de compatibilidad. **No invocarlos para ejecutar este nuevo factorial.** El CLI M6 original no interpreta `exact_promoters`; usar `run_energy_wom.py`.

Los identificadores `r001_P1_E3_W0` significan réplica 1, un promotor, energía inicial 0,3 y peso negativo 0. Cien réplicas son cien entornos independientes, no 1.800 entornos independientes: las dieciocho celdas están emparejadas dentro de cada réplica.

## Rehacer el análisis con los resultados entregados

Descomprimir `Article_8_Energia_WOM_Resultados_v0.3.0.zip` en un directorio vacío. Contiene `analysis/` (tablas procesadas) y `experiment/` (plan, metadatos, registros de corrida y tablas pequeñas con huellas). Los 34 archivos `Article_8_Energia_WOM_Trazas_rNNN_NNN_v0.3.0.tar` contienen 54 TAR.XZ por bloque, salvo el último con 18, además de registros y plan. Extraerlos en el mismo directorio `experiment/`. Los metadatos comunes son idénticos; `block_manifest.json` pertenece a cada contenedor y debe consultarse dentro de ese contenedor si se requiere su manifiesto individual.

El archivo `raw_archives_manifest.json` del ZIP de resultados identifica el tamaño y SHA-256 de cada contenedor. Se deben comprobar antes de extraer. Después de extraer los 34:

```bash
python scripts/analyze_energy_wom.py --source /ruta/experiment --out /ruta/analysis_rebuilt
python scripts/plot_energy_wom.py --source /ruta/analysis_rebuilt --out /ruta/figures_rebuilt
```

El analizador comprueba la huella de cada TAR.XZ y de cada tabla pequeña antes de calcular estadísticas. Para inspeccionar la historia completa de una corrida, extraer su TAR.XZ en una carpeta individual. `archive_runs.verify_archive(path)` vuelve a leer todos los miembros y comprueba huellas y las 72.600 filas agente–período. Las exportaciones incluyen configuración, red, eventos, decisiones de compra, experiencia, activación, energía, genealogía, reproducción y clasificación.

## Diccionario breve de resultados

- `runs.csv`: una fila por corrida; parámetros, semilla, compras, eventos históricos, estado al cierre, fechas y huellas.
- `cell_summary.csv`: 18 celdas; compras, proporciones Wilson y tiempos condicionales con sus conteos.
- `paired_differences.csv` y `paired_summary.csv`: efectos por semilla e intervalos bootstrap. Compras en personas; `sustained_v02` y `m6_takeoff` en fracciones (multiplicar por 100 para puntos porcentuales).
- `system_period_all.csv`: 217.800 filas, incluyendo t=0, con agregados del sistema.
- `classification_sensitivity.csv` y `sensitivity_summary.csv`: 21.600 reclasificaciones y sus 216 resúmenes. No son corridas nuevas.
- `incidence.csv`: incidencia acumulada con denominador constante 100, incluyendo los casos sin evento.
- `cohort_initial.csv` y `cohort_summary.csv`: reproducción de cohortes para ventanas 3/6/12.
- `discrete_frontier.csv`: mínimos dentro de {1,2}; no interpolaciones ni umbrales universales.
- `classification_disagreements.csv` y `open_trajectories.csv`: casos que requieren distinguir definición o censura al horizonte.
- `analysis_summary.json`, `execution_summary.json`, `pre_execution_record.json`: auditoría, duración y plan previo.

λ=0 mantiene mensajes y formación de detractores pero anula su influencia en compra y presión neta. E0 cambia solo el grupo inicial; nuevos promotores conservan energía 0,6. El segundo promotor incorpora otra comunidad bajo selección repartida. La presión usada por la clasificación depende de λ; interpretar junto con compras y cohortes.

El generador del informe verifica la huella exacta del diseño original para impedir que otra ejecución se presente como estos resultados. Para diseñar otro experimento, cambiar versión, semillas y carpeta de destino; no sobreescribir este plan. Los metadatos de tiempo y las huellas que dependen de ellos pueden cambiar entre ejecuciones, aunque las trayectorias determinísticas y los resultados numéricos deben reproducirse.
