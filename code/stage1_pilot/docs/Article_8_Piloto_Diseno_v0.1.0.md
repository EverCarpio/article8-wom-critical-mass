# Article 8 — Diseño del piloto v0.1.0

Fecha: 27 de septiembre de 2026. Modelo congelado: **0.6.0-m6**, Python. Diseño derivado de la sección 14 de la especificación mínima v0.1. El archivo design.json y su huella se registran antes de ejecutar las corridas.

## Matriz

| Bloque | Condiciones | Réplicas por condición | Corridas |
|---|---|---:|---:|
| Barrido base | p0 = 0; 2,5; 5; 7,5; 10; 12,5; 15; 17,5; 20; 25; 30 %. Energía inicial 0,6; distribución repartida | 10 | 110 |
| Contrastes al 15 % | Energía inicial 0,3 y 0,9 × distribución repartida y concentrada | 10 | 40 |
| Total | 15 escenarios | 10 | 150 |

p0 usa como denominador los 120 clientes iniciales, no las 600 personas del mercado. Seis comunidades de 100 personas; seis detractores iniciales; horizonte de 60 períodos más t=0. WOM negativo habilitado, peso 1; calidad 0,7. Los demás parámetros y las reglas de clasificación son los de M6.

La energía modificada es exclusivamente la de la cohorte inicial de promotores. La energía de nuevos promotores y de detractores permanece en 0,6. No se añaden promotores externos ni se activa recuperación. No se introduce una condición de energía 0,6 concentrada porque no pertenece a las 40 corridas adicionales definidas; la distribución se contrasta directamente a energías 0,3 y 0,9.

## Réplicas, comparabilidad y ejecución

Semillas maestras enteras 810001–810010, una por réplica. Son identificadores, no fechas. No reutilizan las semillas de verificación M5/M6. Los experimentos principales deberán usar identificadores nuevos.

Los 15 escenarios de una réplica comparten red, rasgos, clientes iniciales, detractores reservados y ordenaciones de selección. Los sorteos dinámicos se indexan por agente, período, mecanismo y oportunidad. Cambiar ubicación puede alterar grado y alcance inicial; se registran ambos. Las comparaciones son emparejadas por réplica, sin suponer que dos escenarios sean muestras independientes.

Cada corrida conserva todos los registros: población inicial, red, estados individuales por período, mensajes, compras, experiencias, activaciones, energía, genealogía, series y ventanas de análisis. Las corridas terminadas se guardan con identificadores únicos; una reanudación comprueba su plan y huellas antes de reutilizarlas.

## Controles

Se verifican las 61 huellas de archivos de la entrega M6, cuya suite de 229 pruebas ya pasó. Tres pruebas nuevas verifican la matriz, el emparejamiento de semillas, la ausencia de duplicados y la protección de reanudación. No se modifica el motor.

Cada corrida ejecuta las validaciones M5, la clasificación M6 y la reconciliación independiente de cohortes con eventos. Debe conservar 600 × 61 = 36.600 registros individuales. Se comprueba la integridad de los archivos exportados y la huella común del entorno dentro de cada réplica.

## Análisis fijado

El resultado principal es **haber confirmado despegue en algún momento**, conservando el estado terminal por separado. Se resumen compras, nuevas activaciones, tiempos, saturación y colapso posterior al despegue. Las diez réplicas por condición son exploratorias.

Se calculan proporciones observadas de despegue con intervalos Wilson del 95 % por condición y estadísticas descriptivas de compras. Las diferencias de energía y distribución se calculan dentro de cada réplica; sus intervalos exploratorios se obtienen por bootstrap emparejado, conservando juntas las observaciones de cada réplica.

La frontera exploratoria es la menor proporción ensayada cuya frecuencia de despegue alcanza 0,25, 0,50 o 0,75. Se reportan todas las condiciones y posibles resultados no monótonos. No se interpola un umbral continuo ni se presenta un porcentaje universal.

Se aplican ocho reglas de clasificación ya disponibles a las mismas trayectorias: base; duración 4; duración 8; crecimiento 1,10; crecimiento 1,50; sin requisito W positivo; límites de mercado (0,05; 0,15); y (0,15; 0,30). Son 1.200 evaluaciones de clasificación, no nuevas simulaciones ni cambios de la dinámica.

Se revisa si al cierre persisten promotores activos, experiencias pendientes o activaciones positivas pendientes. La ausencia de esas tres fuentes identifica absorción de futuras compras en el modelo mínimo, aunque una etiqueta temporal quede sin conclusión. No se modifica el horizonte de las 150 corridas después de observar resultados.

## Decisiones posteriores

El piloto puede identificar una región informativa o mostrar que no la hay. Sus resultados orientan el experimento principal y la sensibilidad; no prueban el 15 % ni validan empíricamente los supuestos. Todo cambio posterior de reglas o parámetros requiere una versión nueva y no se mezcla con este piloto como si fueran réplicas equivalentes.
