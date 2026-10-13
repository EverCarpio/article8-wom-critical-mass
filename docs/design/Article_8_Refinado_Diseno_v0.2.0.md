# Article 8 — Diseño del piloto refinado v0.2.0

Fecha: 27 de septiembre de 2026. Documento fijado antes de las nuevas corridas. La revisión del criterio se informa por el piloto anterior de 150 corridas; no constituye una preinscripción externa ni una validación empírica.

## Objetivo y matriz

Resolver la transición entre cero y tres promotores y distinguir aceleración comercial de difusión sostenida en el modelo teórico.

| Promotores iniciales exactos | Porcentaje de los 120 clientes iniciales | Réplicas nuevas | Períodos |
|---:|---:|---:|---:|
| 0 | 0 % | 100 | 120 |
| 1 | 0,8333… % | 100 | 120 |
| 2 | 1,6667… % | 100 | 120 |
| 3 | 2,5 % | 100 | 120 |

Total: 400 corridas, 100 bloques emparejados. Se incluyen controles con cero promotores y una referencia con tres; no se reutilizan las diez semillas del piloto anterior como nuevas réplicas. Semillas maestras: 820001–820100. No se amplía el número de corridas según los resultados.

Se mantienen N=600, seis comunidades, C0=120, 480 susceptibles iniciales, seis detractores, energía inicial positiva y negativa 0,6, calidad 0,7, WOM negativo activo y peso 1. La energía de nuevos promotores permanece en 0,6. Todas las demás reglas M6, incluidas experiencia, fatiga y contactos sin repetición, quedan intactas.

Dentro de cada bloque son iguales la red, los rasgos, los clientes iniciales, los detractores y los sorteos indexados. Los conjuntos de promotores están anidados: P1 está contenido en P2 y P2 en P3. La selección usa el orden de comunidades aleatorio de M6: con uno, dos y tres promotores se ocupan, respectivamente, una, dos y tres comunidades. El contraste estima el efecto de agregar promotores bajo esta política, que también aumenta la cobertura; no separa cantidad de localización.

## Entrada exacta por conteo

El validador M6 de porcentajes rechaza 1/120 y 2/120 como decimales finitos exactos. Se incorpora `CountConfig`, un adaptador que hereda de `Config` y utiliza `exact_promoters` entero como fuente del conteo. `promoter_share` se conserva únicamente como proporción informativa coherente. No se redondean conteos ni se alteran el tamaño de población o la base de clientes. La configuración exportada se reconstruye con `CountConfig(**config)`; el CLI M6 original no admite este campo nuevo.

## Revisión del criterio

El criterio M6 requiere, en una ventana de seis períodos, al menos tres compras en la primera mitad, crecimiento de al menos 25 % en la segunda, stock activo final estable o creciente y positivo, nuevas activaciones endógenas que cubran las salidas en la segunda mitad, presión neta positiva en cada período, compras en al menos dos comunidades y ausencia de entradas externas.

El piloto anterior mostró que una expansión inicial rápida puede incumplir la comparación relativa entre mitades aunque produzca muchas compras. No se sustituye el historial anterior ni se calibra el modelo para recuperar un umbral de 15 %.

**Resultado principal revisado: difusión sostenida v0.2**, denominada operativamente despegue sostenido durante una ventana finita. Se confirma si, en seis períodos consecutivos completos, se cumplen todos estos requisitos:

1. Al menos una compra nueva en cada período.
2. Al menos el 5 % del mercado susceptible inicial adquirido dentro de esa ventana: 24 de 480 personas.
3. Presión neta WOM estrictamente positiva en cada período.
4. Stock activo final mayor que cero y no inferior al stock anterior a la ventana.
5. Al menos un nuevo promotor endógeno en la segunda mitad y activaciones de esa mitad iguales o superiores a las desactivaciones.
6. Compras en al menos dos comunidades durante la ventana.
7. Ningún promotor externo añadido durante la ventana.

