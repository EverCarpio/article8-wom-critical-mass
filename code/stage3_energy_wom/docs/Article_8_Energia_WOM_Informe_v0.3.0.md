# Article 8 — Energía inicial y WOM negativo, v0.3.0

Fecha: 27 de septiembre de 2026. Simulación teórica en Python. **1.800 corridas nuevas: 18 condiciones × 100 réplicas, con 120 períodos por corrida.**

## Lectura de los resultados

Con WOM negativo de referencia (λ=1), la difusión sostenida fue 69/80/84 % con un promotor y 84/95/97 % con dos, al variar E0 entre 0,3/0,6/0,9. El segundo promotor mejora la frecuencia en las nueve combinaciones de energía y peso: 11–15 puntos porcentuales. Estas son frecuencias simuladas, no probabilidades universales.

En la referencia E0=0,6, λ=1, pasar de uno a dos añade 15 puntos porcentuales de difusión sostenida (IC bootstrap 95 %: 8–22) y 61,77 compras medias (34,22–91,95). La mediana de la diferencia de compras es 3,5; 36/100 parejas registran menos compras con dos. La mejora del promedio no implica que todas las cascadas crezcan más.

Elevar E0 de 0,3 a 0,6 con λ=1 añade 11 puntos porcentuales en ambos conteos: IC 1–21 con un promotor y 3–19 con dos. En cambio, el incremento de 0,6 a 0,9 produce diferencias de 4 puntos (−5 a 13) y 2 puntos (−3 a 7): estos intervalos no distinguen claramente una mejora adicional. La separación entre medias y medianas muestra la mezcla de cascadas amplias y trayectorias de poca adquisición.

El peso negativo produce cambios pequeños en la clasificación dentro del rango ensayado. Al pasar de λ=0 a 1, la frecuencia baja uno o dos puntos con un promotor y permanece igual con dos. Entre λ=1 y 2, la clasificación es idéntica en las 600 parejas correspondientes; las compras sí varían. En E0=0,6, el cambio medio de compras es −0,35 con un promotor (IC −0,73 a 0,11) y −0,70 con dos (−1,88 a 0,27). Esto no demuestra irrelevancia general del WOM negativo: se fijaron cantidad y energía de detractores, calidad y retención de memoria.

Para observar al menos 75 % de difusión bajo el criterio principal, el menor conteo ensayado es dos con E0=0,3 y uno con E0=0,6 o 0,9. Si se exige que el límite Wilson inferior también alcance 75 %, con E0=0,6 se requieren dos dentro de esta grilla; con E0=0,9 ya cruza uno. Son cruces puntuales condicionados, no una frontera continua ni una garantía. Ese cruce del límite inferior no se mantiene en todas las definiciones: con un promotor, E0=0,9 y λ=1, las nueve variantes producen 78–84 eventos. La sensibilidad completa aparece más abajo.

La nueva referencia da 80/100 y 95/100, frente a 83/100 y 100/100 del piloto refinado previo. Son lotes de semillas distintos y el motor es idéntico; no se mezclan como si fueran la misma muestra. La incertidumbre Monte Carlo acompaña cada resultado.

## Diseño y alcance

Se cruzaron uno o dos promotores iniciales, energía positiva inicial de 0,3/0,6/0,9 y peso negativo λ=0/1/2. Los cien entornos nuevos usan semillas 830001–830100, emparejadas en las dieciocho celdas. Las corridas de los pilotos previos no entran en los promedios ni en los intervalos de esta entrega.

N=600, seis comunidades, C0=120, S0=480 y seis detractores iniciales. La calidad es 0,7. Se mantiene selección repartida y energía negativa inicial y endógena 0,6. E0 modifica solamente los promotores iniciales; los nuevos promotores conservan energía 0,6. P0=1 y P0=2 equivalen a 0,8333 % y 1,6667 % de C0, respectivamente.

