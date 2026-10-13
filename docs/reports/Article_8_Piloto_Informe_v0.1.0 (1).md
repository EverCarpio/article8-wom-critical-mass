# Article 8 — Informe del piloto v0.1.0

**Fecha:** 27 de septiembre de 2026. **Modelo:** M6 0.6.0-m6, Python 3.12.14. **Alcance:** 150 corridas exploratorias de 60 períodos, más seis seguimientos diagnósticos separados hasta 120 períodos.

## Resultado y decisión

El piloto está completo: **150 de 150 corridas**, sin fallos de invariantes ni de integridad de las exportaciones. Se conservaron 5.490.000 registros agente–período, eventos, genealogía y configuraciones. Las reglas del modelo y su clasificación permanecieron iguales a M6.

El resultado principal es una transición más temprana que la región del 15 %: **tres promotores entre 120 clientes iniciales (2,5 %) generaron despegue en las diez réplicas base**. Eso no identifica un umbral universal, ni demuestra que tres sean el mínimo: no se ensayaron uno y dos promotores. La grilla actual no resuelve la transición entre cero y tres.

Antes del experimento principal recomiendo un piloto refinado con uno y dos promotores, una revisión explícita de la clasificación y un horizonte común de 120 períodos. No se debe aumentar automáticamente el número de réplicas de la misma grilla sin atender estos tres resultados.

## Diseño y ejecución

El diseño se fijó antes de ejecutar: 11 proporciones × 10 réplicas = 110 corridas base, más cuatro contrastes de energía/distribución al 15 % × 10 réplicas = 40 corridas. N = 600; seis comunidades; C0 = 120; seis detractores iniciales; calidad 0,7; energía base 0,6; WOM negativo habilitado, lambda = 1. La energía de nuevos promotores permanece en 0,6.

Las semillas maestras 810001–810010 son identificadores enteros. Cada réplica comparte la red, rasgos, clientes, detractores y sorteos indexados entre sus 15 escenarios. Las huellas del entorno confirmaron ese emparejamiento en las diez réplicas. Las semillas no reutilizan las verificaciones M5/M6.

El motor conserva los 61 archivos de la entrega M6 conforme a su manifiesto. La suite previa de 229 pruebas permaneció como control de versión; se añadieron tres pruebas de orquestación para matriz, emparejamiento y reanudación. Cada corrida ejecutó sus validaciones, incluyendo **27.000 reconciliaciones de ventanas de cohorte** en el total del piloto.

La ejecución usó cuatro procesos y tomó 155.0 segundos de cómputo transcurrido en este entorno, sin incluir análisis, compresión o transferencia. La mediana de duración registrada por corrida fue 3.87 segundos; las duraciones en concurrencia no deben sumarse como tiempo de pared.

## Barrido base

La proporción usa clientes iniciales como denominador. Las compras son nuevas adquisiciones entre los 480 susceptibles iniciales; no incluyen los 120 clientes de partida. Despegue significa que se confirmó alguna ventana durante la trayectoria, aunque después se agotara la actividad.

| p0 | Promotores iniciales | Despegues | IC Wilson 95 % | Compras nuevas medias | Mínimo–máximo |
|---|---:|---:|---:|---:|---:|
| 0 % | 0 | 0/10 | 0.0–27.8 % | 0.0 | 0–0 |
| 2.5 % | 3 | 10/10 | 72.2–100.0 % | 407.8 | 351–426 |
| 5 % | 6 | 10/10 | 72.2–100.0 % | 421.0 | 383–442 |
| 7.5 % | 9 | 10/10 | 72.2–100.0 % | 425.9 | 404–446 |
| 10 % | 12 | 10/10 | 72.2–100.0 % | 426.5 | 406–447 |
| 12.5 % | 15 | 10/10 | 72.2–100.0 % | 434.8 | 421–461 |
| 15 % | 18 | 10/10 | 72.2–100.0 % | 435.4 | 416–464 |
| 17.5 % | 21 | 10/10 | 72.2–100.0 % | 429.7 | 410–439 |
| 20 % | 24 | 10/10 | 72.2–100.0 % | 434.1 | 421–452 |
| 25 % | 30 | 9/10 | 59.6–98.2 % | 440.5 | 425–453 |
| 30 % | 36 | 8/10 | 49.0–94.3 % | 441.8 | 430–456 |

Los intervalos son marginales por condición, no bandas simultáneas ni incertidumbre de una frontera estimada. Diez éxitos de diez dan un límite inferior cercano a 72,2 %, no certeza de éxito. Los resultados de condiciones distintas están emparejados por réplica.

La regla exploratoria de menor proporción ensayada que alcanza frecuencias de 0,25, 0,50 o 0,75 devuelve **2,5 %** para los tres criterios. Es el límite inferior positivo del barrido, no una estimación precisa del mínimo. El resultado queda condicionado a esta red, rasgos, calidad, energías y ecuación de compra.

