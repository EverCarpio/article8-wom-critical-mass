# Article 8 — Informe del piloto refinado v0.2.0

Fecha: 27 de septiembre de 2026. Alcance: simulación teórica en Python, sin datos empíricos. **400 corridas nuevas de 120 períodos**, 100 réplicas por condición y 100 entornos emparejados.

## Resultado y alcance

Se completaron las cuatro condiciones con 0, 1, 2 y 3 promotores iniciales. El porcentaje usa los **120 clientes iniciales**, no las 600 personas de la población. Las compras nuevas se producen entre los 480 susceptibles iniciales. Las cifras de este informe pertenecen exclusivamente a estas 400 corridas; las 150 del piloto anterior y sus seis seguimientos permanecen separados.

| P0 | % de C0 | v0.2 / 100 | IC 95 % v0.2 | M6 / 100 | Compras: media | Mediana | Mín.–máx. |
|---|---|---|---|---|---|---|---|
| 0 | 0.000 | 0 | 0.0–3.7 % | 0 | 0.00 | 0.0 | 0–0 |
| 1 | 0.833 | 83 | 74.5–89.1 % | 84 | 348.59 | 414.5 | 1–454 |
| 2 | 1.667 | 100 | 96.3–100.0 % | 100 | 419.40 | 421.0 | 367–454 |
| 3 | 2.500 | 100 | 96.3–100.0 % | 100 | 422.09 | 424.0 | 369–451 |

**Hallazgo central:** un solo promotor produjo difusión sostenida en 83/100 réplicas, frente a 100/100 con dos y con tres. El IC Wilson del 95 % para un promotor es 74,45–89,11 %: incluye una probabilidad de 75 %, por lo que el cruce observado de ese nivel conserva incertidumbre. Para dos y tres el intervalo es 96,30–100 %; cien éxitos observados no garantizan éxito universal.

Con un promotor existe una dispersión considerable entre corridas: la media de compras es 348,59 y la mediana 414,5. El promedio combina cascadas amplias con trayectorias de poca difusión. Con dos y tres se reducen los resultados de muy baja adquisición en estas semillas.

Los intervalos Wilson son marginales por condición, no bandas simultáneas ni intervalos de un umbral continuo. El criterio principal es difusión sostenida v0.2. M6 se conserva como referencia de aceleración y reposición. Cualquier mínimo observado está condicionado al entorno basal y a la política de selección repartida.

## Diseño y revisión previa del despegue

Se fijaron 100 semillas nuevas, 820001–820100, y cuatro conteos por semilla. Se mantienen N=600, seis comunidades, C0=120, seis detractores iniciales, energías iniciales 0,6, calidad 0,7 y WOM negativo activo con peso 1. Los promotores nuevos conservan energía 0,6. Red, rasgos, clientes, detractores y sorteos indexados se emparejan dentro de cada réplica; los conjuntos de promotores están anidados.

El adaptador `CountConfig` permite introducir uno y dos promotores como enteros exactos. Evita el problema de representar 1/120 y 2/120 mediante decimales finitos sin redondear personas. El motor M6 y sus reglas de compra, experiencia, contactos, formación, energía y fatiga permanecen intactos.

La revisión utiliza el diagnóstico del piloto anterior y se fijó antes de observar estas nuevas trayectorias. **No es una preinscripción externa**. La huella del plan es `8379eeb9074402a056ce47181a67fc5474f66daf8806944be2aa505537d98790`; se entrega el registro temporal local previo a la ejecución.

M6 exige que las compras de la segunda mitad de una ventana de seis períodos superen en al menos 25 % a las de la primera. Esa razón puede dejar sin etiqueta una expansión inicialmente rápida. La definición revisada separa la persistencia y el volumen de la aceleración relativa.

**Difusión sostenida v0.2** exige simultáneamente, dentro de seis períodos consecutivos completos: compras en cada período; al menos 24 compras en total (5 % de los 480 susceptibles iniciales); presión neta positiva en cada período; stock promotor final positivo y no menor que al comienzo; al menos un promotor nuevo en la segunda mitad y activaciones que cubran sus salidas; compras en dos o más comunidades; y ausencia de entradas externas.

El umbral de 24 es operativo y exploratorio. No se escogió después de observar estas 400 corridas. Una trayectoria estable que se reproduce puede calificar sin acelerar; una expansión pequeña que acelera puede calificar bajo M6 y no bajo v0.2. Ninguno de los criterios es una ampliación automática del otro. La persistencia observada en seis períodos **no significa crecimiento perpetuo**.

## Diferencias entre uno, dos y tres promotores

| Contraste | Δ compras media | IC bootstrap 95 % | Pares con menos compras |
|---|---|---|---|
| P1-P0 | 348.59 | 317.10 a 377.51 | 0 |
| P2-P1 | 70.81 | 41.55 a 102.82 | 41 |
| P3-P2 | 2.69 | -1.17 a 6.48 | 40 |
| P3-P1 | 73.50 | 44.59 a 104.83 | 32 |