**λ=0 neutraliza la influencia negativa; conserva mensajes negativos y formación de detractores.** λ=1 es la referencia y λ=2 duplica el peso en la penalización de compra y en la presión neta. Este experimento no varía el número inicial ni la energía de los detractores. Tampoco equivale a comparar ausencia/presencia del módulo negativo.

La política repartida hace que el segundo promotor ocupe otra comunidad. El efecto P2−P1 incluye conjuntamente el aumento de cantidad y de cobertura; no separa ambos mecanismos.

## Resultado principal y volumen de compras

Se conserva difusión sostenida v0.2. Una ventana completa de seis períodos debe tener compras en cada período, al menos 24 compras totales, presión neta positiva siempre, stock final de promotores positivo y no menor al inicial, nacimientos que cubran salidas durante la segunda mitad con al menos un nacimiento, compras en dos o más comunidades y ninguna entrada externa. Se registra la presencia histórica de al menos una ventana hasta t=120.

La etiqueta significa persistencia durante una ventana finita, no crecimiento perpetuo. Como λ también afecta la presión usada por el clasificador, se informa el volumen de compras como resultado independiente. Los intervalos Wilson del 95 % son puntuales, sin corrección por multiplicidad.

| P0 | E0 | λ | Sostenida /100 | IC 95 % | Compras: media | Mediana | M6 /100 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.3 | 0 | 70 | 60.4–78.1 % | 295.39 | 410.0 | 70 |
| 1 | 0.3 | 1 | 69 | 59.4–77.2 % | 291.22 | 409.0 | 69 |
| 1 | 0.3 | 2 | 69 | 59.4–77.2 % | 291.15 | 409.0 | 69 |
| 1 | 0.6 | 0 | 81 | 72.2–87.5 % | 341.90 | 419.0 | 82 |
| 1 | 0.6 | 1 | 80 | 71.1–86.7 % | 338.01 | 418.5 | 80 |
| 1 | 0.6 | 2 | 80 | 71.1–86.7 % | 337.66 | 417.5 | 80 |
| 1 | 0.9 | 0 | 86 | 77.9–91.5 % | 363.63 | 419.0 | 87 |
| 1 | 0.9 | 1 | 84 | 75.6–89.9 % | 355.58 | 419.5 | 85 |
| 1 | 0.9 | 2 | 84 | 75.6–89.9 % | 354.92 | 418.0 | 85 |
| 2 | 0.3 | 0 | 84 | 75.6–89.9 % | 354.49 | 417.0 | 84 |
| 2 | 0.3 | 1 | 84 | 75.6–89.9 % | 354.85 | 417.5 | 84 |
| 2 | 0.3 | 2 | 84 | 75.6–89.9 % | 354.32 | 417.0 | 84 |
| 2 | 0.6 | 0 | 95 | 88.8–97.8 % | 399.66 | 420.0 | 95 |
| 2 | 0.6 | 1 | 95 | 88.8–97.8 % | 399.78 | 420.0 | 95 |
| 2 | 0.6 | 2 | 95 | 88.8–97.8 % | 399.08 | 419.0 | 95 |
| 2 | 0.9 | 0 | 97 | 91.5–99.0 % | 409.88 | 422.0 | 97 |
| 2 | 0.9 | 1 | 97 | 91.5–99.0 % | 409.56 | 423.0 | 97 |
| 2 | 0.9 | 2 | 97 | 91.5–99.0 % | 409.01 | 422.0 | 97 |

## Efecto emparejado del segundo promotor

Cada diferencia compara dos corridas del mismo entorno. Los intervalos percentiles se calculan con 20.000 remuestras de las cien parejas. La tabla conserva también las parejas en que el segundo promotor produjo menos compras: un efecto medio no implica monotonicidad en todas las trayectorias.

