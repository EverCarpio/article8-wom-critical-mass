# Article 8 — Especificación mínima v0.1

**Título de trabajo:** When Does Word of Mouth Take Off—or Collapse? An Agent-Based Model of Promoter Critical Mass, Fatigue, and Negative WOM  
**Fecha:** 25 de septiembre de 2026  
**Estado:** propuesta operativa para implementación y revisión metodológica; sin resultados de simulación.  
**Proyecto:** The 22 Manuscripts – Season II · Universidad Nacional de Colombia, Sede de La Paz.  
**Documento fuente:** Indications - Article 8 - NM - crítical mass.md, proporcionado en el proyecto.

## 1. Propósito y alcance

Construir un modelo basado en agentes (ABM) que permita examinar cuándo una población inicial de promotores genera nuevos clientes y nuevos promotores, cuándo pierde actividad y cuándo el WOM negativo limita la difusión.

La pregunta principal es: **¿bajo qué condiciones una misma proporción nominal de promotores produce despegue sostenido, estancamiento o colapso prematuro?**

Se trata de un ejercicio teórico y computacional. No se utilizarán datos de empresas, clientes, entrevistas, encuestas ni campañas para calibrar parámetros. Los valores de esta versión son supuestos ilustrativos de diseño, pendientes de revisión teórica y sensibilidad. La evidencia producida será evidencia del comportamiento del modelo.

El 15 % constituye una condición de comparación y una pregunta científica. No se ajustarán parámetros para obtener una transición en ese porcentaje. Tampoco se considerará un fallo de programación que las simulaciones contradigan las expectativas conceptuales.

La v0.1 incluye una red estática, una empresa, un producto, una compra por persona, WOM positivo y negativo, experiencia de compra, formación endógena de promotores y detractores, energía y contactos finitos. Se aplazan las políticas de incentivos, eventos, actores especializados, recompra, entrada de población, abandono del producto, reactivación y recuperación. La sincronización se mantiene fija: los promotores iniciales elegibles comienzan simultáneamente.

**Implementación prevista:** NetLogo para el ABM y BehaviorSpace para experimentos; Python o R para preparación y análisis. Este documento no certifica compatibilidad con una versión de software: la versión exacta y sus dependencias se registrarán al implementar.

## 2. Unidad de análisis y horizonte

| Elemento | Decisión v0.1 |
|---|---|
| Población total | N = 600 personas |
| Comunidades | 6, con 100 personas cada una |
| Clientes iniciales | C0 = 120, con 20 por comunidad |
| Mercado susceptible inicial | U0 = 480 personas sin compra |
| Horizonte | 60 períodos, más registro del estado inicial t = 0 |
| Unidad temporal | Mes simulado; escala convencional, sin equivalencia empírica calibrada |
| Compra | Una por agente, irreversible durante la corrida |
| Actualización | Sincrónica: los mensajes del período se reúnen antes de decidir compras |

Se eligen 120 clientes para representar exactamente incrementos de 2,5 puntos porcentuales: cada incremento equivale a tres personas. Esta decisión concreta la recomendación flexible del documento fuente.

## 3. Red e inicialización

### 3.1 Red

Se construye una red simple, no dirigida, sin autoenlaces. Para cada pareja de personas se crea un enlace con probabilidad 0,08 si pertenecen a la misma comunidad y 0,006 si pertenecen a comunidades diferentes. El grado medio esperado bajo esta regla es 99 × 0,08 + 500 × 0,006 = 10,92.

No se añaden enlaces para favorecer la difusión ni se descartan redes por sus resultados comerciales. Se registran nodos, enlaces, grado medio, distribución de grados, clustering, modularidad respecto de las comunidades asignadas, componentes, tamaño del componente mayor y enlaces entre comunidades. Si la conectividad resulta inadecuada para el diseño, se revisa la regla mediante una nueva versión antes de los experimentos principales.

### 3.2 Rasgos individuales

Cada persona recibe, una sola vez:

- Necesidad: uniforme entre 0,5 y 1.
- Ajuste al producto: uniforme entre 0,5 y 1.
- Credibilidad como emisor: uniforme entre 0,6 y 1.

Los rasgos permanecen fijos. Son heterogeneidad sintética, no estimaciones de una población. Las pruebas extremas podrán reemplazar estas distribuciones por valores controlados.

