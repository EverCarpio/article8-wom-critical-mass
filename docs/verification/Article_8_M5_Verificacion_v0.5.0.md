# Article 8 — Verificación M5: WOM negativo y formación de detractores

**Versión:** 0.5.0-m5. **Fecha local:** 27 de septiembre de 2026, America/Bogota. **Runtime:** Python 3.12.14.

## Resultado

El modelo en Python integra WOM positivo y negativo, exposición conjunta, memoria negativa, formación de detractores por experiencia y desgaste de energía de ambos signos. Pasaron **184 pruebas y 80 corridas diagnósticas**, sin fallos ni errores.

Se mantuvieron las 146 pruebas de M1–M4 y se añadieron 38 de M5. Deshabilitar WOM negativo recupera la trayectoria de M4. Mantenerlo habilitado con lambda cero conserva la trayectoria de compras del control deshabilitado, pero produce mensajes, memorias, formación y desgaste negativos. La equivalencia de compras se comprobó en veinte grupos emparejados.

## Reglas implementadas

Los mensajes de ambos signos utilizan la misma instantánea de susceptibles y se procesan antes de comprar. Cada emisor dispone de las oportunidades de M2 y selecciona vecinos sin repetición. Se conservan memorias positiva y negativa con persistencia 0,5; cada influencia se transforma como `1 − exp(−memoria)`.

Con al menos un mensaje positivo nuevo, el índice logístico de compra es:

`z = −2 + 1,5 × necesidad + 1,5 × ajuste + 1,2 × H+ − 1,2 × lambda × H−`.

Sin mensaje positivo nuevo no hay compra ni sorteo, aunque exista exposición negativa o memoria positiva anterior. Varios mensajes generan un único registro por receptor y período. El padre atribuido se selecciona únicamente entre emisores positivos del período.

Un cliente compra en t y evalúa su experiencia una sola vez en t + 1. Si la satisfacción es ≤ 0,35, realiza una única Bernoulli de disposición negativa con probabilidad 0,8. Si es favorable, queda como detractor potencial con energía 0,6. En t + 2 intenta activarse una sola vez: energía > 0,05 y al menos un contacto elegible. Un fallo conserva el estado potencial y sus motivos, sin reintentos.

Los nuevos detractores pueden emitir en el período de activación. Recibir WOM negativo no produce insatisfacción ni disposición negativa sin compra y experiencia propias. Satisfacción, neutralidad e insatisfacción se mantienen separadas de la actividad WOM. Los detractores iniciales conservan sus experiencias previas impuestas.

La energía negativa se actualiza al cierre con desgaste 0,06 y costo 0,04 por mensaje realmente enviado. Potenciales e inactivos conservan su saldo. Las causas de desactivación son energía agotada, contactos agotados o ambas; no hay recuperación ni cambio de signo.

## Arquitectura y trazabilidad

`mixed.py` extiende el ciclo M4 y reúne mensajes, compras y energía de ambos signos en un único período síncrono. `mixed_validation.py` reconcilia independientemente los registros con el estado final, reconstruyendo memorias, contactos históricos, probabilidad, cronología, energía y capacidad efectiva.

La CLI añade `--mode mixed`, `--negative-config` y `--negative-weight`. El interruptor `--negative-off` deshabilita el mecanismo completo. Las configuraciones y exportaciones de modos anteriores se conservan.

Los registros añaden signo, exposición negativa, disposición negativa, energía negativa y estados de detractores. `purchase_decisions.csv` incluye exposiciones no elegibles para compra: con solo mensajes negativos, el sorteo está vacío y la probabilidad es cero. `purchases.csv` contiene únicamente compras efectivas.

La generación se mantiene definida para promotores activos. Los detractores conservan padre positivo y raíz de compra, pero generación sin asignar; no se introduce una genealogía ficticia de contagio de insatisfacción.

## Pruebas automatizadas