El volumen mínimo expresa expansión sustantiva y las compras en todos los períodos expresan persistencia. La definición no exige aceleración de ventas, crecimiento perpetuo ni reposición durante toda la vida de la cascada. Una trayectoria estable con reproducción puede calificar; un pico aislado no. Una expansión acelerada pero de volumen pequeño puede calificar bajo M6 y no bajo v0.2. Por tanto, ninguno de los dos criterios es una ampliación automática del otro.

El 5 % es una decisión operativa exploratoria, no un parámetro empírico validado. Se fija ahora, antes de observar las nuevas corridas. La sensibilidad cruza duraciones de 4, 6 y 8 períodos con volúmenes de 2,5 %, 5 % y 10 % del mercado inicial: nueve definiciones sobre las mismas trayectorias. Los mínimos de volumen son 12, 24 y 48 compras por ventana, sin reescalarlos por duración; duración y volumen se interpretan conjuntamente. M6 base y sus factores de crecimiento 1,10 y 1,50 se conservan como tres referencias adicionales.

La clasificación es un observador: nunca retroalimenta decisiones del modelo. Una etiqueta histórica significa que se confirmó al menos una ventana, aunque luego haya saturación o cese de actividad. La primera confirmación usa solo información disponible en ese momento. Una ventana incompleta no confirma un evento. Las etiquetas terminales, el colapso y la saturación continúan siendo las originales de M6 y se identifican explícitamente como tales; no se redefine el colapso a partir del nuevo despegue.

## Resultados y análisis fijados

- Frecuencia de difusión sostenida v0.2 y despegue M6, con intervalos marginales Wilson del 95 % por condición.
- Compras nuevas al período 120: media, mediana, dispersión, rango y distribución por réplica.
- Diferencias emparejadas entre conteos adyacentes y entre tres y uno. Intervalos bootstrap percentiles del 95 % con 20.000 remuestras de bloques; semilla base 88201. No se ajustan por comparaciones múltiples y los intervalos binarios degenerados no implican certeza.
- Desacuerdos de clasificación y sensibilidad de las nueve variantes, sin seleccionar posteriormente la más favorable.
- Tiempo a alcanzar 10 %, 25 %, 50 % y 75 % de los 480 susceptibles. Se conserva la ausencia de evento como censura al 120; las medianas entre éxitos se identifican como condicionales. Las curvas de incidencia usan siempre las 100 réplicas como denominador.
- Comparación de compras al 60 y al 120 dentro de cada corrida; fuentes de compra aún presentes al cierre.
- Frontera discreta exploratoria: menor conteo ensayado con frecuencia observada de al menos 25 %, 50 % y 75 %. Sin interpolación, umbral continuo, ni extrapolación fuera de 0–3. Se entregan los intervalos por condición; no se presentan como intervalo de confianza de un umbral ajustado.

El aporte adicional de un promotor bajo redes y resultados estocásticos no se supone monotónico en cada réplica. La política repartida y el resto de parámetros condicionan cualquier umbral observado.

## Verificación y trazabilidad

Se verifica conteo exacto, conjuntos anidados, entornos emparejados, equivalencia del adaptador con M6 para tres promotores, serialización, rechazo de entradas inválidas, criterios sobre trayectorias sintéticas, censura y ausencia de modificación o información futura por el observador. Los 61 archivos del motor M6 deben coincidir con su manifiesto verificado anterior; no se repite innecesariamente su suite de 229 pruebas si permanecen idénticos.

Cada corrida conserva configuraciones, red, estados iniciales y finales, todos los estados agente–período, eventos, decisiones, genealogía, indicadores y auditoría de clasificación. Se comprueban invariantes, reconciliación independiente de cohortes, sumas de eventos y hashes de exportación. Se esperan 29.040.000 registros agente–período y 144.000 ventanas de cohorte auditadas.

El registro local `pre_execution_record.json` y el hash de `design.json` fijan esta ejecución antes de comenzar. El informe distinguirá los resultados de estas 400 corridas de las 150 anteriores y de los seis seguimientos diagnósticos. Los experimentos de energía, WOM negativo, calidad y ubicación siguen pendientes y no se infieren de este refinamiento basal.