### 3.3 Clientes y emisores iniciales

Se seleccionan al azar 20 clientes por comunidad. Dentro de ellos se reserva una persona por comunidad como detractor inicial potencialmente activo: D0 = 6. Esas identidades se mantienen entre escenarios emparejados.

La proporción inicial de promotores es:

p0 = P0 / C0.

El barrido previsto es 0; 0,025; 0,05; 0,075; 0,10; 0,125; 0,15; 0,175; 0,20; 0,25; 0,30. Los tamaños resultantes son 0, 3, 6, 9, 12, 15, 18, 21, 24, 30 y 36 personas. Por ejemplo, 15 % significa **18 promotores entre 120 clientes**, equivalente a 3 % del mercado total.

Los promotores iniciales se seleccionan sin incluir a los seis detractores:

- **Distribuidos:** asignación tan equilibrada como sea posible entre las seis comunidades. Los residuos se asignan siguiendo una permutación comunitaria fijada por semilla.
- **Concentrados:** asignación equilibrada entre las primeras dos comunidades de esa misma permutación. Hay 38 clientes elegibles en ellas, suficientes para P0 ≤ 36.
- Dentro de cada comunidad se utiliza una ordenación aleatoria fija; al aumentar p0 se amplía el conjunto, conservando anidamiento dentro de cada política.

Los promotores iniciales representan experiencias satisfactorias anteriores al inicio: satisfacción inicial = 1. Los detractores representan experiencias insatisfactorias anteriores: satisfacción = 0. Los demás clientes iniciales son neutrales, con satisfacción = 0,5, y no se activan posteriormente de forma espontánea. Estas condiciones iniciales son impuestas; no se afirma que procedan de la calidad contemporánea q.

Cada promotor seleccionado conserva su pertenencia al conjunto nominal P0 aunque no pueda emitir por energía o contactos. Su estado efectivo debe reflejar esa limitación. Las comparaciones también reportarán grado y alcance iniciales, pues cambiar la ubicación de los promotores puede cambiar estas características.

## 4. Estados y variables de los agentes

Se utilizarán tres dimensiones para evitar confundir compra, satisfacción y actividad:

| Dimensión | Valores |
|---|---|
| Estado comercial | susceptible; cliente pendiente de experiencia; cliente con experiencia |
| Experiencia | no evaluada; neutral; satisfecho; insatisfecho |
| Estado WOM | ninguno; promotor potencial; promotor activo; promotor fatigado; detractor potencial; detractor activo; detractor inactivo |

Reglas de consistencia:

- Una persona no puede ser simultáneamente promotora activa y detractora activa.
- Solo clientes con experiencia pueden emitir WOM. Los emisores iniciales tienen experiencia previa impuesta.
- Un satisfecho puede no convertirse en promotor; un promotor potencial todavía no emite.
- Un promotor fatigado conserva su compra y satisfacción. Fatiga no significa insatisfacción.
- Un insatisfecho puede permanecer sin actividad negativa.
- El WOM recibido no convierte por sí solo al receptor en detractor.

Se almacenarán: identificador, comunidad, vecinos, rasgos, fecha de compra, fecha de experiencia, satisfacción, elegibilidad, fecha de activación, energías positiva y negativa, contactos utilizados por signo, exposiciones recibidas, emisor atribuido a la compra, generación de la cascada, fecha y motivo de desactivación.

La conciencia de la oferta se registra como indicador derivado de haber recibido algún mensaje. No añade una etapa comercial con probabilidades propias en v0.1.

## 5. Secuencia de cada período

El estado t = 0 registra la inicialización. Para t = 1,…,60:

1. Procesar experiencias de las compras realizadas en t − 1.
2. Resolver las activaciones programadas para t; comprobar energía y contactos.
3. Fijar una instantánea de susceptibles y emisores elegibles.
4. Generar todos los mensajes positivos y negativos usando esa instantánea.
5. Actualizar exposiciones y memoria de influencia.
6. Calcular una sola decisión de compra por susceptible elegible y ejecutar las compras conjuntamente.
7. Atribuir cada compra a un emisor positivo y programar su experiencia para t + 1.
8. Actualizar energía de quienes estuvieron activos durante el período.
9. Recalcular contactos restantes tras las compras y desactivar cuando corresponda.
10. Registrar agentes, eventos, indicadores y banderas de clasificación.

