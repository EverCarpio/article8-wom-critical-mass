# Article 8 — M6: reproducción, reposición y clasificación

**Versión:** 0.6.0-m6. **Fecha:** 27 de septiembre de 2026. **Implementación:** Python, biblioteca estándar. Base: especificación mínima v0.1, secciones 11–13, adenda de Python y dinámica M5.

## Alcance

M6 observa las trayectorias de M5: no modifica estados, compras, atribuciones, eventos, energías ni sorteos. Los nueve módulos de dinámica, configuración, inicialización, red y validación conservan exactamente sus bytes de M5. Se añaden analysis.py y classification.py y se extienden exportación y CLI. La versión anterior se conserva.

El análisis admite corridas completas y parciales. Los stocks se observan al cierre: quien se desactiva en t ya no pertenece al stock activo del cierre t. Una activación seguida de desactivación en el mismo período cuenta en ambos flujos.

## Indicadores y seguimiento

Se conservan capacidades M+, M− y presión indicativa W. Se añaden proporciones nominal y activa entre clientes, proporción activa en el mercado, cambio neto, agotamiento del mercado inicialmente susceptible y cobertura comunitaria por mensajes y nuevas compras. Los clientes iniciales no cuentan como nuevas comunidades adquiridas.

Reposición = B_t / D_t, con nuevas activaciones positivas B y desactivaciones positivas D. Denominador cero produce **NA**, incluso cuando B > 0. Se conservan conteos y B − D; no se sustituye por cero o infinito.

Para una ventana [a,b], de longitud w:

| Medida | Numerador | Denominador | Disponible |
|---|---|---|---|
| R_ventana | Nuevas activaciones positivas entre a y b | Promotores activos al cierre de a−1 | Cierre b |
| R_cohorte | Hijos directos activados, con padre en ese stock y compra entre a y b | El mismo stock del cierre a−1 | Cierre b+2 |

Se calculan w = 3, 6 y 12; la principal es 6. Los hijos cuentan aunque el padre o ellos mismos se hayan desactivado al observar la ventana. Se excluyen nietos, detractores, potenciales sin activación y compras fuera de la ventana. La atribución es contable, no causal.

Las ventanas comienzan en cada período observado desde 1 hasta T. Si b > T, R_ventana queda censurada; si b+2 > T, R_cohorte queda censurada. Sus razones son NA, pero se exportan numeradores observados, límites, miembros, hijos y motivos. No se presume fracaso por falta de seguimiento.

En la serie temporal, reproduction_ratio es R_ventana de la ventana completa que termina en t. cohort_ratio_available corresponde a la ventana de compras que termina en t−2, cuyas fechas también se exportan. Ningún período usa activaciones futuras. R_ventana > 1 no demuestra por sí solo crecimiento: puede coexistir con numerosas salidas y con hijos de emisores ausentes del denominador.

## Reglas operativas

Las reglas provienen de la especificación anterior a estas verificaciones. Son convenciones del modelo, no umbrales empíricos.

**Despegue:** seis períodos; compras de la primera mitad ≥ 3 y segunda mitad ≥ 1,25 veces la primera; stock activo final ≥ inicial y > 0; segunda mitad con al menos una activación y entradas ≥ salidas; W > 0 cada período; compras en al menos dos comunidades; sin entradas externas. Se registran inicio y confirmación.

**Colapso:** seis períodos cuyo inicio es posterior a la primera confirmación de despegue. Compras sumadas ≤ 0,5 × 6 × la media positiva de los tres períodos previos; segunda mitad ≤ primera; stock final ≤ mitad del inicial, con inicial ≥ 1; W final ≤ 0 o M+ final ≤ mitad del máximo observado antes del inicio; U/U0 ≥ 0,20 toda la ventana. Reconoce caídas abruptas a cero y no atribuye automáticamente la causa al WOM negativo.

**Saturación:** U/U0 ≤ 0,10. **Meseta:** seis períodos por encima de ese límite, compras de la primera mitad ≥ 3, diferencia entre mitades ≤ 20 % de la primera y cambio absoluto del stock ≤ 20 % de max(stock inicial, 1).