| Contraste | Δ compras | IC 95 % | Δ sostenida (pp) | IC 95 % (pp) | Pares con menos compras |
| --- | --- | --- | --- | --- | --- |
| P2-P1_E0.3_W0.0 | 59.10 | 32.09 a 88.84 | +14.0 | +8.0 a +21.0 | 34 |
| P2-P1_E0.3_W1.0 | 63.63 | 35.62 a 94.02 | +15.0 | +8.0 a +22.0 | 34 |
| P2-P1_E0.3_W2.0 | 63.17 | 35.08 a 94.06 | +15.0 | +8.0 a +22.0 | 33 |
| P2-P1_E0.6_W0.0 | 57.76 | 31.14 a 86.81 | +14.0 | +8.0 a +21.0 | 37 |
| P2-P1_E0.6_W1.0 | 61.77 | 34.22 a 91.95 | +15.0 | +8.0 a +22.0 | 36 |
| P2-P1_E0.6_W2.0 | 61.42 | 33.74 a 91.96 | +15.0 | +8.0 a +22.0 | 40 |
| P2-P1_E0.9_W0.0 | 46.25 | 22.20 a 72.68 | +11.0 | +5.0 a +17.0 | 41 |
| P2-P1_E0.9_W1.0 | 53.98 | 28.65 a 82.23 | +13.0 | +7.0 a +20.0 | 37 |
| P2-P1_E0.9_W2.0 | 54.09 | 28.67 a 82.75 | +13.0 | +7.0 a +20.0 | 39 |

## Efectos de energía y de peso negativo

Las diferencias de energía usan 0,6−0,3 y 0,9−0,6, manteniendo P0 y λ. Las de peso negativo usan 1−0 y 2−1, manteniendo P0 y E0. Un signo negativo representa reducción del resultado. No se promedian las celdas para ocultar heterogeneidad.

### Energía inicial

| Contraste | Δ compras | IC 95 % | Δ sostenida (pp) | IC 95 % (pp) |
| --- | --- | --- | --- | --- |
| E0.6-E0.3_P1_W0.0 | 46.51 | 4.72 a 89.01 | +11.0 | +1.0 a +21.0 |
| E0.9-E0.6_P1_W0.0 | 21.73 | -14.30 a 59.66 | +5.0 | -4.0 a +14.0 |
| E0.6-E0.3_P1_W1.0 | 46.79 | 5.87 a 89.20 | +11.0 | +1.0 a +21.0 |
| E0.9-E0.6_P1_W1.0 | 17.57 | -20.33 a 55.79 | +4.0 | -5.0 a +13.0 |
| E0.6-E0.3_P1_W2.0 | 46.51 | 5.40 a 88.25 | +11.0 | +1.0 a +21.0 |
| E0.9-E0.6_P1_W2.0 | 17.26 | -19.94 a 55.09 | +4.0 | -5.0 a +13.0 |
| E0.6-E0.3_P2_W0.0 | 45.17 | 12.95 a 78.27 | +11.0 | +3.0 a +19.0 |
| E0.9-E0.6_P2_W0.0 | 10.22 | -8.60 a 30.99 | +2.0 | -3.0 a +7.0 |
| E0.6-E0.3_P2_W1.0 | 44.93 | 12.93 a 78.23 | +11.0 | +3.0 a +19.0 |
| E0.9-E0.6_P2_W1.0 | 9.78 | -9.39 a 30.14 | +2.0 | -3.0 a +7.0 |
| E0.6-E0.3_P2_W2.0 | 44.76 | 12.66 a 77.87 | +11.0 | +3.0 a +19.0 |
| E0.9-E0.6_P2_W2.0 | 9.93 | -9.02 a 30.19 | +2.0 | -3.0 a +7.0 |

### Peso negativo