La compra en t solo puede producir un nuevo emisor desde t + 2: experiencia en t + 1 y activación en t + 2. Se prohíben las cascadas instantáneas dentro del mismo período.

## 6. Contactos y emisión

Para cada emisor i y signo s, los contactos elegibles son vecinos que siguen susceptibles al inicio del período y que i nunca ha contactado con ese signo.

Cada emisor dispone de k = 2 oportunidades por período. En cada oportunidad, emite con probabilidad:

Pr(mensaje de i) = o × E_i,

con o = 0,8 y E_i en [0,1]. Solo puede emitir si E_i > E_min y existen contactos elegibles. La selección del destinatario es uniforme entre los elegibles, ordenados por identificador para reproducibilidad. Dentro del período se retiran los destinatarios ya seleccionados por ese emisor.

Un mismo receptor puede recibir mensajes de diferentes personas y de ambos signos en el mismo mes. Cada pareja dirigida emisor–receptor produce como máximo un mensaje por signo durante la corrida. Los rechazos de compra no habilitan nuevos intentos del mismo emisor.

Se distinguirán eventos, parejas únicas y personas únicas alcanzadas. Dos emisores que contacten a la misma persona generan dos eventos, pero solo una persona alcanzada. La capacidad efectiva se describe con solapamiento explícito; no se supone que la suma de contactos individuales sea alcance único del sistema.

## 7. Influencia y adopción

Para cada susceptible j se mantienen memorias no negativas L+ y L−. En cada período:

L+_j(t) = rho × L+_j(t−1) + suma de credibilidad de los emisores positivos recibidos en t.

L−_j(t) = rho × L−_j(t−1) + suma de credibilidad de los emisores negativos recibidos en t.

Se usa rho = 0,5. La influencia acotada es H+ = 1 − exp(−L+) y H− = 1 − exp(−L−).

Solo quienes reciben al menos un **mensaje positivo nuevo en t** pueden comprar en t. Para ellos:

z_j(t) = −2 + 1,5 × necesidad_j + 1,5 × ajuste_j + 1,2 × H+_j(t) − 1,2 × lambda × H−_j(t).

Pr(compra_j,t) = 1 / [1 + exp(−z_j(t))].

Una uniforme u de adopción determina la compra si u < Pr(compra). Quienes no reciben mensaje positivo nuevo tienen probabilidad cero. No existe adquisición orgánica o publicidad durante la corrida.

Esta puerta de entrada evita compras espontáneas por el intercepto logístico. También implica que las recomendaciones antiguas solo contribuyen cuando llega un nuevo mensaje positivo. Esa es una simplificación explícita que debe discutirse.

El parámetro lambda pondera la influencia negativa. Lambda = 1 iguala los coeficientes de las dos influencias transformadas, sin afirmar simetría empírica ni equivalencia entre todos sus efectos dinámicos.

Las ventas bloqueadas o retrasadas no se observan directamente. Se puede registrar la probabilidad calculada con y sin influencia negativa, pero no etiquetar una no compra individual como causalmente impedida sin un contrafactual definido.

## 8. Experiencia y formación de emisores

Un cliente que compra en t recibe en t + 1:

satisfacción_i = clip[q + 0,2 × (ajuste_i − 0,5) + epsilon_i, 0, 1],

donde epsilon es uniforme entre −0,4 y 0,4 y q = 0,7 en el escenario base. Esta amplitud permite experiencias a ambos lados de los umbrales en el escenario base; también produce recorte en los extremos de la escala. Se comprobará su influencia mediante sensibilidad, sin ajustarla para obtener un porcentaje particular de despegue.

- Si satisfacción ≥ 0,75: cliente satisfecho. Una única decisión Bernoulli con probabilidad 0,8 determina su disposición a promover. Si es favorable pasa a promotor potencial.
- Si satisfacción ≤ 0,35: cliente insatisfecho. Una única decisión Bernoulli con probabilidad 0,8 determina su disposición a emitir WOM negativo. Si es favorable pasa a detractor potencial.
- En el intervalo abierto (0,35; 0,75): cliente neutral.
- Los satisfechos o insatisfechos sin disposición conservan estado WOM = ninguno.