Las frecuencias no son monótonas: 20 % registra 10/10, 25 % registra 9/10 y 30 % registra 8/10. A la vez, las compras medias aumentan de 434,1 a 440,5 y 441,8. Por tanto, una menor frecuencia de la etiqueta no equivale automáticamente a menor difusión comercial.

## Auditoría de alta difusión sin etiqueta de despegue

Cinco corridas con promotores no confirman despegue pese a terminar con entre 415 y 434 compras nuevas. En su primera ventana, todos los criterios salvo crecimiento relativo son verdaderos. No aparece una ventana posterior que cumpla el conjunto completo.

| Corrida | Compras al 60 | Compras t1–t3 | Compras t4–t6 | Razón entre mitades |
|---|---:|---:|---:|---:|
| r01_B10 | 430 | 72 | 80 | 1.111 |
| r07_E9_distributed | 415 | 61 | 56 | 0.918 |
| r08_B09 | 425 | 78 | 83 | 1.064 |
| r08_B10 | 434 | 90 | 95 | 1.056 |
| r08_E9_concentrated | 430 | 54 | 63 | 1.167 |

El criterio exige razón ≥ 1,25. Esta auditoría muestra que una trayectoria con muchas compras tempranas puede no recibir la etiqueta. Es una limitación de la definición operativa para comparar cohortes grandes, no evidencia de que agregar promotores perjudique las ventas. No se cambió el criterio después de observar los datos.

Antes del experimento principal conviene contrastar la definición actual con medidas continuas de adquisición y tiempo para alcanzar un nivel predefinido del mercado. Cualquier definición nueva debe documentarse y analizarse separadamente; no sustituir retroactivamente los resultados M6.

## Energía y distribución al 15 %

| Energía inicial | Distribución | Despegues | Compras medias | Mínimo–máximo |
|---|---|---:|---:|---:|
| 0.6 | Repartida | 10/10 | 435.4 | 416–464 |
| 0.3 | Repartida | 10/10 | 419.4 | 381–439 |
| 0.3 | Concentrada | 10/10 | 425.2 | 366–451 |
| 0.9 | Repartida | 9/10 | 434.8 | 403–454 |
| 0.9 | Concentrada | 9/10 | 435.3 | 426–447 |

En distribución repartida, reducir energía de 0,6 a 0,3 se asocia con **16 compras menos por réplica en promedio**; el intervalo bootstrap emparejado del 95 % es −27,8 a −5,0. Aumentarla de 0,6 a 0,9 arroja una diferencia media de −0,6, con intervalo −11,4 a 10,5.

Concentrar frente a repartir produce diferencias medias de +5,8 compras con energía 0,3 y +0,5 con energía 0,9. Sus intervalos incluyen cero. Estas diez réplicas no sustentan una ventaja general de concentración o distribución. Cambiar ubicación también altera grado y alcance; se entregan esos componentes iniciales.

Los intervalos se obtuvieron con 20.000 remuestras de las diferencias por réplica, preservando los pares. Son exploratorios, sin ajuste por comparaciones múltiples. En diferencias binarias constantes, un intervalo bootstrap degenerado no implica certeza poblacional. No existe una condición 0,6 concentrada en este piloto: no se presenta como un factorial completo 3 × 2.

## Historia y estados terminales

En el conjunto diseñado de 150 corridas se observaron **135 despegues históricos, seis colapsos históricos y 68 saturaciones**. Estas banderas pueden coexistir; no suman categorías mutuamente excluyentes. Tampoco se interpreta 135/150 como probabilidad de un mercado general, porque combina escenarios elegidos deliberadamente.

Los estados terminales son: 68 saturaciones; 61 en evolución; cinco colapsos; 14 sin despegue confirmado; y dos con seguimiento insuficiente. Una trayectoria con colapso histórico terminó posteriormente saturada, por lo que los seis colapsos históricos no equivalen a los cinco terminales.

La etiqueta en evolución es residual: hubo despegue, ya no está vigente y no se satisface otra regla terminal. **No significa actividad o crecimiento actual.** Puede existir una trayectoria absorbida en la franja de mercado restante que las reglas no fuerzan a saturación o colapso. Conviene conservar un indicador independiente de actividad y revisar el nombre de esa categoría en una adenda futura.

## Sensibilidad de clasificación

Se aplicaron ocho configuraciones M6 a las mismas 150 trayectorias: **1.200 evaluaciones**, sin nuevas simulaciones ni cambios de decisiones.

| Configuración | Despegues históricos | Colapsos históricos | Saturaciones |
|---|---:|---:|---:|
| Base | 135 | 6 | 68 |
| Duración 4 | 130 | 4 | 68 |
| Duración 8 | 133 | 4 | 68 |
| Crecimiento 1,10 | 138 | 6 | 68 |
| Crecimiento 1,50 | 90 | 4 | 68 |
| Sin requisito W > 0 | 135 | 6 | 68 |
| Límites 5 % / 15 % | 135 | 39 | 4 |
| Límites 15 % / 30 % | 135 | 0 | 131 |

