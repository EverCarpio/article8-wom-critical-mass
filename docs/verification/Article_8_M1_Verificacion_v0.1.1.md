# Article 8 — Verificación del módulo M1 en Python v0.1.1

**Fecha:** 25 de septiembre de 2026, Colombia. **Código:** 0.1.1-m1. **Entorno probado:** Python 3.12.14.

## Resultado

**42 pruebas automatizadas aprobadas, cero fallos y cero errores.** Además, se verificaron 220 inicializaciones y 60 comprobaciones energéticas emparejadas sin fallos de invariantes.

El módulo genera red, población y estados en t = 0. Se ejecutaron **cero simulaciones temporales de difusión**. Esta entrega no demuestra despegue, reproducción ni colapso y no sustituye la verificación pendiente del modelo completo.

## Correspondencia con la especificación

La especificación v0.1 se conserva como referencia científica y la adenda v0.1.1 registra la decisión de usar Python. El cambio de plataforma fue solicitado por el profesor coordinador. No se modificaron los parámetros de inicialización para producir resultados favorables.

| Elemento | Resultado en el ejemplo base |
|---|---:|
| Población | 600 |
| Comunidades | 6 de 100 personas |
| Clientes iniciales | 120; 20 por comunidad |
| Susceptibles | 480 |
| Promotores nominales | 18, equivalentes al 15 % de clientes y 3 % del mercado |
| Promotores activos iniciales | 18 en ambas distribuciones |
| Detractores activos iniciales | 6; uno por comunidad |
| Clientes neutrales | 96 |
| Distribución equilibrada | 3 promotores en cada comunidad |
| Distribución concentrada | 9 en comunidad 2 y 9 en comunidad 3; IDs desde cero |

## Red del ejemplo base

**Semilla maestra:** 20260925. La red y los rasgos son idénticos en ambas políticas de distribución.

| Indicador | Valor |
|---|---:|
| Enlaces | 3352 |
| Enlaces internos | 2425 |
| Enlaces entre comunidades | 927 |
| Grado medio | 11.173333 |
| Clustering medio, incluyendo aislados | 0.045683 |
| Modularidad de comunidades asignadas | 0.556574 |
| Componentes | 1 |
| Fracción en el componente mayor | 100.00% |

Estos valores describen una realización sintética, no una red observada. Las redes no se reparan ni se seleccionan según resultados de difusión. El grado esperado por la regla de generación es 10,92; no se exige que cada realización sea exactamente igual a ese valor.

En las diez semillas, el grado medio estuvo entre 10.6900 y 11.2333; su promedio fue 10.9777. Este barrido comprueba inicialización y variabilidad, no constituye una prueba estadística exhaustiva del generador.

## Comparación de capacidad inicial

| Indicador | Distribuida | Concentrada |
|---|---:|---:|
| Capacidad positiva M+ | 6.969726 | 7.037081 |
| Capacidad negativa M− | 2.629342 | 2.629342 |
| Presión neta indicativa | 4.340383 | 4.407738 |

La concentración presenta un M+ ligeramente mayor en esta semilla porque el índice depende también de credibilidad y contactos restantes. No se obliga a la distribución equilibrada a dominar ese índice ni se interpreta esta diferencia como mayor difusión futura. La cobertura por comunidades y los resultados temporales deben analizarse por separado.

## Diseño de comprobación

- Once proporciones: 0; 0,025; 0,05; 0,075; 0,10; 0,125; 0,15; 0,175; 0,20; 0,25; 0,30.
- Dos políticas de distribución y diez semillas: 20260925 a 20260934. Total: 220 inicializaciones.
- Al 15 %, energías 0,3; 0,6; 0,9, dos políticas y diez semillas: 60 comprobaciones energéticas. Veinte coinciden con configuraciones del barrido anterior: 260 configuraciones únicas y 280 evaluaciones entre ambos barridos.
- Se conservaron red, clientes, detractores, rasgos y ordenaciones de selección entre escenarios emparejados. Los conjuntos de promotores son anidados al aumentar la proporción dentro de cada política.
- Los CSV/JSON fueron recuperados localmente y comprobados con SHA-256. Dos procesos con diferentes PYTHONHASHSEED produjeron exportaciones idénticas byte por byte.

## Cobertura de pruebas

| Grupo | Cobertura |
|---|---|
| Configuración | Conteos exactos, límites, no finitos, porcentajes fraccionarios e imposibilidad de concentración |
| Red | Grafos simples, simetría, componentes, grados, clustering y modularidad contra grafos calculables a mano |
| Inicialización | Conservación, balance por comunidad, separación de roles, estados, fechas y genealogía inicial |
| Casos límite | Cero promotores, cero energía, umbral exacto, red sin enlaces, mercado sin susceptibles y WOM negativo deshabilitado |
| Emparejamiento | Mismas condiciones exógenas y conjuntos nominales cuando corresponda, sin compartir agentes mutables |
| Exportación | Conteos recuperados, configuración reconstruible, integridad, detección de alteraciones y rechazo de sobrescritura |

Las pruebas de cero energía y contactos verifican el estado y la elegibilidad inicial. Todavía no verifican la emisión a lo largo de meses. Las pruebas de satisfacción/activación endógena, adopción, costos temporales, retardos, genealogía dinámica y clasificación de trayectorias quedan pendientes.

### Registro de pruebas automatizadas