La activación se evalúa una vez en t + 2. Requiere energía superior al umbral y al menos un contacto elegible. Si no cumple, permanece potencial con motivo registrado, sin reintentos en esta versión.

Los nuevos promotores reciben energía E+_nuevo = 0,6 y los nuevos detractores E−_nuevo = 0,6. La variación de energía inicial afecta **solo a la cohorte inicial** en el experimento principal de energía; la energía de los nuevos promotores se estudia por separado en sensibilidad.

Para atribuir la compra se escoge, entre los mensajes positivos recibidos en el mes de compra, el emisor con mayor credibilidad; los empates se resuelven por menor identificador. La atribución es una convención contable, no una identificación causal. Se conservan todos los mensajes para probar otra regla de atribución.

La generación de un promotor inicial es 0; la de un nuevo promotor activo es la de su emisor atribuido + 1. Un descendiente puede activarse cuando su emisor original ya está inactivo.

## 9. Energía, fatiga y agotamiento de contactos

Para cada emisor activo durante el período y para su signo:

E_i(t+1) = max[0, (1 − delta) × E_i(t) − c × m_i(t)],

donde m es el número de mensajes realmente emitidos, delta = 0,06 y c = 0,04 en el escenario base. La energía usada para todas las oportunidades de un período es la de su inicio; el costo se aplica al cierre.

Un promotor pasa a fatigado cuando:

- su energía final es ≤ 0,05; o
- no conserva contactos elegibles tras las compras del período.

Se registran dos indicadores de causa: energía agotada y contactos agotados. Si ambos se cumplen, se conservan ambos. El estado agregado incluye inactividad por alcance; en el análisis se distinguirá de la fatiga energética.

Un detractor pasa a inactivo bajo los mismos criterios. No hay costos adicionales por rechazo, refuerzo por éxito ni recuperación energética. Las energías de los agentes que ya estaban inactivos quedan congeladas, dado que no pueden reactivarse.

## 10. Parámetros de referencia

Todos los valores siguientes son decisiones ilustrativas de v0.1. Ninguno se presenta como estimación empírica.

| Parámetro | Base | Variación prevista |
|---|---:|---|
| N; comunidades; C0 | 600; 6; 120 | Tamaño y topología en robustez |
| Probabilidades de enlace interna / externa | 0,08 / 0,006 | Modularidad y grado, por separado |
| Horizonte | 60 | 120 períodos para comprobar truncamiento |
| p0 | 0,15 | 11 niveles entre 0 y 0,30 |
| D0 | 6 | 0, 6 y 12 en sensibilidad |
| Ubicación inicial de promotores | Distribuida | Concentrada en dos comunidades |
| E+ inicial | 0,6 | 0,3; 0,6; 0,9 |
| E+ de nuevos promotores | 0,6 | 0,3; 0,6; 0,9, por separado |
| E− inicial y de nuevos detractores | 0,6 | 0,3; 0,6; 0,9 |
| Oportunidades k; factor o | 2; 0,8 | k = 1 y 2 |
| Delta positivo / negativo | 0,06 / 0,06 | 0,03; 0,06; 0,12 |
| Costo por mensaje positivo / negativo | 0,04 / 0,04 | 0,02; 0,04; 0,08 |
| Umbral energético | 0,05 | 0,025 y 0,10 |
| Persistencia rho | 0,5 | 0 y 0,8 |
| Calidad q | 0,7 | 0,4; 0,7; 0,9 |
| Amplitud del ruido de experiencia | ±0,4 | ±0,2 y ±0,5 |
| Umbrales de satisfacción positivo / negativo | 0,75 / 0,35 | 0,65–0,85 / 0,25–0,45 |
| Disposición positiva / negativa | 0,8 / 0,8 | 0,4; 0,8; 1 |
| Retraso compra–experiencia–activación | 1 + 1 períodos | Mantener explícito al comparar ventanas |
| Peso negativo lambda | 1 | WOM deshabilitado; lambda = 1; lambda = 2 |

Cuando WOM negativo esté deshabilitado, no habrá activaciones negativas, eventos negativos ni memoria negativa. Se conservarán las identidades y experiencias iniciales insatisfactorias para comparabilidad. Esto es una intervención sobre el mecanismo completo, distinta de mantener mensajes activos con lambda = 0.

