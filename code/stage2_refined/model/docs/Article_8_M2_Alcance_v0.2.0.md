# Article 8 — Alcance del módulo M2 v0.2.0

**Fecha:** 25 de septiembre de 2026, Colombia.  
**Código:** 0.2.0-m2.  
**Base:** especificación mínima v0.1 y adenda Python v0.1.1.

## Mecanismos incorporados

M2 incorpora oportunidades de WOM positivo, destinatarios elegibles sin repetición por emisor, memoria de influencia, compra probabilística y compra única. Las decisiones se actualizan sincrónicamente y se registran como mensajes, decisiones, compras y estados por período.

Se conservan las ecuaciones de las secciones 6 y 7: dos oportunidades por período; probabilidad de emitir 0,8 por energía; persistencia de memoria 0,5; influencia acotada; coeficientes logísticos −2, 1,5, 1,5 y 1,2. Comprar requiere un mensaje positivo nuevo. Los parámetros son supuestos ilustrativos sin calibración empírica.

## Condiciones del módulo parcial

Para verificar estos mecanismos de forma aislada, M2 tiene WOM negativo deshabilitado, energías constantes y formación endógena de emisores deshabilitada. Estas condiciones delimitan la implementación parcial; no sustituyen las reglas previstas para el modelo completo.

Los seis clientes reservados como detractores mantienen identidad e insatisfacción, pero permanecen inactivos. Un promotor deja de emitir cuando agota sus contactos susceptibles no utilizados; su energía y satisfacción no cambian. El motivo es contacts_exhausted.

El comprador pasa a cliente pendiente de experiencia. Su fecha de experiencia prevista es t + 1, pero M2 no la procesa. No se asignan satisfacción, generación de promotor ni fecha de activación a nuevos compradores. La atribución de la compra se registra para el desarrollo posterior de la genealogía.

## Contabilidad y actualización

- Un emisor no vuelve a contactar al mismo receptor, aunque la recomendación no termine en compra.
- Distintos emisores pueden contactar a la misma persona, incluso en el mismo período.
- Todos los mensajes de un período utilizan la misma instantánea de susceptibles; ninguna compra parcial elimina un mensaje del mismo lote.
- Cada receptor expuesto decide comprar una vez por período. Tras comprar deja de ser susceptible y nunca vuelve a comprar.
- Eventos, parejas dirigidas y personas únicas alcanzadas se contabilizan por separado.
- Las probabilidades usan todas las credibilidades del lote y la memoria anterior. Las memorias de quienes ya compraron quedan congeladas.
- La atribución usa mayor credibilidad y, en empate, menor ID. No es una estimación causal.
- Si varios mensajes preceden una compra, todos pueden indicar que el receptor compró, pero solo un emisor recibe el crédito. El conteo de ventas procede de purchases.csv.

## Verificación y versiones

Se conservaron las 42 pruebas de M1 y se añadieron 31 de M2. Pasaron las 73 pruebas, además de veinte trayectorias diagnósticas de 60 períodos. Los artefactos de M1 se conservan como referencia.

Las veinte trayectorias cubren dos distribuciones y diez semillas, todas con 18 promotores iniciales. Comprueban invariantes y reproducibilidad; no constituyen el piloto de 150 corridas ni el experimento principal. No se clasifican como despegue o colapso.

## Próxima incorporación

Experiencia posterior a compra, satisfacción, disposición a promover y activación con retraso. Energía temporal, WOM negativo, reproducción y clasificación deberán integrarse y verificarse antes del piloto del modelo completo.

