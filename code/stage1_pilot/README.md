# Article 8 — Piloto v0.1.0

Modelo congelado **M6 0.6.0-m6**. Piloto exploratorio de 150 corridas, con diez réplicas emparejadas y 15 escenarios. Se conservan las 150 trayectorias originales de 60 períodos y, por separado, seis seguimientos diagnósticos a 120 períodos. Estos seguimientos no son réplicas independientes adicionales.

## Entorno

Motor y ejecución: Python 3.12.14, biblioteca estándar. Análisis bootstrap: NumPy 2.3.5. Figuras: Matplotlib 3.10.8. Esas son las versiones usadas, sin afirmar reproducción byte a byte entre versiones distintas. Colab no fue probado.

## Reproducir

Desde esta carpeta, con destinos nuevos o vacíos:

```bash
python -m unittest discover -s tests -v
python scripts/run_pilot.py --out outputs/pilot_150 --workers 4
python scripts/analyze_pilot.py --source outputs/pilot_150 --out outputs/analysis
python scripts/check_horizon.py --pilot outputs/pilot_150 --analysis outputs/analysis --out outputs/horizon_followup
python scripts/plot_pilot.py --analysis outputs/analysis --out outputs/figures
python scripts/package_traces.py --pilot outputs/pilot_150 --followup outputs/horizon_followup --out outputs/trace_archives
```

El ejecutor comprueba las huellas de la copia M6 en model/. El plan y el archivo de escenarios quedan fijados antes de ejecutar. Si se repite el comando sobre el mismo destino, solo se reutilizan resultados completos cuyo plan y manifiesto coinciden; los resultados originales no se sobrescriben. --workers modifica únicamente la concurrencia.

Las tres pruebas nuevas cubren la matriz de escenarios, emparejamiento y protección del plan. La suite M6 de 229 pruebas, ya superada, se conserva dentro de model/tests. No es necesario repetirla para analizar este piloto sin modificar el motor.

## Diseño

110 corridas: once proporciones iniciales de promotores entre 0 % y 30 %, energía 0,6, distribución repartida. 40 corridas: proporción 15 %, energías 0,3/0,9 y distribución repartida/concentrada. N = 600, seis comunidades, C0 = 120, WOM negativo habilitado, peso 1, calidad 0,7, 60 períodos. Solo cambia la energía de la cohorte inicial; los nuevos promotores mantienen energía 0,6.

Semillas maestras 810001–810010. Todos los escenarios de cada réplica comparten entorno y sorteos indexados. Las semillas del experimento principal deberán ser nuevas. El diseño completo está en docs/Article_8_Piloto_Diseno_v0.1.0.md y en design/design.json.

## Salidas

- Traces r01–r10: quince escenarios completos por archivo, con red, estados individuales, eventos, energía, genealogía, cohortes, indicadores y clasificación.
- Seguimiento 120: seis trayectorias completas adicionales en horizonte, con comparación exacta de sus primeros 60 períodos y estados individuales.
- Resultados: resúmenes por corrida y escenario; diferencias emparejadas; 1.200 evaluaciones de clasificación; cohortes iniciales; series compactas; controles y diseño.
- Figuras: cuatro gráficos en PNG, SVG y PDF.

Las tablas separan despegue histórico de estado terminal. Saturación y colapso son reglas operativas, no validación empírica. La etiqueta en evolución es residual y puede coexistir con ausencia de actividad al cierre; no implica crecimiento actual.

Las estimaciones son exploratorias: diez réplicas por condición. Los intervalos Wilson son marginales por condición; los intervalos bootstrap de diferencias conservan pares de réplica, usan 20.000 remuestras y no corrigen comparaciones múltiples. Un intervalo bootstrap degenerado para una diferencia binaria constante no demuestra certeza poblacional.

No se mezclan los seis seguimientos con los resultados originales al período 60. El informe documenta por qué conviene refinar el barrido inferior, revisar sensibilidad de clasificación y fijar un horizonte común antes de ampliar los experimentos.