La sensibilidad de D0 modifica la reserva inicial de detractores, equilibrándola entre comunidades y preservando la factibilidad de la selección de promotores. El barrido propuesto sigue siendo factible con D0 = 12: quedan 36 elegibles en las dos comunidades de concentración.

## 11. Indicadores

Se calculan con estados al cierre, salvo que se indique otra cosa:

- Clientes C_t, susceptibles U_t y nuevas compras Y_t.
- Promotores potenciales, activos A_t y fatigados; detractores potenciales, activos e inactivos.
- Nuevos promotores activos B_t y desactivaciones D_t^P.
- Cambio neto de promotores: DeltaA_t = B_t − D_t^P = A_t − A_(t−1).
- Proporción activa entre clientes A_t / C_t y proporción activa en el mercado A_t / N.
- Proporción nominal contemporánea: (potenciales + activos + fatigados) / C_t. Se presenta aparte de p0.
- Contactos restantes por agente r_i,t y fracción restante h_i,t = r_i,t / grado_i; si grado = 0, h = 0.
- Capacidad positiva ponderada M+_t = suma sobre promotores activos de E+_i × credibilidad_i × h_i,t.
- Capacidad negativa M−_t definida análogamente para detractores activos; vale 0 con mecanismo deshabilitado.
- Presión neta indicativa W_t = M+_t − lambda × M−_t.
- Agotamiento del mercado inicial: 1 − U_t / U0.
- Comunidades alcanzadas por mensajes y comunidades con nuevas compras, separadas de la distribución inicial.
- Alcance único por signo y redundancia acumulada = 1 − receptores únicos / eventos; NA si no hay eventos.

M+ y W son índices descriptivos de capacidad, no probabilidades, personas equivalentes ni fuerzas adicionales que entren a la ecuación de compra. Se exportan también energía total y contactos únicos accesibles para examinar cuánto depende el resultado de la construcción del índice.

### Reposición y reproducción

La razón de reposición por período es B_t / D_t^P; si el denominador es cero se registra NA, los conteos y DeltaA. No se sustituye por cero ni por infinito.

Para una ventana de w períodos que comienza en a:

R_ventana(a,w) = suma de B_t entre a y a+w−1 / A_(a−1).

Es un indicador de entradas relativas al stock inicial de la ventana. **R_ventana > 1 no prueba por sí solo crecimiento ni reproducción causal**, porque puede haber salidas y descendientes de emisores que no pertenecen al denominador.

La medida genealógica complementaria es:

R_cohorte(a,w) = hijos directos que se activan, atribuidos a emisores activos al cierre de a−1 y a compras realizadas entre a y a+w−1 / A_(a−1).

Se espera hasta a+w+1 para completar los dos períodos de maduración. Las ventanas sin seguimiento completo se marcan censuradas; denominador cero produce NA. Los nietos no se atribuyen nuevamente al abuelo. Se utilizará w = 6 y sensibilidad w = 3 y 12.

Estas distinciones corrigen la interpretación demasiado fuerte de una razón simple. El cambio neto y los stocks se reportan junto con ambas razones.

## 12. Clasificación de trayectorias

Las reglas son convenciones operativas revisables. No son umbrales empíricos ni se escogerán después para hacer aparecer un resultado deseado.

### 12.1 Despegue sostenido observado

En una ventana de seis períodos a,…,a+5, se confirma despegue si se cumplen simultáneamente:

1. Las compras de la primera mitad suman al menos 3 y las de la segunda mitad son al menos 1,25 veces las de la primera.
2. A_(a+5) ≥ A_(a−1) y A_(a+5) > 0.
3. En la segunda mitad se activa al menos un nuevo promotor y las activaciones son mayores o iguales que las desactivaciones.
4. W_t > 0 en cada uno de los seis períodos.
5. Hay nuevas compras en al menos dos comunidades durante la ventana.
6. No se han añadido emisores externos durante la ventana.

Se registra el inicio a y la confirmación a+5. Es crecimiento sostenido durante una ventana finita, no crecimiento perpetuo en un mercado finito. Se examinarán duraciones de 4 y 8 períodos, divididas en dos mitades, factores de crecimiento 1,10 y 1,50, y una variante que omita W para evaluar dependencia respecto del índice de capacidad.

### 12.2 Colapso prematuro posterior al despegue