**Pico temporal:** sin despegue confirmado, un bloque de tres períodos registra compras ≥ max(3, dos veces las del bloque previo); el bloque siguiente registra como máximo la mitad de las compras y la mitad del stock al cierre del pico; al final U/U0 > 0,10. Solo el bloque que comienza en 1 usa un bloque previo convencional de cero. Los demás requieren tres períodos previos observados. Se examinan inicios móviles.

**Sin despegue confirmado:** no se observó una ventana válida y no falta seguimiento para una señal identificada; no implica cero ventas ni imposibilidad futura. **En evolución:** hubo despegue, perdió vigencia y no corresponde otra etiqueta. **Seguimiento insuficiente:** horizonte menor que la duración requerida o señal incompleta al final.

La zona entre saturación y colapso no se fuerza a ninguna categoría. Las comparaciones inclusivas admiten tolerancia numérica de 1e−12; presión positiva y mercado por encima de saturación mantienen desigualdades estrictas.

## Historia y precedencia terminal

Se conservan banderas, primer inicio, primera confirmación y última confirmación de cada evento. Cada período usa exclusivamente su información disponible. Analizar un prefijo produce las mismas filas que el prefijo del análisis completo.

Orden terminal: saturación; colapso confirmado; meseta con ventana que termina en el período actual; despegue vigente; pico histórico sin despegue; seguimiento insuficiente; en evolución tras despegue antiguo; ausencia de despegue confirmado. El despegue está vigente si hubo confirmación en los últimos seis períodos, incluido el actual, sin categoría prioritaria. La vigencia cambia junto con la duración configurada.

Para concretar la precedencia de v0.1, el colapso conserva prioridad hasta una saturación posterior; no existe clase de recuperación. La meseta se evalúa al cierre actual y no se perpetúa porque haya ocurrido antes. El pico histórico se conserva si después ocurre despegue, pero deja de determinar el estado terminal.

La señal incompleta es conservadora: identifica una primera mitad con compras mínimas, actividad y presión admisibles; una caída parcial compatible con colapso tras despegue; o un bloque de pico pendiente de seguimiento. No predice confirmación. Las ventanas incompletas nunca tienen triggered=true. Una etiqueta prioritaria puede coexistir con seguimiento incompleto para otro evento.

takeoff_time_censored y collapse_time_censored indican falta de confirmación hasta el cierre, no ausencia permanente. El colapso se evalúa únicamente después del despegue. Estos campos no constituyen un análisis de supervivencia: en ese análisis futuro la saturación debe tratarse explícitamente como evento competitivo, no asumirse censura independiente.

## Configuración y salidas

configs/m6_analysis.json contiene todas las reglas. Se admiten duraciones pares y límites de mercado separados. La verificación examina duraciones 4 y 8, factores 1,10 y 1,50, variante sin exigir W > 0 y límites (0,05; 0,15) y (0,15; 0,30). Las ventanas de reproducción 3, 6 y 12 se calculan simultáneamente.

M6 añade analysis_config.json, analysis_summary.json, reproduction_windows.csv y classification_windows.csv. Enriquece system_period.csv y run_summary.json. La tabla de clasificación conserva criterios y estadísticas de cada ventana completa; las incompletas conservan fechas y censura. Se mantienen los archivos M5 de mensajes, decisiones, experiencia, energía y genealogía. JSON usa null y CSV vacío para NA.

Las cohortes y comunidades se reconstruyen a partir de eventos y estados con fechas, sin requerir historial individual. Omitir agent_period.csv no cambia indicadores. Las exportaciones rechazan carpetas no vacías e incluyen huellas SHA-256.

## Verificación y siguiente paso

Pasaron 229 pruebas: 184 anteriores y 45 nuevas. Ocho casos sintéticos cubren todas las etiquetas. Doce trayectorias de 60 períodos se analizaron con ocho configuraciones: 96 análisis, no 96 nuevas simulaciones. Se reconciliaron independientemente 2.160 ventanas de cohorte con los registros de activación y desactivación.

M6 cierra la medición y clasificación del modelo mínimo. Esta verificación no estima la frontera ni valida empíricamente el modelo. Sigue el piloto de la especificación: 110 corridas de proporciones más 40 contrastes de energía y distribución, **150 en total**, antes de los experimentos principales. Sincronización y recuperación permanecen aplazadas.