| Contraste | Δ compras | IC 95 % | Δ sostenida (pp) | IC 95 % (pp) |
| --- | --- | --- | --- | --- |
| W1.0-W0.0_P1_E0.3 | -4.17 | -12.57 a 0.20 | -1.0 | -3.0 a +0.0 |
| W2.0-W1.0_P1_E0.3 | -0.07 | -0.32 a 0.17 | +0.0 | +0.0 a +0.0 |
| W1.0-W0.0_P1_E0.6 | -3.89 | -12.57 a 0.81 | -1.0 | -3.0 a +0.0 |
| W2.0-W1.0_P1_E0.6 | -0.35 | -0.73 a 0.11 | +0.0 | +0.0 a +0.0 |
| W1.0-W0.0_P1_E0.9 | -8.05 | -20.05 a 0.11 | -2.0 | -5.0 a +0.0 |
| W2.0-W1.0_P1_E0.9 | -0.66 | -1.60 a 0.15 | +0.0 | +0.0 a +0.0 |
| W1.0-W0.0_P2_E0.3 | 0.36 | -0.48 a 1.26 | +0.0 | +0.0 a +0.0 |
| W2.0-W1.0_P2_E0.3 | -0.53 | -1.31 a -0.03 | +0.0 | +0.0 a +0.0 |
| W1.0-W0.0_P2_E0.6 | 0.12 | -0.79 a 0.96 | +0.0 | +0.0 a +0.0 |
| W2.0-W1.0_P2_E0.6 | -0.70 | -1.88 a 0.27 | +0.0 | +0.0 a +0.0 |
| W1.0-W0.0_P2_E0.9 | -0.32 | -1.11 a 0.48 | +0.0 | +0.0 a +0.0 |
| W2.0-W1.0_P2_E0.9 | -0.55 | -1.53 a 0.23 | +0.0 | +0.0 a +0.0 |

La interacción extrema se define como [Y(E0=0,9,λ=2)−Y(0,3,2)]−[Y(0,9,0)−Y(0,3,0)]. Mide cuánto cambia el efecto de elevar energía cuando se pasa del peso negativo cero al doble. La remuestra conserva las cuatro celdas del mismo entorno.

| P0 | Resultado | Interacción | IC 95 % |
| --- | --- | --- | --- |
| Energy_x_WOM_P1 | new_purchases | -4.47 | -12.97 a 0.22 |
| Energy_x_WOM_P1 | sustained_v02 | -1.00 | -3.00 a 0.00 |
| Energy_x_WOM_P2 | new_purchases | -0.70 | -2.51 a 1.01 |
| Energy_x_WOM_P2 | sustained_v02 | 0.00 | 0.00 a 0.00 |

Las interacciones del evento binario se expresan en puntos porcentuales. Todos los contrastes son exploratorios y sus intervalos no se ajustan por comparaciones múltiples. Un intervalo bootstrap de ancho cero refleja ausencia de variación en esta muestra; no demuestra certeza poblacional.

## Frontera discreta condicionada

La tabla siguiente muestra el menor conteo ensayado que alcanza una frecuencia observada de difusión sostenida del 75 %. La segunda columna de cruces aplica el mismo objetivo al límite inferior Wilson. Son dos resúmenes diferentes, no intervalos de confianza de un umbral ajustado.

| E0 | λ | Menor P0 ensayado ≥75 % | Menor P0 con límite inferior ≥75 % | Estado de la grilla |
| --- | --- | --- | --- | --- |
| 0.3 | 0 | 2 | 2 | Cruza en 2 |
| 0.3 | 1 | 2 | 2 | Cruza en 2 |
| 0.3 | 2 | 2 | 2 | Cruza en 2 |
| 0.6 | 0 | 1 | 2 | Ya cruza en 1 |
| 0.6 | 1 | 1 | 2 | Ya cruza en 1 |
| 0.6 | 2 | 1 | 2 | Ya cruza en 1 |
| 0.9 | 0 | 1 | 1 | Ya cruza en 1 |
| 0.9 | 1 | 1 | 1 | Ya cruza en 1 |
| 0.9 | 2 | 1 | 1 | Ya cruza en 1 |

Si uno cruza, solo se conoce el mínimo dentro de esta grilla: no se ensayó cero en este factorial. Si ninguno cruza, no se identifica el umbral dentro de {1,2}; no se concluye que tres basten. `discrete_frontier.csv` incluye además objetivos de 25 % y 50 % y el criterio M6. No se interpola ni se declara un porcentaje universal.

## Sensibilidad del criterio y seguimiento