Pasar de uno a dos se asocia con **70,81 compras adicionales en promedio** (IC 95 %: 41,55 a 102,82) y 17 puntos porcentuales más de difusión sostenida. La mediana de la diferencia de compras es solo cinco: la ganancia media recoge especialmente la prevención de trayectorias con poca difusión. En 41 de las 100 parejas, agregar el segundo promotor produjo menos compras al 120, aun cuando mejoró el promedio y la frecuencia de despegue.

Pasar de dos a tres añade una media de **2,69 compras** (IC 95 %: −1,17 a 6,48); esta comparación no distingue con claridad una ganancia de volumen al 120. Sí se observa una llegada más temprana al 50 % del mercado: medianas de 30 frente a 35 períodos, descriptivas y con el nivel alcanzado en las 100 corridas de ambos grupos.

Cada contraste conserva las 100 parejas de red y semilla. Los intervalos percentiles usan 20.000 remuestras de bloques y semillas 88201–88204. Son exploratorios, sin ajuste por comparaciones múltiples. Las diferencias binarias de clasificación y sus intervalos también están en `paired_summary.csv`; un intervalo bootstrap degenerado no demuestra certeza.

Con la selección repartida, agregar el segundo o tercer promotor incorpora otra comunidad. Los resultados estiman ese cambio conjunto de cantidad y cobertura bajo la política especificada. **No identifican por separado el efecto de cantidad y el de ubicación**. Tampoco requieren que cada réplica produzca más compras al agregar un promotor.

## Desacuerdos y sensibilidad de clasificación

Hubo **1 desacuerdos entre M6 y v0.2** en el conjunto diseñado de 400 corridas.

| P0 | Ambos criterios | Solo v0.2 | Solo M6 | Ninguno |
|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 100 |
| 1 | 83 | 0 | 1 | 16 |
| 2 | 100 | 0 | 0 | 0 |
| 3 | 100 | 0 | 0 | 0 |

El único desacuerdo es `r098_P1`: termina con 54 compras nuevas; M6 confirma despegue y v0.2 no. La coincidencia de presencia del evento no implica coincidencia de su fecha: con un promotor las medianas de confirmación entre los eventos observados son 15 períodos para M6 y 23 para v0.2; con dos, 12 y 16; con tres, 11 y 12,5. Las medianas usan el subconjunto de eventos de cada definición, no una estimación emparejada de diferencias temporales.

`classification_disagreements.csv` identifica cada caso, compras finales y tiempos de confirmación. Los conteos históricos pueden coexistir con saturación o cese posterior de actividad. Las categorías terminales, el colapso y la saturación siguen siendo las de M6; no se presentan como una nueva clasificación terminal derivada de v0.2.

| Definición | P0=0 | P0=1 | P0=2 | P0=3 |
|---|---|---|---|---|
| d4_f025 | 0 | 84 | 100 | 100 |
| d4_f050 | 0 | 83 | 100 | 100 |
| d4_f100 | 0 | 81 | 97 | 99 |
| d6_f025 | 0 | 84 | 100 | 100 |
| d6_f050 | 0 | 83 | 100 | 100 |
| d6_f100 | 0 | 83 | 100 | 100 |
| d8_f025 | 0 | 83 | 100 | 100 |
| d8_f050 | 0 | 83 | 100 | 100 |
| d8_f100 | 0 | 83 | 100 | 100 |
| M6 | 0 | 84 | 100 | 100 |
| M6_growth110 | 0 | 84 | 100 | 100 |
| M6_growth150 | 0 | 84 | 100 | 100 |

En `d6_f050`, d6 significa seis períodos y f050 significa el 5 % del mercado susceptible inicial adquirido **dentro de la ventana**. f025 y f100 corresponden a 12 y 48 compras. Los volúmenes no se reescalan con la duración. Las nueve variantes v0.2 y las tres M6 producen **4.800 evaluaciones de clasificación sobre las mismas 400 trayectorias**, no nuevas simulaciones. Las conclusiones deben considerar la matriz completa; no se elige posteriormente la fila más favorable.

Las nueve variantes v0.2 producen 81–84 eventos con un promotor, 97–100 con dos y 99–100 con tres. La comparación basal es bastante estable en este rango de definiciones. Los tres factores de crecimiento M6 mantienen los mismos conteos, lo que no demuestra insensibilidad general del modelo fuera de estas condiciones.

## Horizonte y tiempos de difusión

| P0 | Compras medias t60 | Compras medias t120 | Corridas con compras t61–120 | Sin fuentes de compras al cierre |
|---|---|---|---|---|
| 0 | 0.00 | 0.00 | 0 | 100 |
| 1 | 310.67 | 348.59 | 52 | 99 |
| 2 | 407.79 | 419.40 | 49 | 100 |
| 3 | 420.83 | 422.09 | 19 | 100 |

Entre los períodos 61 y 120 se registraron **5079 compras adicionales en 120 corridas**. Al cierre, 399/400 carecían de promotores activos, experiencias pendientes y activaciones positivas pendientes. Esta condición de ausencia de futuras fuentes de compras se mide separadamente de la etiqueta terminal M6.