Solo se considera después de un despegue confirmado. Para una ventana posterior de seis períodos que comienza en a, se toma como referencia Y_ref, la media de compras de los tres períodos anteriores, y A_ref = A_(a−1):

- Y_ref > 0 y las compras de los seis períodos suman como máximo 0,5 × 6 × Y_ref; además, las compras de la segunda mitad no superan las de la primera. Esto permite reconocer una caída abrupta a cero.
- A_ref ≥ 1 y el stock al cierre no supera la mitad de A_ref.
- W al cierre es ≤ 0, o M+ al cierre no supera la mitad del máximo de M+ observado hasta el inicio de la ventana.
- U_t / U0 ≥ 0,20 en los seis períodos.

Se registran inicio y confirmación. La regla identifica un patrón; no atribuye automáticamente su causa al WOM negativo. Se reportan energía, alcance y actividad negativa para interpretar el mecanismo. Las trayectorias que no satisfagan todos los requisitos no se fuerzan a esta categoría.

### 12.3 Saturación, meseta, pico y ausencia de despegue

| Etiqueta | Regla v0.1 |
|---|---|
| Saturación del mercado inicial | U_t / U0 ≤ 0,10. Si la difusión cae bajo esta condición, no se interpreta como colapso prematuro. |
| Meseta operativa | Durante seis períodos, U/U0 > 0,10; compras de la primera mitad ≥ 3; diferencia absoluta entre compras de ambas mitades ≤ 20 % de las primeras; cambio absoluto de A entre inicio y cierre ≤ 20 % de max(A inicial,1). |
| Pico temporal | Sin despegue confirmado: un bloque de tres períodos tiene compras ≥ max(3, dos veces las del bloque anterior); el bloque siguiente tiene como máximo la mitad de sus compras y como máximo la mitad de su A al cierre; al final queda U/U0 > 0,10. Para el bloque inicial, el bloque previo convencional tiene cero compras. |
| Sin despegue confirmado | No aparece una ventana de despegue. Puede coexistir con difusión lenta o con un pico; no equivale a cero ventas. |
| En evolución / seguimiento insuficiente | No cumple las reglas anteriores o la señal empieza demasiado cerca del final para completar la ventana de confirmación. |

Se guardan **banderas históricas y fechas**, además del estado terminal: una corrida puede despegar y luego colapsar o saturarse. Para la etiqueta terminal se prioriza saturación, luego colapso confirmado, meseta, despegue confirmado todavía vigente, pico sin despegue y, finalmente, sin despegue/en evolución. Un despegue está vigente si una ventana de despegue termina en los últimos seis períodos y no hay un evento posterior prioritario. Las categorías no deben borrar la historia.

Las zonas entre 10 % y 20 % de mercado restante no se fuerzan a saturación o colapso. Se probarán pares alternativos de límites (5 %,15 %) y (15 %,30 %), manteniendo una separación explícita.

## 13. Pruebas de verificación obligatorias

Estas son pruebas previstas; **todavía no se han ejecutado**.

| Prueba | Resultado exigido |
|---|---|
| Conservación poblacional y compra única | N constante; nadie compra dos veces; C_t + U_t = N |
| Estados compatibles | Ningún emisor sin experiencia ni agente activo de ambos signos |
| Cero promotores y sin adquisición externa | Cero mensajes positivos, nuevas compras y promotores endógenos |
| Energía positiva cero | Cero mensajes positivos del agente |
| Sin contactos elegibles | Cero mensajes y alcance nuevo del agente |
| Contactos finitos | Como máximo un evento por pareja dirigida y signo; emisores respetan vecinos |
| Doble exposición | Dos mensajes a una persona incrementan eventos en dos y alcance único en uno |
| Sin satisfacción elegible | Cero promotores endógenos, manteniendo las semillas iniciales |
| Sin insatisfacción elegible | Cero detractores endógenos |
| Delta y costo cero | La energía no decrece; todavía puede agotarse el alcance |
| Fatiga extrema | Con delta = 1, energía cero al cierre; inactividad desde el período siguiente |
| WOM negativo deshabilitado | Cero actividad, eventos, memoria e influencia negativos |
| Comunidades desconectadas | Ningún mensaje cruza componentes sin enlace |
| Retardos | Compra t, experiencia t+1 y primera emisión posible t+2 |
| Decisión conjunta | Reordenar el procesamiento no altera compras con iguales números aleatorios |
| Calidad e influencia extremas | Probabilidades y satisfacción permanecen en [0,1]; con rasgos fijados, más influencia negativa no aumenta la probabilidad de compra |
| Denominadores y genealogía | NA cuando corresponde; cada nuevo promotor tiene un único progenitor atribuido; seguimiento de cohorte completo |
| Misma proporción nominal | Igual P0 en escenarios emparejados; energía/ubicación pueden cambiar M+ sin alterar P0 |
| Clasificación sintética | Casos diseñados de despegue, pico, meseta, saturación y colapso reciben sus banderas; comprobar valores exactamente en los límites |
| Seguimiento truncado | Ventanas incompletas no se convierten en fracasos definitivos; R_cohorte censurado correctamente |
| Reproducibilidad | Mismos parámetros, red, tablas aleatorias y versión producen iguales resultados |