| Grupo | Pruebas | Resultado |
|---|---:|---|
| M1: red, población y estados | 42 | Todas pasan |
| M2: WOM positivo y compra | 31 | Todas pasan |
| M3: experiencia y promotores | 37 | Todas pasan |
| M4: energía y fatiga | 36 | Todas pasan |
| M5: Formación y fatiga de detractores | 11 | Todas pasan |
| M5: Exportación y CLI | 5 | Todas pasan |
| M5: Exposición mixta y memoria | 8 | Todas pasan |
| M5: Probabilidad y parámetros | 5 | Todas pasan |
| M5: Regresiones e integridad | 9 | Todas pasan |
| **Total** | **184** | **0 fallos; 0 errores** |

Las pruebas de exposición verifican simultaneidad, memorias por signo, retención extrema, congelación después de comprar, ausencia de compra con WOM exclusivamente negativo y varios emisores con una sola decisión. Una prueba manual usa necesidad y ajuste 0,5 y memorias de ambos signos iguales a 1: los términos de influencia se cancelan cuando lambda = 1 y la probabilidad es `logistic(−0,5)`.

Otra prueba fija un sorteo de compra de 0,45. Con un mensaje positivo la probabilidad excede ese valor; al incorporar un mensaje negativo simultáneo, cae por debajo. Se comprueba que la exposición negativa afecta esa misma decisión y no solo el período siguiente.

Las pruebas de ciclo verifican t, t + 1 y t + 2; disposición estricta y única; probabilidades 0 y 1; energía independiente; bloqueos por umbral y contactos; ausencia de reintentos; fatiga, congelación y causas simultáneas. Un receptor de WOM negativo que no compra permanece susceptible, sin experiencia ni disposición.

Las regresiones verifican equivalencia con M4 cuando el mecanismo se deshabilita, distinción de lambda cero, inversión del orden de emisores, ejecución por tramos, independencia del historial y reversión del período completo ante errores. También detectan corrupción de eventos, memoria, energía, disposición y atribución. La CLI generó archivos idénticos entre procesos con distintas semillas de hash de Python.

## Diagnóstico emparejado

Se ejecutaron **10 semillas × 2 distribuciones × 4 condiciones = 80 corridas**, cada una de 60 períodos. Se usan 600 agentes, 120 clientes iniciales, 18 promotores y seis detractores iniciales reservados. Las semillas enteras van de 20260925 a 20260934; no son fechas.

Las condiciones son mecanismo deshabilitado y mecanismo habilitado con lambda 0, 1 y 2. Cada grupo mantiene la red, rasgos, identidades iniciales y parámetros exógenos. El interruptor cambia la actividad negativa, no la identidad insatisfactoria de los clientes iniciales. Los sorteos se mantienen indexados por agente, período y mecanismo.

En veinte grupos se verificó igualdad exacta de fechas, compradores y padres atribuidos entre el control deshabilitado y lambda cero. Las ochenta corridas conservaron población y reconciliaron eventos con costo energético, compras con exposición, experiencias con clientes y activaciones con sus retrasos. No se observaron fallos de invariantes. Se entregan sesenta diferencias respecto al control.

### Promedios descriptivos: veinte corridas por condición

| Condición | Compras nuevas | Promotores nuevos | Detractores nuevos | Mensajes negativos |
|---|---:|---:|---:|---:|
| Deshabilitado | 433.25 | 160.95 | 0.00 | 0.00 |
| Lambda = 0 | 433.25 | 160.95 | 4.85 | 54.35 |
| Lambda = 1 | 433.70 | 161.50 | 4.75 | 54.15 |
| Lambda = 2 | 433.85 | 162.35 | 4.75 | 54.20 |

Los promedios reúnen diez semillas y dos distribuciones por condición. No muestran una reducción monótona de compras acumuladas al aumentar lambda; las medias de lambda 1 y 2 son ligeramente superiores al control. Este resultado se conserva sin ajustar parámetros para forzar un efecto esperado.