Corridas que aún conservan alguna de esas fuentes al 120: **r005_P1**. Se mantiene el horizonte común de 120 fijado para este diseño; una trayectoria abierta no se declara extinguida ni se extiende selectivamente para mejorar una comparación.

En `r005_P1` se registran 319 compras al 120, frente a 34 al 60, y aún quedan 15 promotores activos, siete experiencias pendientes y una activación positiva pendiente. Las 319 son compras al horizonte fijado, no el tamaño definitivo de esa cascada.

| P0 | Alcanzan 10 % | Alcanzan 25 % | Alcanzan 50 % | Alcanzan 75 % | Mediana t50 entre quienes lo alcanzan |
|---|---|---|---|---|---|
| 0 | 0/100 | 0/100 | 0/100 | 0/100 | No alcanzado |
| 1 | 84/100 | 83/100 | 83/100 | 82/100 | 41 |
| 2 | 100/100 | 100/100 | 100/100 | 100/100 | 35.0 |
| 3 | 100/100 | 100/100 | 100/100 | 100/100 | 30.0 |

El tiempo a alcanzar un porcentaje se cuenta desde t=0. Las medianas de tiempo de la tabla se calculan solo entre quienes alcanzan ese nivel y se identifican como condicionales. Las curvas de incidencia acumulada mantienen siempre 100 réplicas como denominador y conservan como censurados al 120 los casos sin evento; no se eliminan fracasos para dibujar trayectorias aparentemente más rápidas.

## Frontera discreta e incertidumbre

| Criterio | Frecuencia objetivo | Menor P0 ensayado | Menor P0 cuyo límite Wilson inferior supera el objetivo |
|---|---|---|---|
| sustained_v02 | 25 % | 1 | 1 |
| sustained_v02 | 50 % | 1 | 1 |
| sustained_v02 | 75 % | 1 | 2 |
| m6_takeoff | 25 % | 1 | 1 |
| m6_takeoff | 50 % | 1 | 1 |
| m6_takeoff | 75 % | 1 | 1 |

El mínimo es únicamente el menor **conteo entero ensayado** que cruza la frecuencia indicada. No se interpola entre cero y uno ni se estima un porcentaje universal. La columna de límites inferiores ayuda a evaluar la incertidumbre de cada condición, pero no constituye un intervalo de confianza de una frontera ajustada. `discrete_frontier.csv` conserva también los límites superiores por condición.

La interpretación corresponde al escenario basal: estas corridas no identifican todavía una frontera condicionada por energía, intensidad del WOM negativo, calidad o estructura de la red. El resultado no se ajusta para reproducir el 15 % de la tesis. Tampoco es una recomendación porcentual validada para empresas reales.

## Verificación, integridad y reproducción

Pasaron **14 pruebas nuevas** de entrada por conteo, equivalencia con M6 para tres promotores, serialización, emparejamiento, integridad de trazas y trayectorias sintéticas para el criterio revisado. Los 61 archivos del motor coinciden con el manifiesto de M6, cuya suite de 229 pruebas se verificó en la etapa previa. No se presenta esa suite como una nueva ejecución en esta entrega.

Las 400 corridas pasaron invariantes y las exportaciones finales fueron verificadas. Se conservaron **29,040,000 registros agente–período**, 144,000 reconciliaciones independientes de ventanas de cohorte y las trazas de eventos, decisiones y genealogía. Cada archivo comprimido se leyó y contrastó íntegramente con las huellas de los archivos originales, sin muestrear agentes o períodos.

Durante la comprobación de exportaciones se detectaron nueve copias de trazas incompletas. Se reconstruyeron con la misma semilla y las mismas reglas. Hubo además una repetición al ajustar el lector de integridad al nombre del campo `period`: **10 reconstrucciones en total**, todas con resultados idénticos y 29 archivos determinísticos coincidentes con el manifiesto original. Se entregan los detalles en `export_recovery.json`. Estas reconstrucciones no son réplicas adicionales ni reemplazos seleccionados según el resultado.

Tiempo de la ejecución original registrado: 1172.7 segundos con cuatro procesos, sin sumar duraciones concurrentes. No incluye análisis, recuperación de exportaciones, compresión o transferencia. Python 3.12.14; NumPy y Matplotlib se fijan en el archivo de dependencias. Consulte `README.md` para reconstrucción desde código o desde las trazas completas.

## Alcance de la próxima etapa

El siguiente experimento debe concentrarse alrededor de **uno y dos promotores**, variando energía y WOM negativo, con una referencia de tres y controles apropiados. Esto permitirá evaluar condiciones que desplazan la probabilidad de éxito, porque el escenario basal ya presenta frecuencias altas con conteos muy pequeños. Posteriormente deben contrastarse ubicación, calidad y fatiga. No hay fundamento para volver por defecto a un factorial centrado en 15 % ni para declarar universales los porcentajes bajos de este piloto.

Los métodos y estos resultados ya pueden incorporarse a un borrador como experimentos basales. La frontera condicional completa y la sensibilidad sustantiva siguen pendientes.