La verificación evalúa programación y consistencia. La revisión conceptual por los profesores evalúa plausibilidad de supuestos. Ninguna sustituye una validación empírica; esta última está fuera del alcance del artículo.

## 14. Plan de piloto y experimentos

### Piloto de diagnóstico

Después de superar las pruebas:

- 11 proporciones iniciales × 10 réplicas emparejadas = **110 corridas**.
- Base: energía inicial 0,6; distribución equilibrada; WOM negativo activo con lambda = 1; calidad 0,7; 60 períodos.
- Revisar trazas, variabilidad, tiempos de ejecución, contabilidad y frecuencia de clasificaciones.
- Comparar adicionalmente el mismo 15 % bajo energías 0,3 y 0,9 y distribución concentrada/distribuida, con las mismas diez réplicas: **40 corridas de diagnóstico**.
- Total previsto de esta primera fase: **150 corridas**, sin interpretación confirmatoria.

No se asume que habrá una transición visible. Si todas las condiciones fallan o despegan, primero se auditan mecanismos y clasificaciones. Cualquier modificación se documenta como nueva versión y se repite el piloto; no se mezclan versiones como si fueran réplicas.

### Experimentos principales, después del piloto

1. Barrido de las 11 proporciones con al menos 100 réplicas por condición: 1.100 corridas base.
2. Proporción × tres energías iniciales: 3.300 corridas, incluyendo el nivel base ya ejecutado si corresponde exactamente a la misma versión y configuración.
3. En la región informativa, cruzar al menos tres proporciones, tres condiciones de WOM negativo y las dos distribuciones.
4. Sensibilidad prioritaria: formación de nuevos promotores, calidad, fatiga, persistencia del WOM, clasificación y horizonte.
5. Robustez de red y de atribución genealógica.

No se ejecutará de entrada todo el factorial. El manifiesto de escenarios identifica combinaciones ya calculadas para evitar duplicarlas. Las diez réplicas del piloto son exploratorias; los experimentos principales utilizarán identificadores de réplica nuevos.

## 15. Semillas y comparabilidad

Cada réplica comparte entre escenarios la red, las identidades de clientes, rasgos individuales y ordenaciones de selección. Cambia únicamente el factor experimental previsto. Se almacenarán los cambios inevitables de composición derivados de la ubicación de promotores.

Antes de implementar, se fijará una generación reproducible de números aleatorios por componente: red, rasgos, asignación y dinámica. Para la dinámica se prepararán tablas indexadas por réplica, agente, período, mecanismo y oportunidad. Cada escenario consulta la misma entrada para la misma decisión potencial, aunque otras decisiones no ocurran.

Los mecanismos cubiertos son oportunidad positiva/negativa, selección de destinatario, compra, experiencia y disposición positiva/negativa. La selección usa el uniforme asignado sobre la lista elegible ordenada. Una llamada aleatoria omitida no debe desplazar las decisiones siguientes.

Se exportarán semillas, tablas o instrucciones exactas para regenerarlas, versiones del generador y huellas de los archivos. Usar solamente la misma semilla global no se considerará garantía suficiente de emparejamiento dinámico.

## 16. Datos y trazabilidad

