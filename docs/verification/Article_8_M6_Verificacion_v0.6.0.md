# Article 8 — Verificación M6

**Versión:** 0.6.0-m6. **Fecha local:** 27 de septiembre de 2026, America/Bogota. **Runtime:** Python 3.12.14.

## Resultado

M6 integra reproducción por ventana y por cohorte, reposición, cobertura comunitaria y clasificación de trayectorias. Pasaron **229 pruebas**, sin fallos ni errores: 184 anteriores y 45 nuevas. Se verificaron ocho casos sintéticos, doce trayectorias de 60 períodos y 96 evaluaciones de clasificación sobre esas mismas trayectorias.

Se reconciliaron **2,160 ventanas de cohorte** con registros independientes de activación y desactivación. No se ejecutó el piloto de 150 corridas ni se estimó una frontera de masa crítica.

## Implementación y trazabilidad

La capa de análisis es determinista y no modifica M5. Los nueve módulos de dinámica, configuración, población, red y validación conservan exactamente sus huellas de M5; la evidencia se entrega en m5_core_regression.json. Las extensiones se limitan a observación, CLI, exportación, pruebas, configuración y documentación.

Reposición conserva conteos y diferencia neta; denominador cero produce NA. R_ventana cuenta entradas respecto al stock previo. R_cohorte cuenta hijos directos con compra dentro de la ventana y espera dos períodos adicionales. Nietos, detractores y activaciones bloqueadas no se cuentan como hijos activos. Las cohortes conservan miembros y descendientes para auditoría.

La serie temporal solo publica la reproducción genealógica cuando ha terminado su seguimiento. Se verificó que analizar una corrida parcial produce exactamente el prefijo correspondiente de los indicadores de la corrida completa. Ejecutar análisis entre pasos tampoco altera la dinámica posterior.

Cada ventana completa de clasificación exporta criterios booleanos y estadísticas. Las incompletas quedan censuradas y nunca se disparan. Se conservan fechas e historia además del estado terminal, diferenciando saturación de colapso posterior a despegue.

## Pruebas

| Módulo | Pruebas | Resultado |
|---|---:|---|
| M1: red y población | 42 | Pasan |
| M2: WOM positivo y compra | 31 | Pasan |
| M3: experiencia y promotores | 37 | Pasan |
| M4: energía y fatiga | 36 | Pasan |
| M5: WOM negativo y detractores | 38 | Pasan |
| M6: indicadores y clasificación | 45 | Pasan |
| **Total** | **229** | **0 fallos; 0 errores** |

M6 comprende cuatro pruebas de configuración y entradas; ocho de reproducción; 23 de clasificación; y diez de integración/exportación. Los casos cubren denominador cero con y sin nuevas entradas, maduración exactamente en b+2, padres e hijos ya inactivos, hijos frente a nietos, ventanas incompletas, límites inclusivos y presión estrictamente positiva.

Se comprueban despegue sin adelantar confirmación, requisitos de comunidades y formación endógena, exclusión de entradas externas, colapso posterior a despegue, caída abrupta a cero, zona intermedia de mercado, prioridad de saturación, conservación del historial, pico inicial, vigencia del despegue y seguimiento insuficiente. La interfaz rechaza parámetros inválidos y series inconsistentes.

Los ocho casos sintéticos entregan entrada, serie clasificada, ventanas y resultado esperado para: despegue, colapso, meseta, pico, ausencia de despegue, seguimiento corto, despegue antiguo sin etiqueta concluyente actual y saturación. Son trayectorias diseñadas para verificar reglas, no corridas empíricas ni evidencia de frecuencia de esos resultados.

La exportación se comprobó con y sin historial individual, horizonte cero, directorios no vacíos, celdas NA, huellas de integridad y configuraciones serializadas. Dos procesos con distintas semillas de hash de Python produjeron exportaciones idénticas.

## Doce trayectorias de verificación

Diseño: dos semillas enteras (20260925 y 20260926) × dos distribuciones × tres proporciones iniciales (0 %, 15 % y 30 %). N = 600, C0 = 120, seis comunidades, 60 períodos, energía 0,6, calidad 0,7, WOM negativo activo con peso 1. Las comparaciones comparten entorno y sorteos indexados por réplica. Estos identificadores de semilla no son fechas.

| Semilla | Distribución | p0 | Compras nuevas | Confirmación despegue | U/U0 final | Estado terminal |
|---|---|---:|---:|---:|---:|---|
| 20260925 | distributed | 0 % | 0 | — | 100.00 % | Sin despegue confirmado |
| 20260925 | distributed | 15 % | 445 | 6 | 7.29 % | Saturación |
| 20260925 | distributed | 30 % | 461 | 6 | 3.96 % | Saturación |
| 20260925 | concentrated | 0 % | 0 | — | 100.00 % | Sin despegue confirmado |
| 20260925 | concentrated | 15 % | 440 | 6 | 8.33 % | Saturación |
| 20260925 | concentrated | 30 % | 457 | 6 | 4.79 % | Saturación |
| 20260926 | distributed | 0 % | 0 | — | 100.00 % | Sin despegue confirmado |
| 20260926 | distributed | 15 % | 431 | 6 | 10.21 % | En evolución / sin clasificación concluyente actual |
| 20260926 | distributed | 30 % | 447 | 6 | 6.88 % | Saturación |
| 20260926 | concentrated | 0 % | 0 | — | 100.00 % | Sin despegue confirmado |
| 20260926 | concentrated | 15 % | 443 | 6 | 7.71 % | Saturación |
| 20260926 | concentrated | 30 % | 441 | 6 | 8.12 % | Saturación |