La incidencia de colapso depende fuertemente del mercado remanente requerido: cambia de seis a 39 con el par (5 %,15 %) y a cero con (15 %,30 %). El requisito de crecimiento 1,50 reduce los despegues de 135 a 90. Omitir W > 0 no cambia esos conteos en este conjunto; eso no prueba irrelevancia general de la presión negativa.

Las diferencias obligan a presentar sensibilidad junto con los resultados principales. No hay base para escoger la regla que maximice el despegue o produzca el umbral esperado del 15 %.

## Seguimiento diagnóstico a 120 períodos

Al período 60, 144 corridas no tenían promotores activos, experiencias pendientes ni activaciones positivas pendientes: futuras compras ya no pueden producirse bajo las reglas del modelo mínimo. Seis conservaban alguna de esas fuentes. Para resolver este riesgo concreto se repitieron exclusivamente esas seis con horizonte 120, manteniendo la versión y todos los parámetros restantes.

Los primeros 60 períodos y los 36.600 registros individuales correspondientes de cada seguimiento coincidieron exactamente con sus originales: **12 comparaciones de prefijos satisfactorias**. Los resultados originales no se reemplazaron y las seis extensiones no se cuentan como nuevas réplicas independientes.

| Corrida | Compras 60 | Compras 120 | Adicionales | Estado 60 | Estado 120 |
|---|---:|---:|---:|---|---|
| r01_B01 | 414 | 414 | 0 | evolving | evolving |
| r06_B01 | 351 | 392 | 41 | insufficient_followup | collapse |
| r07_B01 | 403 | 403 | 0 | evolving | evolving |
| r07_B02 | 419 | 420 | 1 | evolving | evolving |
| r07_E3_concentrated | 366 | 404 | 38 | insufficient_followup | evolving |
| r10_B01 | 403 | 404 | 1 | collapse | collapse |

Se observaron **81 compras adicionales**: cuatro seguimientos agregaron compras y dos no. No cambiaron las banderas de despegue. Una corrida confirmó un colapso adicional; todas quedaron sin fuentes de nuevas compras al período 120. Esto justifica fijar un horizonte común de 120 en el siguiente diseño, sin mezclar los resultados de 60 y 120 como si fueran observaciones equivalentes.

## Entregables y reproducción

Se entregan código completo, diseño, tablas procesadas, figuras en PNG/SVG/PDF, diez archivos de trazas (uno por réplica, quince escenarios cada uno) y un archivo separado para los seis seguimientos. Las trazas incluyen estados individuales de todos los agentes y períodos. Cada exportación tiene manifiesto de huellas; los ZIP pasaron comprobación de integridad.

El paquete de resultados contiene resúmenes por corrida y escenario, diferencias emparejadas, sensibilidad, cohortes iniciales, series compactas, auditoría de las cinco corridas sin etiqueta, manifiesto experimental y comparación de horizontes. El índice de archivos incluye las huellas y enlaces de recuperación.

El código incluye una copia íntegra y congelada de M6. Desde article8_pilot_v0.1.0:

```bash
python scripts/run_pilot.py --out outputs/pilot_150 --workers 4
python scripts/analyze_pilot.py --source outputs/pilot_150 --out outputs/analysis
python scripts/check_horizon.py --pilot outputs/pilot_150 --analysis outputs/analysis --out outputs/horizon_followup
python scripts/plot_pilot.py --analysis outputs/analysis --out outputs/figures
```

Motor: biblioteca estándar. Análisis/figuras: NumPy 2.3.5 y Matplotlib 3.10.8. Los destinos de análisis deben ser nuevos o vacíos. Las marcas de tiempo y duración varían al repetir; no se afirma identidad byte a byte entre runtimes distintos. Colab no fue probado.

## Siguiente decisión antes del experimento principal

1. Refinar entre cero y tres promotores iniciales: añadir uno y dos (aproximadamente 0,83 % y 1,67 % de C0), con réplicas nuevas y contrastes informativos de energía/WOM negativo.
2. Fijar 120 períodos como horizonte común y documentarlo como cambio de diseño, conservando la referencia de 60.
3. Revisar la interpretación de crecimiento relativo y de la categoría residual, manteniendo resultados continuos y sensibilidad. Una revisión se registra como nueva versión; no se modifica este piloto.
4. Después fijar las condiciones principales y al menos 100 réplicas por condición. No ejecutar todavía un factorial grande alrededor del 15 % por inercia.

Ya pueden redactarse métodos y resultados preliminares del piloto. Para el borrador completo del artículo faltan el refinamiento, el experimento principal, la sensibilidad sustantiva y la revisión de teoría/tesis. Ningún resultado aquí es validación empírica ni recomendación universal para empresas reales.