| Archivo previsto | Unidad y contenido mínimo |
|---|---|
| parameters.csv | Un registro por escenario con todos los parámetros, versión y factores |
| run_manifest.csv | Corrida, réplica, semillas, versión del modelo, configuración, fechas y estado de ejecución |
| network_edges.csv | Réplica, emisor, receptor; cada enlace no dirigido una vez |
| agents_initial.csv | Rasgos, comunidad, compra inicial, estado WOM y energía inicial |
| system_period.csv | Corrida–período; compras, stocks, entradas/salidas, energías, alcance, M+, M−, W, razones y banderas |
| wom_events.csv | Evento, emisor, receptor, signo, período, energía/credibilidad, comunidades, exposiciones anteriores y compra del receptor |
| agent_period.csv | Corrida–agente–período; estados, energía, contactos y fechas |
| lineage.csv | Cliente, emisor atribuido, compra, experiencia, activación y generación; incluye quienes no llegan a promotores |
| run_summary.csv | Una fila por corrida con parámetros, resultados finales, eventos históricos y tiempos |
| verification_log.md | Prueba, configuración, resultado esperado/observado, evidencia y versión |

El estado inicial genera una fila t = 0 en las series aplicables. Los datos de fin de corrida deben reconciliarse con eventos y transiciones. Un valor no definido se guarda vacío/NA y acompañado de los conteos necesarios.

Durante el piloto se guardan todos los registros por agente. Antes del experimento principal puede reducirse ese volumen mediante una política explícita y versionada, preservando las series, los eventos y la genealogía necesarios para auditar cada resultado.

## 17. Análisis y frontera condicional

El resultado principal será la proporción de corridas con despegue sostenido observado, acompañada de incertidumbre entre réplicas. También se reportarán tiempo de despegue, compras finales, incidencia de colapso entre quienes despegaron, saturación y estados sin clasificación concluyente.

Para cada combinación de energía, distribución y WOM negativo se estimará una frontera operativa: la menor proporción ensayada cuya probabilidad estimada de despegue alcance 0,50. Se mostrarán todas las probabilidades y su incertidumbre; este resumen no supone monotonicidad. Si hay resultados no monótonos se describen las múltiples regiones; si no se cruza 0,50, se informa que la frontera no se identificó en el intervalo estudiado. Se repetirá el resumen con 0,25 y 0,75.

La comparación entre proporción nominal e indicadores efectivos usará escenarios equivalentes y separación por réplica entre entrenamiento y evaluación si se construyen modelos predictivos. Para alertas tempranas solo se utilizará información anterior al desenlace. Un modelo que predice una etiqueta mediante los mismos indicadores que la definen tiene circularidad; por ello se contrastarán clasificaciones alternativas y resultados continuos de compras y actividad.

No se presentarán las fronteras como porcentajes recomendados universalmente para empresas reales.

## 18. Organización y responsabilidades

La especificación y el futuro protocolo ODD se guardan en 02_Especificacion_y_ODD. El código corresponde a 03_Modelo_y_codigo; las pruebas a 04_Pruebas_y_verificacion; los escenarios y semillas a 05_Diseno_experimental. Las salidas se separan entre piloto, experimentos principales y robustez, cada una con datos brutos y procesados.

El estudiante lidera revisión bibliográfica, implementación documentada, ejecución, análisis y primeros borradores. Los profesores orientan la teoría, revisan reglas y pruebas, supervisan interpretación y realizan la revisión crítica del manuscrito.

La v0.1 traduce la guía a decisiones programables. No sustituye la revisión de la tesis ni un protocolo ODD completo. Queda pendiente verificar en la fuente original el alcance del resultado del 15 %; este documento no lo presenta como evidencia nueva ni incorpora referencias bibliográficas no verificadas.

## 19. Criterio para comenzar la implementación

Esta versión permite iniciar **el módulo de red, población inicial y contabilidad de estados**. Su primer entregable será una red reproducible con 600 agentes, seis comunidades, 120 clientes, proporciones exactas, las dos distribuciones de promotores y pruebas de invariantes.

Después se incorporan: WOM positivo y compra; experiencia y reproducción; energía y desactivación; WOM negativo; clasificación y exportación. El piloto solo comienza cuando pasan las pruebas correspondientes al modelo completo.

Toda modificación de una regla, parámetro, ventana, denominador o clasificación debe registrarse con fecha, motivo y versión. Un cambio posterior al piloto no se presenta como si hubiese sido fijado antes de observarlo.
