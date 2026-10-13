# Article 8 — Energía y WOM negativo alrededor de uno y dos promotores

Diseño v0.3.0, 27 de septiembre de 2026. Simulación teórica en Python. Fijado antes de ejecutar las nuevas condiciones; no constituye preinscripción externa.

## Pregunta y diseño

¿Cómo cambian la difusión sostenida y las compras cuando se modifica la energía inicial de uno o dos promotores y el peso de la influencia negativa?

Factorial completo: P0={1,2} × energía positiva inicial E0={0,3;0,6;0,9} × peso negativo λ={0;1;2}. Dieciocho condiciones, cien réplicas por condición, 120 períodos: **1.800 corridas nuevas**, semillas 830001–830100. No se agregan al piloto previo. Cien entornos independientes; dentro de cada entorno se comparan las dieciocho condiciones.

N=600, seis comunidades, clientes iniciales C0=120 y susceptibles iniciales S0=480. Los conteos P0 equivalen a 0,8333 % y 1,6667 % de C0. Se conservan seis detractores iniciales, energía negativa inicial 0,6, calidad 0,7 y selección repartida. Las reglas M6 0.6.0-m6 permanecen congeladas. `CountConfig` conserva conteos enteros exactos.

## Manipulaciones e interpretación

E0 cambia únicamente la energía de los promotores iniciales. Los promotores formados por experiencia comienzan con energía 0,6 en todas las condiciones. No se modifican el desgaste, el costo por recomendación, las oportunidades ni la calidad.

λ modifica dos términos ya existentes: la penalización negativa del logit de compra y la sustracción de capacidad negativa al calcular presión neta. Se mantiene activo el mecanismo de mensajes y formación de detractores en las dieciocho condiciones. λ=0 neutraliza su influencia; **no elimina sus eventos ni equivale a apagar el módulo**. λ=1 es la referencia y λ=2 duplica el peso, sin duplicar necesariamente mensajes o detractores. Energía de detractores nuevos=0,6.

Esta primera variación de WOM negativo estudia su peso de influencia. No identifica efectos separados de cantidad de detractores, energía negativa, duración del recuerdo o propensión a quejarse. Puesto que λ también entra en presión neta, sus efectos sobre la clasificación pueden incluir un cambio directo del indicador: se analizan asimismo compras, reproducción y trayectorias.

Cada réplica comparte red, rasgos, clientes iniciales, detractores y sorteos indexados. La selección de promotores no depende de E0 ni λ y el promotor de P1 pertenece al conjunto P2. La política repartida ubica al segundo promotor en otra comunidad: el contraste P2−P1 incluye conjuntamente cantidad y cobertura.

## Criterio principal y resultados

Se conserva difusión sostenida v0.2: una ventana completa de seis períodos debe registrar compras en todos ellos, al menos 24 compras en total (5 % de S0), presión neta positiva en cada período, stock promotor final positivo y no menor al inicio, al menos un promotor nuevo durante la segunda mitad y activaciones que cubran sus salidas, compras en dos o más comunidades y ninguna incorporación externa.

El resultado es la presencia histórica de al menos una ventana válida hasta t=120. No implica persistencia perpetua ni actividad al cierre. El tiempo de confirmación es el final de la primera ventana válida. Se conservan sin cambios las etiquetas terminales y de colapso M6 como resultados distintos.

Resultados adicionales: compras nuevas al 120 y al 60, compras tardías, promotores y detractores nuevos, eventos, reproducción de la cohorte inicial, tiempo al 10/25/50/75 % de S0, y ausencia de fuentes positivas al cierre. Las medianas de tiempo entre casos con evento se identifican como condicionales; las curvas de incidencia usan cien como denominador.

Sensibilidad: las mismas nueve definiciones v0.2 (duración 4/6/8 × volumen 12/24/48 compras) y M6 con crecimiento 1,10/1,25/1,50. Son reclasificaciones de las mismas trayectorias. No se escogerá posteriormente la definición más favorable.

## Comparaciones e incertidumbre

Se reportan dieciocho proporciones con intervalos Wilson del 95 %. Se comparan P2−P1 para cada E0,λ; E0=0,6−0,3 y 0,9−0,6 para cada P0,λ; λ=1−0 y 2−1 para cada P0,E0. Interacción extrema por P0: [Y(E0=0,9,λ=2)−Y(0,3,2)]−[Y(0,9,0)−Y(0,3,0)]. Compras y evento binario usan diferencias dentro de la misma semilla, 20.000 remuestras de las cien parejas/bloques y semilla base 88301. Intervalos exploratorios puntuales, sin ajuste de multiplicidad; los intervalos degenerados no equivalen a certeza.

La frontera se limita a los dos conteos ensayados, para frecuencias objetivo de 25/50/75 %. Si uno ya cruza, el mínimo dentro de la grilla es uno y la frontera completa permanece censurada por abajo. Si ninguno cruza, no se identifica el umbral dentro de {1,2}; no se afirma automáticamente que tres basten. Se muestran por separado cruces de la frecuencia y del límite Wilson inferior. No se interpola una proporción universal.

## Verificación, trazabilidad y almacenamiento

Antes de las corridas: comprobar parámetros, equivalencia basal con v0.2, emparejamiento, anidamiento, serialización, cuadrícula completa y archivado/reanudación con detección de corrupción. Se conservan las catorce pruebas del adaptador y observador v0.2. Las huellas del motor deben coincidir con los 61 archivos M6.

En cada corrida: invariantes del motor; reconciliación independiente de cohortes; conteo de mensajes; 600 × 121=72.600 filas agente–período; clasificación; exportación y huellas. La exportación cerrada se comprime sin pérdidas y se leen íntegramente todos sus miembros para contrastar huellas y secuencia de cada agente/período antes de liberar la copia intermedia. No se descartan trazas ni se muestrean períodos.

Las corridas se ejecutan fuera del directorio sincronizado para prevenir truncamientos durante la escritura. Cada archivo por corrida conserva configuración, red, estados, mensajes, compras, experiencias, activaciones, energía, genealogía, observación y clasificación. Se reúnen en bloques de tres réplicas (54 corridas por bloque, salvo la réplica final), con índice de huellas. Código, plan previo, datos procesados, figuras e informe acompañan las trazas. Los tiempos/huellas de archivos con metadatos temporales pueden variar al reproducir; las trayectorias determinísticas deben coincidir.

Nota logística durante la ejecución: el límite de transferencia a Drive es 100 MiB por archivo. Se cambió el empaquetado de cinco a tres réplicas; no se modificaron parámetros, semillas, corridas ni resultados. Los bloques finales son 34.