| Prueba | Resultado |
|---|---|
| test_m1.ConfigTests.test_exact_promoter_counts | passed |
| test_m1.ConfigTests.test_fractional_person_rejected | passed |
| test_m1.ConfigTests.test_invalid_settings_rejected | passed |
| test_m1.ConfigTests.test_max_concentration_with_twelve_detractors_is_feasible | passed |
| test_m1.ExportTests.test_cli_exports_are_byte_identical_across_hash_seeds | passed |
| test_m1.ExportTests.test_empty_network_csv_retains_header | passed |
| test_m1.ExportTests.test_existing_results_are_not_overwritten | passed |
| test_m1.ExportTests.test_export_rows_checksums_and_reconstruction | passed |
| test_m1.ExportTests.test_tampered_export_is_detected | passed |
| test_m1.InitializationTests.test_activation_threshold_is_strict | passed |
| test_m1.InitializationTests.test_all_customers_means_no_susceptible_contacts | passed |
| test_m1.InitializationTests.test_baseline_totals_and_denominators | passed |
| test_m1.InitializationTests.test_both_exhaustion_reasons_are_retained | passed |
| test_m1.InitializationTests.test_concentrated_promoters_are_balanced_nested_and_in_fixed_two_communities | passed |
| test_m1.InitializationTests.test_contact_eligibility_respects_edges_purchase_and_sign_history | passed |
| test_m1.InitializationTests.test_distributed_promoters_are_balanced_and_nested_at_all_shares | passed |
| test_m1.InitializationTests.test_equal_customer_and_detractor_allocation | passed |
| test_m1.InitializationTests.test_hand_calculated_capacity_on_complete_six_person_graph | passed |
| test_m1.InitializationTests.test_incompatible_or_nonfinite_states_rejected | passed |
| test_m1.InitializationTests.test_m1_outputs_do_not_claim_temporal_results | passed |
| test_m1.InitializationTests.test_negative_off_preserves_dissatisfied_customer_identities | passed |
| test_m1.InitializationTests.test_no_edges_disables_emitters_without_forcing_connectivity | passed |
| test_m1.InitializationTests.test_promoter_detractor_disjoint_and_all_emitters_are_customers | passed |
| test_m1.InitializationTests.test_state_compatibility_rejects_unexperienced_emitter | passed |
| test_m1.InitializationTests.test_timestamp_and_genealogy_invariants_detect_corruption | passed |
| test_m1.InitializationTests.test_zero_energy_retains_nominal_promoters_and_satisfaction | passed |
| test_m1.InitializationTests.test_zero_negative_weight_does_not_disable_negative_emitters | passed |
| test_m1.InitializationTests.test_zero_promoters_preserves_base_customers | passed |
| test_m1.NetworkTests.test_complete_graph_statistics | passed |
| test_m1.NetworkTests.test_empty_graph_is_retained | passed |
| test_m1.NetworkTests.test_generated_edges_are_simple_symmetric_and_within_range | passed |
| test_m1.NetworkTests.test_invalid_graphs_rejected | passed |
| test_m1.NetworkTests.test_triangle_plus_isolate_uses_all_nodes_in_clustering | passed |
| test_m1.NetworkTests.test_two_disconnected_triangles_have_known_statistics | passed |
| test_m1.ReproducibilityTests.test_alternative_seed_changes_network | passed |
| test_m1.ReproducibilityTests.test_component_seeds_distinct_and_global_rng_untouched | passed |
| test_m1.ReproducibilityTests.test_energy_changes_capacity_not_roles | passed |
| test_m1.ReproducibilityTests.test_identical_seed_recreates_entire_state | passed |
| test_m1.ReproducibilityTests.test_independent_scenarios_do_not_share_mutable_agents | passed |
| test_m1.ReproducibilityTests.test_keyed_draws_order_independent_bounded_and_separated | passed |
| test_m1.ReproducibilityTests.test_mismatched_environment_rejected | passed |
| test_m1.ReproducibilityTests.test_scenario_settings_preserve_environment_without_cache | passed |

## Archivos y reproducción

- Article_8_M1_Python_v0.1.1.zip: código, pruebas, configuraciones, instrucciones y adenda.
- Article_8_M1_Evidencias_v0.1.1.zip: registros de pruebas, resumen JSON, barridos CSV, semillas y dos ejemplos completos.
- Article_8_Adenda_Python_v0.1.1.md: decisión de plataforma y precisiones operativas.

Desde la carpeta article8_m1 descomprimida:

```bash
python -m unittest discover -s tests -v
python scripts/verify_m1.py --out outputs/verification
```

La ruta de salida debe ser nueva o vacía. El código no requiere paquetes externos. El README incluye ejemplos de ejecución y un procedimiento para Colab; Colab no se ejecutó en esta sesión.

| Paquete | SHA-256 |
|---|---|
| Article_8_M1_Python_v0.1.1.zip | 9d197fceb04f7ef98a5f0d4524351ed483f2db936a4d713dcac4d869e0aba609 |
| Article_8_M1_Evidencias_v0.1.1.zip | 49cfbc2b7492df1e54a28c5560f1692905375df2c571624b747a8146b5275e3a |

## Siguiente paso

Implementar M2: oportunidades de WOM positivo, selección de contactos sin repetición, registro de exposiciones y compra única mediante actualización sincrónica. Después se incorporarán experiencia, reproducción de promotores, energía temporal, WOM negativo y clasificación. El piloto de 150 corridas se ejecutará cuando esas piezas y sus pruebas estén completas.
