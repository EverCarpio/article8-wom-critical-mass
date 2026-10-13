# Article 8 — Alcance de M3: experiencia y formación de promotores

Fecha: 26 de septiembre de 2026. Versión de código: **0.3.0-m3**. Lenguaje: Python. Base: especificación mínima v0.1 y módulos M1–M2.

## Objetivo

Cerrar el ciclo positivo entre recomendación, compra, experiencia y activación de un nuevo promotor. La implementación conserva la red y población de M1 y el mecanismo síncrono de WOM positivo, contactos sin repetición y compra de M2.

## Reglas incorporadas

Una compra en t crea un cliente pendiente de experiencia. Al inicio de t + 1 se evalúa una sola vez:

`satisfacción = clip[0,7 + 0,2 × (ajuste − 0,5) + ε, 0, 1]`, con `ε ~ Uniforme[−0,4; 0,4]`.

| Satisfacción | Clasificación | Decisión posterior |
|---|---|---|
| ≥ 0,75 | Satisfecho | Una Bernoulli de probabilidad 0,8 para disposición positiva |
| > 0,35 y < 0,75 | Neutral | Sin disposición WOM |
| ≤ 0,35 | Insatisfecho | Sin WOM negativo en M3 |

La satisfacción no se vuelve a evaluar. La disposición solo se sortea para satisfechos, una vez; la comparación es estricta `u < p`. La calidad, efecto del ajuste, amplitud del ruido, umbrales, probabilidad de disposición y energía de los nuevos promotores son parámetros de `ExperienceConfig`. Todos se validan en [0, 1], con umbral de insatisfacción estrictamente menor al de satisfacción.

Un cliente satisfecho con disposición queda como promotor potencial y recibe energía positiva 0,6. Este parámetro es independiente de la energía inicial de los promotores de generación 0. La disposición y la energía no garantizan la activación.

Al inicio de t + 2 se intenta activar una sola vez si la energía es estrictamente mayor que 0,05 y existe al menos un vecino susceptible no contactado antes por ese emisor. Si se activa, puede emitir en ese período. Si falla, permanece como potencial, sin reintentos, con la causa o causas registradas. Un intento fallido no se contabiliza como desactivación.

El conjunto de susceptibles se fija después de experiencia y activación y antes de los mensajes. Las compras se aplican después de reunir todos los mensajes. No hay cascadas instantáneas. Un promotor puede activarse y agotar sus contactos en el mismo período; ambas transiciones quedan contadas en los flujos.

Los clientes iniciales ya tienen experiencia en t = 0 y no se reevalúan. Los compradores en el último período conservan la experiencia pendiente; los potenciales creados en ese período conservan la activación pendiente para el siguiente. No se amplía el horizonte automáticamente.

## Atribución y generaciones

El padre de una compra es el emisor con mayor credibilidad entre los mensajes positivos recibidos en el período; los empates se resuelven por menor ID. Es la convención contable de M2 y no identifica un efecto causal.

Los promotores iniciales tienen generación 0. Un nuevo promotor recibe generación `padre + 1` al activarse. El padre puede estar inactivo en ese momento. Los compradores que aún no se activaron, incluidos los potenciales bloqueados, tienen generación sin asignar. La raíz inicial y la cadena de padres quedan disponibles para toda compra atribuida.

## Registro y verificación

Se añaden tablas de evaluaciones, intentos de activación y genealogía. Los registros de evaluación contienen ruido, satisfacción y sorteo de disposición; los de activación contienen energía, contactos elegibles al inicio, resultado y razones. Los archivos de configuración y el manifiesto permiten reproducir las corridas normales y verificar su integridad.

La población se conserva. El stock de promotores activos se reconcilia cada período con entradas y salidas. No se permite experiencia repetida, activación repetida, emisión antes de activarse, compra repetida ni contacto posterior a la compra. La inversión del orden de emisores y la ejecución por tramos conservan la trayectoria.

El verificador M3 reúne 110 pruebas —42 de M1, 31 de M2 y 37 nuevas— y 20 trayectorias diagnósticas emparejadas. Los detalles y resultados constan en el informe y paquete de evidencias de esta versión.

## Límite de esta entrega

La energía permanece constante y solo se desactiva por agotamiento de contactos; `promoter_fatigued` mantiene el nombre del estado usado desde M1. La insatisfacción se calcula, pero no se sortea disposición negativa ni se forman nuevos detractores. Los detractores iniciales conservan sus identidades y permanecen inactivos.

Desgaste temporal, fatiga energética, WOM negativo, razones de reproducción y reposición y clasificación de despegue siguen pendientes. Las corridas de diagnóstico no sustituyen el piloto del modelo completo ni permiten concluir que exista un umbral de 15 % de promotores. El siguiente incremento corresponde al desgaste de energía y la fatiga, con sus pruebas.
