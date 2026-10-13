# Article 8 — Piloto refinado v0.2.0 (Python)

400 corridas: 0, 1, 2 y 3 promotores iniciales × 100 semillas nuevas, 120 períodos. El denominador de la proporción es C0=120 clientes, con N=600 y 480 susceptibles iniciales. Alcance teórico, sin calibración empírica.

El motor `model/article8` es la entrega M6 0.6.0-m6 íntegra, con 61 archivos controlados por su manifiesto. `scripts/refined.py` añade entrada exacta por conteo y clasificación observacional v0.2; no modifica las decisiones ni el azar del motor. La selección repartida incorpora una comunidad adicional con cada promotor en este rango, por lo que el contraste de cantidad está condicionado a esa política de ubicación.

## Reproducir desde código

Python 3.12.14 usado. Motor y pruebas: biblioteca estándar. Análisis y figuras: NumPy 2.3.5 y Matplotlib 3.10.8 (`requirements-analysis.txt`). Colab no fue probado. Se necesita espacio para las trazas CSV completas; los archivos comprimidos son considerablemente menores.

Desde la raíz de este proyecto:

```bash
python3 -m pip install -r requirements-analysis.txt
python3 -m unittest discover -s tests -v
python3 scripts/run_refined.py --out outputs/refined_400 --prepare-only
python3 scripts/run_refined.py --out outputs/refined_400 --workers 4
python3 scripts/analyze_refined.py --source outputs/refined_400 --out outputs/analysis
python3 scripts/plot_refined.py --analysis outputs/analysis --out outputs/figures
python3 scripts/pack_traces.py --source outputs/refined_400 --out outputs/trace_archives --workers 2
```

Espere a que la ejecución termine y verifique las exportaciones antes de empaquetar. Si el entorno sincroniza archivos mientras se están escribiendo, use para `--out` un directorio de trabajo estable y traslade los archivos terminados al finalizar. El destino de análisis debe ser nuevo o vacío.

El ejecutor reanuda únicamente corridas completadas cuyo manifiesto y plan coinciden. No sobrescribe una corrida incompleta o alterada: debe inspeccionarse y ponerse aparte antes de repetirla con la misma semilla. Nunca se cambian semillas para sustituir resultados desfavorables.

## Reproducir desde las trazas entregadas

Los diez archivos `Article_8_Refinado_Trazas_rNNN_NNN_v0.2.0.tar.xz` contienen diez bloques emparejados cada uno: 40 corridas y todos sus registros. Extraiga los diez en un mismo directorio vacío, por ejemplo `outputs/refined_400`. Comparten copias idénticas de cinco archivos de metadatos experimentales y tienen carpetas de corridas distintas. No se descartan ni muestrean registros agente–período. Después ejecute el análisis y las figuras con los comandos anteriores.

En Python 3.12 puede extraerse cada archivo de esta forma:

```python
from pathlib import Path
import tarfile

destination = Path('outputs/refined_400')
destination.mkdir(parents=True, exist_ok=True)
for path in sorted(Path('descargas').glob('Article_8_Refinado_Trazas_*.tar.xz')):
    with tarfile.open(path, 'r:xz') as archive:
        archive.extractall(destination, filter='data')
```

`CountConfig(**config_exportada)` reconstruye el conteo exacto; el CLI M6 original no admite `exact_promoters`. Las marcas de tiempo y duración pueden variar entre ejecuciones. No se promete identidad binaria entre versiones de Python, plataformas o compresores.

## Qué significa cada resultado

- `sustained_v02`: alguna ventana de seis períodos con compras en todos ellos, al menos 24 compras totales, presión neta positiva en todos, stock promotor estable o creciente y positivo, reposición endógena en la segunda mitad, compras en al menos dos comunidades y cero entradas externas.
- `m6_takeoff`: definición original con crecimiento relativo 1,25. Se conserva como comparación; no se reescribe el piloto v0.1.
- `m6_terminal_class`, `m6_collapse` y `m6_saturation`: clasificaciones M6 originales. No son categorías terminales revisadas a partir de v0.2.
- `positive_process_absorbed`: no hay promotores activos, experiencias pendientes ni activaciones positivas pendientes; se informa independientemente de la etiqueta terminal.
- `reach10_time`…`reach75_time`: primer período en que las compras nuevas llegan al porcentaje correspondiente de los 480 susceptibles. Valor vacío: no se alcanzó al 120.
- `cumulative_incidence.csv`: siempre 100 réplicas como denominador, incluidos los casos sin evento. Los tiempos resumidos solo entre éxitos están identificados como condicionales.
- `discrete_frontier.csv`: menor conteo probado que cruza una frecuencia objetivo. Sin interpolación ni extrapolación; los intervalos Wilson son por condición, no de un umbral continuo.

La sensibilidad reclasifica las mismas trayectorias: nueve variantes v0.2 y tres variantes M6, 4.800 evaluaciones en total. No son 4.800 simulaciones adicionales.

Consulte `docs/Article_8_Refinado_Diseno_v0.2.0.md` para decisiones fijadas antes de ejecutar y la distinción entre aceleración, persistencia y volumen. El informe describe incertidumbre, casos discrepantes y siguientes experimentos. Los cambios de energía, WOM negativo, calidad y distribución no se ensayan en este refinamiento basal.