La regla negativa sí reduce o mantiene la probabilidad para un **mismo estado de exposición**, como verifican los cálculos y pruebas controladas. Eso no implica monotonía de ventas finales en trayectorias endógenas: un cambio de compra modifica contactos, tiempos de experiencia, sorteos indexados y emisores futuros. Este diagnóstico no descompone cuál de esos caminos explica las pequeñas diferencias agregadas ni demuestra un efecto beneficioso de WOM negativo.

### Ejemplos de la primera semilla

| Distribución | Condición | Compras nuevas | Promotores nuevos | Detractores nuevos | Mensajes negativos |
|---|---|---:|---:|---:|---:|
| Repartida | Deshabilitado | 445 | 160 | 0 | 0 |
| Repartida | Lambda = 0 | 445 | 160 | 5 | 52 |
| Repartida | Lambda = 1 | 445 | 160 | 5 | 52 |
| Repartida | Lambda = 2 | 445 | 160 | 5 | 52 |
| Concentrada | Deshabilitado | 440 | 162 | 0 | 0 |
| Concentrada | Lambda = 0 | 440 | 162 | 5 | 58 |
| Concentrada | Lambda = 1 | 440 | 162 | 5 | 58 |
| Concentrada | Lambda = 2 | 440 | 162 | 5 | 58 |

En esta semilla los conteos finales de compras no cambian al variar lambda. Con el mecanismo habilitado sí aparecen actividad y nuevos detractores. Las trazas completas corresponden a lambda = 1, en ambas distribuciones, y permiten inspeccionar decisiones y memorias aun cuando los totales coinciden.

No se etiqueta cada no compra como venta causalmente bloqueada. El campo `probability_without_negative` solo retira el término negativo del cálculo para la historia observada; no simula una historia alternativa completa. Los contrastes entre corridas son una salida separada.

## Evidencias y reproducción

El paquete de código incluye módulos, pruebas, configuraciones, documentación y verificadores. El de evidencias contiene `unit_tests.log`, resultados individuales por prueba, ochenta resúmenes, sesenta diferencias emparejadas, resumen de verificación, huella del código y dos trazas completas.

Cada traza incorpora red y población iniciales; las configuraciones; mensajes de ambos signos; decisiones y compras; experiencias; intentos de activación; genealogía; energía; desactivaciones; historial individual; estado final; indicadores por período y manifiesto de integridad.

```bash
python -m unittest discover -s tests -v
python scripts/verify_m5.py --out outputs/verification_reproduction
python -m article8 --mode mixed --config configs/m5_baseline.json --seed 20260925 --negative-weight 1 --out outputs/example_reproduction
```

Ejecute desde `article8_m5` tras descomprimir. Las salidas deben ser nuevas o vacías. La fecha del informe cambia al repetir la verificación; las trayectorias se reproducen con las mismas configuraciones y runtime. No se garantiza identidad byte a byte entre versiones de Python distintas; Colab no se probó.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| Article_8_M5_Python_v0.5.0.zip | 111633 | `6a87d50d6cf5a572b6ad76c00799e2ef4153877f0937cb40ea3d923717880b67` |
| Article_8_M5_Evidencias_v0.5.0.zip | 4542980 | `931cbd3f9a88eeff725558dd74d46d987ae99bbd7795709ca66c39003ef03097` |
| Article_8_M5_Alcance_v0.5.0.md | 5987 | `058c14ba01c76593ac6c16a5e1b2d955d774ba45a264c11d96c603ebe2e54bb5` |

Ambos ZIP pasaron su comprobación de integridad y los manifiestos de las trazas se verificaron al exportar. Registro UTC: `2026-09-27T12:03:56.122434+00:00`.

## Siguiente paso

Implementar y verificar indicadores de reproducción y reposición, sus ventanas temporales y la clasificación de despegue, saturación y colapso. Después se podrá ejecutar el piloto completo. Estas ochenta corridas son diagnósticas: no estiman una frontera de masa crítica ni prueban un umbral universal de 15 %.