Las cuatro corridas sin promotores no generan compras ni despegue. Las ocho con promotores registran despegue bajo la regla base; siete terminan saturadas. Una conserva 49 de los 480 susceptibles iniciales (10,2083 %) y queda entre los límites operativos de saturación y colapso. El rótulo en evolución no significa que siga creciendo: es la categoría residual tras perder vigencia el despegue sin satisfacer otra regla terminal. No se observan colapsos en estas doce trayectorias; su detección se verifica mediante los casos sintéticos.

Este conjunto es demasiado reducido y deliberadamente seleccionado para estimar probabilidades o recomendar porcentajes. Que 15 % y 30 % despeguen aquí no identifica el menor porcentaje necesario ni un umbral universal.

## Sensibilidad diagnóstica de la clasificación

Las ocho configuraciones se aplicaron a las mismas doce trayectorias, sin repetir ni modificar sus decisiones. Son 96 análisis. En todas permanecen cuatro casos sin despegue correspondientes a p0 = 0.

| Configuración | Despegues históricos | Saturaciones terminales | En evolución | Colapsos |
|---|---:|---:|---:|---:|
| base | 8 | 7 | 1 | 0 |
| duration4 | 8 | 7 | 1 | 0 |
| duration8 | 8 | 7 | 1 | 0 |
| growth1_10 | 8 | 7 | 1 | 0 |
| growth1_50 | 6 | 7 | 1 | 0 |
| without_pressure | 8 | 7 | 1 | 0 |
| limits05_15 | 8 | 2 | 6 | 0 |
| limits15_30 | 8 | 8 | 0 | 0 |

Elevar el factor de crecimiento de 1,25 a 1,50 reduce los despegues detectados de ocho a seis. Cambiar el límite de saturación de 10 % a 5 % o 15 % altera cuántos cierres reciben esa etiqueta. Esto muestra dependencia de las convenciones operativas; no invalida la implementación ni se corrige cambiando parámetros para obtener el resultado esperado. Los resultados finales deben reportarse junto con esta sensibilidad.

Las ventanas genealógicas 3, 6 y 12 se calcularon para cada trayectoria. Las 2.160 reconciliaciones incluyen ventanas completas, censuradas y sin denominador; no se presentan todas como estimaciones completas.

## Reproducción y archivos

Desde article8_m6, después de descomprimir:

```bash
python -m unittest discover -s tests -v
python scripts/verify_m6.py --out outputs/verification_reproduction
python -m article8 --mode mixed --analysis --config configs/m6_baseline.json --analysis-config configs/m6_analysis.json --out outputs/example_reproduction
```

Los destinos deben ser nuevos o vacíos. El paquete de código incluye configuraciones, documentación, suite y verificadores. El paquete de evidencias incluye resultados individuales de pruebas, casos sintéticos, doce resúmenes, 96 clasificaciones, 2.160 reconciliaciones verificadas, dos trazas completas al 15 %, configuración de sensibilidad y huellas de código. Las tablas de cohortes detalladas acompañan las dos trazas; el resumen registra el conteo verificado para las doce corridas.

Las trazas completas incorporan red y población iniciales, mensajes y decisiones de ambos signos, experiencias, activaciones, energía, genealogía, historial individual, estado final, indicadores, ventanas y resúmenes de análisis. Ambos manifiestos de exportación y los dos ZIP pasaron comprobación de integridad.

| Entregable | Bytes | SHA-256 |
|---|---:|---|
| Article_8_M6_Python_v0.6.0.zip | 148165 | `009e816b0e3997dab70d5c13be1f292c013c01454a6a72d7ebbb55415cdf916a` |
| Article_8_M6_Evidencias_v0.6.0.zip | 4592112 | `30aaa99c0ab0411cd5e18ff90408b4327287e5223426666a1bbbbbe36a1ce3ce` |
| Article_8_M6_Alcance_v0.6.0.md | 8467 | `8693de137fe95e3dbc3887a4bcbdb6ae17585cbea1c034f4575fb531250d7ce1` |

Registro UTC de verificación: 2026-09-27T12:42:41.385210+00:00. Solo se afirma reproducción byte a byte dentro del runtime probado. Colab no se verificó.

## Próximo paso

Ejecutar el piloto definido en v0.1: 11 proporciones × 10 réplicas = 110 corridas, más 40 contrastes al 15 % con energías 0,3/0,9 y distribución concentrada/repartida. Total **150 corridas**. Revisar transición, clasificación, tiempos, truncamiento y sensibilidad antes de los experimentos principales.

La revisión conceptual y la comparación con la tesis siguen siendo necesarias para el manuscrito. M6 no constituye validación empírica ni justifica recomendar un porcentaje a empresas reales. Los indicadores de evento no son por sí solos un análisis de supervivencia: una saturación posterior al despegue debe tratarse explícitamente como evento competitivo si se analiza tiempo a colapso.