Se realizaron 21,600 evaluaciones de clasificación sobre las mismas 1.800 trayectorias: nueve definiciones v0.2 y tres M6. Hubo 4 desacuerdos entre el criterio principal v0.2 y M6. No son simulaciones adicionales.

| P0 | E0 | λ | Sostenida principal /100 | Rango: nueve variantes /100 | Fuentes positivas abiertas al 120 |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.3 | 0 | 70 | 70–70 | 0 |
| 1 | 0.3 | 1 | 69 | 69–69 | 0 |
| 1 | 0.3 | 2 | 69 | 69–69 | 0 |
| 1 | 0.6 | 0 | 81 | 78–81 | 2 |
| 1 | 0.6 | 1 | 80 | 77–80 | 2 |
| 1 | 0.6 | 2 | 80 | 77–80 | 2 |
| 1 | 0.9 | 0 | 86 | 80–86 | 0 |
| 1 | 0.9 | 1 | 84 | 78–84 | 0 |
| 1 | 0.9 | 2 | 84 | 78–84 | 0 |
| 2 | 0.3 | 0 | 84 | 81–84 | 0 |
| 2 | 0.3 | 1 | 84 | 81–84 | 0 |
| 2 | 0.3 | 2 | 84 | 81–84 | 0 |
| 2 | 0.6 | 0 | 95 | 92–95 | 0 |
| 2 | 0.6 | 1 | 95 | 91–95 | 0 |
| 2 | 0.6 | 2 | 95 | 91–95 | 0 |
| 2 | 0.9 | 0 | 97 | 94–97 | 0 |
| 2 | 0.9 | 1 | 97 | 93–97 | 0 |
| 2 | 0.9 | 2 | 97 | 94–97 | 0 |

Después del período 60 se produjeron 48,384 compras adicionales en 834 corridas. Al 120 quedan 6 trayectorias con promotores activos, experiencias pendientes o activaciones positivas pendientes. No se extienden selectivamente. Sus compras finales son compras al horizonte común, no tamaños definitivos de cascada.

Las figuras de incidencia mantienen cien réplicas como denominador. Las medianas de tiempo del archivo `cell_summary.csv` son condicionales a observar el evento y se acompañan de sus conteos. Las etiquetas de colapso, saturación y clase terminal siguen siendo las de M6 y permanecen separadas del criterio histórico v0.2.

Clases terminales M6, acumuladas únicamente como inventario de este diseño: `{"collapse": 143, "evolving": 990, "insufficient_followup": 1, "no_confirmed_takeoff": 234, "saturation": 401, "temporary_spike": 31}`. Esta mezcla deliberada de condiciones no estima una probabilidad de mercado general.

## Reproducción de la cohorte inicial

El archivo `cohort_initial.csv` conserva por corrida las cohortes iniciales para ventanas 3/6/12, sus hijos directos y los cocientes observados. Se respeta el retraso hasta la activación; no se divide por cero ni se declara completa una ventana censurada. El resumen siguiente corresponde a la ventana de seis períodos, observada con el seguimiento necesario.

| P0 | E0 | λ | R de cohorte: media | Mediana | Réplicas con R≥1 |
| --- | --- | --- | --- | --- | --- |
| 1 | 0.3 | 0 | 0.60 | 0.00 | 49 |
| 1 | 0.3 | 1 | 0.58 | 0.00 | 47 |
| 1 | 0.3 | 2 | 0.58 | 0.00 | 47 |
| 1 | 0.6 | 0 | 1.26 | 1.00 | 67 |
| 1 | 0.6 | 1 | 1.24 | 1.00 | 67 |
| 1 | 0.6 | 2 | 1.24 | 1.00 | 67 |
| 1 | 0.9 | 0 | 1.70 | 2.00 | 75 |
| 1 | 0.9 | 1 | 1.68 | 2.00 | 74 |
| 1 | 0.9 | 2 | 1.68 | 2.00 | 74 |
| 2 | 0.3 | 0 | 0.56 | 0.50 | 33 |
| 2 | 0.3 | 1 | 0.54 | 0.50 | 31 |
| 2 | 0.3 | 2 | 0.54 | 0.50 | 31 |
| 2 | 0.6 | 0 | 1.10 | 1.00 | 69 |
| 2 | 0.6 | 1 | 1.09 | 1.00 | 67 |
| 2 | 0.6 | 2 | 1.09 | 1.00 | 67 |
| 2 | 0.9 | 0 | 1.60 | 1.50 | 85 |
| 2 | 0.9 | 1 | 1.59 | 1.50 | 85 |
| 2 | 0.9 | 2 | 1.59 | 1.50 | 85 |

