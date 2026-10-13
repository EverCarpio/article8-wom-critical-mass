# Article 8 — M6: reproducción y clasificación de difusión

Versión **0.6.0-m6**, Python con biblioteca estándar. Probado en Python 3.12.14; requiere Python 3.11 o posterior. Incluye M1–M5 y añade una capa de observación sin modificar sus trayectorias.

## Ejecución

Descomprima y ejecute desde `article8_m6`:

```bash
python -m article8 --mode mixed --analysis --config configs/m6_baseline.json --analysis-config configs/m6_analysis.json --out outputs/base
python -m unittest discover -s tests -v
python scripts/verify_m6.py --out outputs/verification_reproduction
```

Cada destino debe ser nuevo o vacío. `--analysis` requiere `--mode mixed`; `--analysis-config` requiere `--analysis`. Sin ellas se conserva el comportamiento previo. `--no-agent-history` reduce archivos sin cambiar modelo ni indicadores. El horizonte se cambia con `--periods`.

Los parámetros están en `configs/m6_*.json`. La CLI admite configuraciones separadas de dinámica, experiencia, energía positiva, WOM negativo y análisis. `--negative-off` deshabilita el mecanismo negativo y `--negative-weight` cambia su peso. Los valores omitidos conservan los valores base.

## Indicadores

- Reposición: nuevas activaciones / desactivaciones positivas. Denominador cero produce NA.
- R_ventana: activaciones en la ventana / stock activo antes de ella.
- R_cohorte: hijos directos activados de ese stock, con compras dentro de la ventana; seguimiento adicional de dos períodos. Se conservan censura, miembros e hijos.
- Proporciones nominal y activa, cambio neto, agotamiento del mercado y cobertura comunitaria.
- Despegue, colapso posterior al despegue, saturación, meseta, pico, ausencia de despegue observado, evolución y seguimiento insuficiente.

La historia se conserva aunque cambie el estado terminal. Falta de confirmación al cierre no demuestra fracaso permanente. Saturación no equivale a colapso. La atribución es contable y los índices de capacidad no son fuerzas adicionales de compra.

Las reglas y precisiones operativas están en `docs/Article_8_M6_Alcance_v0.6.0.md`. La especificación v0.1 incluida es histórica; la implementación vigente es Python y conserva las adendas de cada módulo.

## API

```python
from article8.analysis import AnalysisConfig, analyze_simulation
from article8.mixed import MixedSimulation
from article8.export import export_analyzed_simulation

sim = MixedSimulation().run()
analysis = analyze_simulation(sim, AnalysisConfig())
print(analysis.summary)
export_analyzed_simulation(sim, 'outputs/api_run')
```

`analysis.system` contiene las series, `analysis.reproduction` las ventanas y cohortes, y `analysis.classification_windows` la auditoría de criterios. El objeto sim no se modifica. R_cohorte aparece en las series solo desde el período en que termina el seguimiento; no se usa información futura.

## Exportación

Se mantienen red, configuración y población iniciales; mensajes, decisiones, compras, experiencias, activaciones, genealogía, energía, desactivaciones y estado final. `system_period.csv` y `run_summary.json` incluyen ahora indicadores y clasificación.

| Archivo nuevo | Contenido |
|---|---|
| analysis_config.json | Parámetros de medición y clasificación |
| analysis_summary.json | Estado terminal, historia, fechas y seguimiento |
| reproduction_windows.csv | Numeradores, denominadores, miembros, hijos y censura |
| classification_windows.csv | Criterios y estadísticas por ventana; fecha de confirmación |

`manifest.json` registra versión y SHA-256. CSV vacío / JSON null representan valores no definidos. No se exportan NaN ni infinito. Los conjuntos se serializan como listas JSON ordenadas.

## Verificación

Pasaron **229 pruebas**, incluidas 45 de M6. El verificador añade ocho casos sintéticos y doce trayectorias de 60 períodos: dos semillas × dos distribuciones × tres proporciones (0 %, 15 % y 30 %). Reconcilia 2.160 ventanas de cohortes con registros de activación y desactivación.

Evalúa ocho configuraciones de clasificación sobre esas doce trayectorias: **96 análisis**, no 96 simulaciones adicionales. Dos ejemplos al 15 % incluyen trazas completas. Se prueban límites, retrasos, denominadores cero, seguimiento truncado, hijos frente a nietos, independencia del historial, análisis entre pasos, invariancia de prefijos y reproducción entre procesos con distintas semillas de hash.

Esta verificación no sustituye el piloto de **150 corridas** de la especificación ni estima una frontera. El siguiente paso es ejecutar el piloto y revisar la zona de transición sin ajustar parámetros para forzar el 15 %.

La reproducción byte a byte se limita al mismo runtime. Colab no se verificó. Los verificadores M1–M5 se conservan para auditoría histórica; la verificación vigente es `verify_m6.py`.