## Verificación y reproducción

Pasaron 20 pruebas: seis del nuevo diseño y archivado, junto con las catorce previas del adaptador y observador v0.2. Una primera ejecución de la prueba de corrupción detectó correctamente el archivo truncado pero esperaba otro tipo de excepción; se corrigió la expectativa y la suite final pasó. No fue un fallo de una corrida experimental.

Los 61 archivos del motor coinciden con el manifiesto M6. Su suite de 229 pruebas corresponde a la verificación previa; no se presenta como una nueva ejecución. La condición basal E0=0,6, λ=1 se contrastó con el controlador anterior usando la misma semilla, sin diferencias en estados, eventos o historia de agentes.

Las 1.800 corridas pasaron invariantes, reconciliación de mensajes y 648,000 comprobaciones independientes de ventanas de cohorte. Se conservaron y verificaron 130,680,000 filas agente–período y 57,600 miembros de archivos por corrida. Cada traza se leyó completa, comprobando huellas y la secuencia de los 600 agentes en los 121 instantes. No se muestrearon períodos ni se descartaron eventos.

Cada corrida tiene un archivo TAR.XZ sin pérdida, leído y contrastado con su manifiesto antes de retirar la copia intermedia. Treinta y cuatro contenedores TAR reúnen tres réplicas completas cada uno (54 corridas), salvo el último con una réplica (18 corridas) y vuelven a verificar las huellas de todos los archivos contenidos. El almacenamiento modifica el empaquetado, no la simulación.

Huella del plan previo: `0ad8021f122d58024ca65fc3f625f61ac2f156eb4643f4606caf5f9c4c72093f`. Tiempo de la última invocación, incluyendo reanudación, archivado y comprobaciones: 1904.7 segundos con 8 procesos. Lapso desde la preparación inicial hasta la terminación: 3101.0 segundos, incluyendo la interrupción y la recuperación; no suma tiempos concurrentes. Python 3.12.14. Las figuras y el análisis se ejecutaron después; sus tiempos y las transferencias no se incluyen en esa cifra.

Consulte README para reproducir las corridas o reconstruir el análisis desde las trazas. Los archivos incluyen configuración, semillas, red, estados, eventos, compra, experiencia, energía, genealogía, observación, sensibilidad y manifiestos. No se modificaron las reglas M6 ni se recalibró el criterio tras ver resultados.

## Límites y siguiente etapa

Estos resultados evalúan dos conteos y tres niveles específicos de energía y peso negativo en un único tipo de red, calidad y política de colocación. No validan empíricamente una recomendación para empresas ni identifican una frontera completa. Para separar cantidad y ubicación se requiere un experimento de colocación; para ampliar WOM negativo, variar cantidad o energía de detractores de forma independiente. La calidad, fatiga y topología siguen pendientes como sensibilidad sustantiva. El diseño y los resultados presentes pueden incorporarse al primer borrador como un experimento factorial condicionado.

## Continuidad de la ejecución

El entorno se reinició durante el cálculo. Se preservaron y comprobaron 608 corridas cerradas antes de reanudar. Se aislaron tres directorios de exportación parcial y dos compresiones incompletas; se reconstruyeron las pendientes con las mismas semillas y el plan intacto. No se sustituyeron réplicas ni se seleccionaron resultados. `execution_interruption.json` conserva el registro. La cifra final sigue siendo 1.800 corridas únicas.
