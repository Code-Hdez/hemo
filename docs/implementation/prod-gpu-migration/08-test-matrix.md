# Matriz de pruebas

| Capacidad | Prueba principal | Estado |
| --- | --- | --- |
| Propagación router → fake de historial | `test_conversation_history_propagates_ephemeral_browser_boundary` | PASS |
| Propagación router → fake de turnos | `test_conversation_turn_history_propagates_browser_session_hash` | PASS |
| Caso de uso → port sin fallback | `test_get_or_create_propagates_the_complete_session_contract` | PASS |
| `turn_history()` SQLAlchemy real | `test_turn_history_uses_real_sqlalchemy_repository_and_browser_scope` | PASS |
| Aislamiento entre navegadores | prueba anterior y `test_browser_session_hash_isolates_restore_listing_and_mutation` | PASS |
| Staging RAG inválido sin escritura | `test_rag_promotion_rejects_mismatched_collection_without_writing` | PASS |
| Instalación completa y respaldo privado | `test_complete_environment_install_is_atomic_and_keeps_private_rollback` | PASS |
| Fallo posterior con restauración automática | `test_failed_post_install_validation_restores_complete_previous_environment` | PASS |
| Rollback de `.env` y colección | `test_rollback_restores_previous_env_and_rag_collection_idempotently` | PASS |
| Protección ante revisión más nueva | `test_rollback_refuses_to_overwrite_a_newer_environment` | PASS |
| CLI ejecutable | `test_environment_transaction_cli_installs_and_rolls_back` | PASS |
| Regresión completa de chat/persistencia | suite `backend/tests/llm_chat` | PASS: 596 passed, 1 skipped |
| Contrato de entorno, RAG y migraciones | `test_deploy_env.py`, `test_environment_contract.py`, `test_migrations.py` | PASS: 68 passed |
| Liveness sin dependencias externas | `test_liveness_does_not_probe_or_inherit_dependency_state` | PASS |
| GPU/Ollama apagado degrada solo chat | `test_gpu_off_keeps_core_ready_and_degrades_only_chat` | PASS |
| PostgreSQL caído falla el núcleo | `test_database_failure_is_the_core_failure_boundary` y health operacional | PASS |
| RAG requerido degrada chat, no núcleo | `test_required_rag_failure_degrades_chat_without_failing_core` | PASS |
| Contrato RAG impide índice huérfano | `test_rag_contract_rejects_an_index_without_its_collection` | PASS |
| Proveedor privado y health sanitizado | `test_remote_provider_contract_is_private_versioned_and_sanitized` | PASS |
| Timeout, reintento y deadline acotados | `test_provider_contract_bounds_retry_scope_and_stream_deadline` | PASS |
| Runtime incompatible falla cerrado | `test_chat_health_fails_closed_when_runtime_status_contract_breaks` | PASS |
| Correlación fuera del prompt | pruebas de cliente y caso de uso con `request-correlation-1` | PASS |
| Manifiesto usa un único SHA | `test_every_component_must_use_the_same_github_sha` | PASS |
| Imágenes fijadas por digest | `test_image_reference_and_declared_digest_cannot_diverge` | PASS |
| JSON Schema sin deriva | `test_generated_json_schema_is_closed_and_versioned` | PASS |
| Regresión completa del backend | suite `backend/tests` | PASS: 888 passed, 1 skipped, 4 subtests |
| Lint completo del backend | `ruff check backend` | PASS |
| Contrato de inventario OCI | `test_artifact_set_accepts_one_digest_pinned_image_per_runtime` | PASS |
| Rechazo de `latest`/digest/SHA divergente | `test_artifact_set_fails_closed_on_mutable_or_divergent_input` | PASS |
| Binding de digests a `hemovet.release/v1` | `test_real_artifact_digests_can_be_bound_to_release_v1` | PASS |
| Privilegio mínimo y WIF fail-closed | `test_stage3_resource_contract_enforces_least_privilege_and_fail_closed_wif` | PASS |
| Cleanup no destructivo | `test_cleanup_policy_cannot_delete_tagged_or_recent_artifacts` y describe GCP | PASS (`dry-run=true`) |
| Claves de service accounts | `keys list --managed-by=user` para las tres identidades | PASS: ninguna |
| IAM del repositorio | `get-iam-policy hemovet-images` | PASS: 1 writer, 2 readers |
| Identidades y estado de VMs sin cambio | `compute instances describe` read-only | PASS |
| Intercambio OIDC real desde GitHub | run `30762294120`, job con `environment: production` | PASS: token efímero, impersonación, push y read-back |
| WIF falla cerrado sin environment | mismo run, job negativo sin environment | PASS: `unauthorized_client`, attribute condition rejected |
| Dispatch no despliega | estado de jobs del run `30762294120` | PASS: backend/frontend/config/deploy `skipped` |
| Workflow WIF versionado | `test_stage3_wif_workflow_is_manual_fail_closed_and_non_deploying` y `actionlint 1.7.12` | PASS |
| Regresión final de Etapa 3 en Python 3.11 | suite `backend/tests` sobre `7b9cd4d…` | PASS: 898 passed, 1 skipped, 1 warning, 4 subtests |
| Build del frontend | `tsc -b && vite build` | PASS; warning no bloqueante por tamaño de chunk |
| Inventario publicado | `validate_artifact_set.py artifact-set-515d343….json` | PASS: 3 imágenes y un SHA |
| Tags y digests remotos | `gcloud artifacts docker images list --include-tags` | PASS: tres finales, tres bootstrap, ningún `latest` |
| Labels/attestations OCI | inspección remota de índices y manifiestos | PASS: revision, versión, SPDX y provenance |
| Prueba OCI mediante WIF | paquete `wif-validation`, tag `run-30762294120-1` | PASS: `sha256:0998efbb…af989` |
| Servicios efectivos de desarrollo | `validate_compose_topology.py local` y `config --services` | PASS: aplicación + `ollama`/`ollama_setup` |
| Producción sin Ollama | `validate_compose_topology.py production` | PASS: 7 servicios, sin runtime LLM ni `11434` |
| GPU sin aplicación | `validate_compose_topology.py gpu` | PASS: solo `ollama`, `ollama_setup` |
| GPU rechaza servicio/config clínica | `test_gpu_rejects_application_services_and_configuration` | PASS |
| Bind GPU fail-closed | `test_gpu_rejects_non_private_or_unreachable_bindings` | PASS: wildcard, loopback y pública rechazadas |
| Dependencias Compose externas | `test_external_compose_dependencies_fail_closed` | PASS |
| Imágenes productivas inmutables | `test_production_images_require_the_expected_package_and_digest` | PASS: paquete y `@sha256` obligatorios |
| Producción rechaza Ollama/`latest` | `test_production_rejects_local_ollama_and_mutable_images` | PASS |
| Configuración local + Caddy | `docker compose ... config --quiet/--services` | PASS: 8 servicios |
| Configuración QA | `docker compose ... config --quiet/--services` | PASS: 5 servicios, sin runtime |
| Contratos focales de Etapa 4 | `test_compose_topology.py`, `test_deploy_env.py`, `test_environment_contract.py` | PASS: 77 passed |
| Regresión backend Etapa 4 en Python 3.11 | suite `backend/tests` | PASS: 912 passed, 1 skipped, 1 warning, 4 subtests |
| Regresión frontend Etapa 4 | Vitest, Biome, TypeScript y build Vite | PASS: 103 passed, 86 archivos, build correcto |
| Composición sin proveedor | `test_provider_warmup_never_blocks_persistence_or_container_startup` | PASS |
| Historial con proveedor ausente | `test_provider_absence_returns_generic_503_but_keeps_history_accessible` | PASS |
| 503 público estable | prueba anterior y contratos SSE/no-stream | PASS: `LLM_PROVIDER_UNAVAILABLE`, reintentable |
| Timeout del probe | `test_provider_probe_timeout_is_retryable_and_not_an_identity_mismatch` | PASS |
| Recuperación sin reconstruir núcleo | `test_chat_health_recovers_when_the_provider_returns_without_rebuilding_core` | PASS |
| `/api/ps` solo telemetría | `test_chat_health_does_not_confuse_residency_telemetry_with_provider_readiness` | PASS |
| Modelo instalado fuera de VRAM | `test_ollama_identity_uses_installed_artifact_not_vram_residency` | PASS |
| Identidad inválida falla cerrada | contratos de digest/cuantización y taxonomía pública | PASS |
| Probes proveedor/RAG separados | `test_provider_and_rag_health_contracts_are_independent` | PASS |
| RAG requerido degrada solo chat | backend availability + prueba de `AssistantPage` | PASS |
| Polling frontend a 15 s | `sondea cada 15 segundos y recupera el composer sin borrar la conversación` | PASS |
| Probe frontend fallido | `falla cerrado sin ocultar historial cuando no puede confirmar disponibilidad` | PASS |
| Recuperación E2E sin recarga | `el chat se degrada y recupera por polling sin recargar la aplicación` | PASS |
| Regresión `llm_chat` Etapa 5 / Python 3.11 | suite `backend/tests/llm_chat` | PASS: 608 passed, 1 skipped |
| Regresión backend Etapa 5 / Python 3.11 | suite `backend/tests` | PASS: 924 passed, 1 skipped, 4 subtests |
| Ruff completo Etapa 5 | `python -m ruff check --no-cache backend` | PASS |
| Regresión frontend Etapa 5 | Vitest, Biome, TypeScript y build Vite | PASS: 108 passed, 86 archivos, build correcto |
| Dashboard E2E Etapa 5 | Playwright `desktop-1440` | PASS: 22 passed |
| Topologías preservadas | validador + `compose config --quiet/--services` | PASS: local, producción y GPU |
| Contrato cerrado de release GPU | `test_gpu_runtime_projection_fails_closed` | PASS: estado, hot update, paquete, digest, modelo, cuantización y campos extra rechazados |
| Bundle completo e íntegro | `test_bundle_manifest_covers_operational_files_and_matches_bytes` + `sha256sum --check` | PASS |
| CDI oculto y atómico | `test_nvidia_cdi_generation_is_hidden_until_atomic_install` + boot real | PASS: sin specs duplicadas |
| Bundle histórico compatible | `test_historical_release_projects_to_current_bundle_without_mutation` | PASS |
| Compose runtime estricto | validador + `docker compose config --services` en VM | PASS: solo `ollama`, `ollama_setup` |
| Autenticación AR sin clave | metadata token + inspección `/run` + claves SA | PASS: pull por digest, config efímera ausente, 0 claves de usuario |
| No hot update | reconcile normal con revisión nueva | PASS: `release=deferred`, mismo contenedor/applied/modelo |
| Boot aplica revisión pendiente | stop/start + `hemovet-gpu.service` | PASS: `515d343a…`, `b526b1d4…`, `Result=success` |
| Boot con revisión ya aplicada | stop/start + inferencia previa a `/api/ps` | PASS: `boot_inference`, `full_gpu`, `Result=success` |
| Identidad y cuantización | `/api/tags` + `/api/show` | PASS: `0edcdef3…`, `Q4_K_M` |
| Residencia GPU | `/api/ps`, `ollama ps`, `nvidia-smi` host/contenedor | PASS: `size_vram=size`, `100% GPU`, L4 |
| Persistencia tras stop/start | hash/bytes del volumen antes/después | PASS: `56a69d7f…`, 2,497,296,445 bytes |
| Persistencia tras restart de contenedor | `docker restart` + inferencia | PASS: mismo hash, `full_gpu`, 4,840 ms |
| Idempotencia mismo boot | `systemctl restart hemovet-gpu.service` | PASS: `validate_only`, mismo ID/StartedAt/manifiesto/pesos |
| Revisión inválida falla cerrada | manifest con estado no autorizado | PASS: rc=1, contenedor/manifiesto/pesos intactos |
| Rollback runtime/modelo | `rollback-release.sh --previous` dos veces | PASS: `b526… → f2a4… → b526…`, `full_gpu` |
| Logs sin secretos | scan de `journalctl -u hemovet-gpu.service` | PASS |
| Bind privado / exposición externa | `ss` en guest + `curl` externo | PASS: solo `10.128.0.3:11434`; externo timeout |
| VM apagada al cierre | `gcloud compute instances describe` | PASS: `TERMINATED` |
| Gate inicial Etapa 7 | rama, working tree, VM, snapshot e inventarios read-only | PASS: solo `dips.md` no rastreado; GPU apagada; snapshot `READY` |
| Firewall producción → GPU | curl real y Connectivity Test `10.128.0.2 → 10.128.0.3:11434` | PASS: HTTP 200 / `REACHABLE`, allow 700 |
| Firewall interno no autorizado | Connectivity Test `10.128.0.4 → 10.128.0.3:11434` | PASS: `UNREACHABLE`, deny 800 |
| Firewall Internet → Ollama | Connectivity Test y sonda TCP a `34.45.75.48:11434` | PASS: `UNREACHABLE`, rechazado/filtrado |
| Puertos públicos GPU | sondas reales 22/80/443/3000/3389/11434 | PASS: todos rechazados/filtrados |
| IAP hacia GPU | Connectivity Test `35.235.240.1 → 10.128.0.3:22` | PASS: `REACHABLE`, allow 700 |
| IAP + OS Login GPU | dos sesiones independientes, segunda con `sudo -n true` | PASS |
| IAP tras deny-all | sesión adicional con prioridad 900 activa | PASS |
| Recuperación administrativa | disable/enable controlado de deny-all y restauración de claves efímeras | PASS: estado seguro restaurado |
| IAP producción sin alterar runtime | clave de instancia temporal + túnel IAP | PASS: clave retirada; metadata funcional restaurada |
| Eliminación exposición heredada | describe de firewall/tags | PASS: RDP y allow 11434 amplio ausentes; tags web GPU ausentes |
| Protecciones de VMs | describe de instancias y discos | PASS: `deletionProtection=true`, `autoDelete=false` en ambas |
| Snapshot pre-Etapa 6 | describe final | PASS: `READY`, 58,891,150,336 bytes, conservado |
| Apagado ante bootstrap fallido | revisión inválida + unidad `OnFailure` + operaciones GCP | PASS: `shutdown_requested`, `guestTerminate` |
| Recuperación después del fallo | metadata válida + boot posterior | PASS: `Result=success`, `full_gpu`, 19,044 ms |
| Idempotencia bundle Etapa 7 | reinstalación del mismo digest | PASS: sin reinstalar componentes ni corromper estado |
| Logs del fallo | scan journald y config Docker efímera | PASS: 0 coincidencias sensibles; config ausente |
| Contratos GPU Etapa 7 / Python 3.11 | `backend/tests/test_gpu_runtime_bootstrap.py` y contratos asociados | PASS: 18 passed |
| Regresión backend Etapa 7 / Python 3.11 | suite `backend/tests` | PASS: 942 passed, 1 skipped, 1 warning, 4 subtests |
| Ruff completo Etapa 7 | `python -m ruff check --no-cache backend` | PASS |
| ShellCheck Etapa 7 | imagen fijada `koalaman/shellcheck:v0.11.0@sha256:61862e…` | PASS |
| Bundle Etapa 7 | `sha256sum --check deploy/gpu/bundle-manifest.sha256` | PASS: 16 archivos |
| Release GPU Etapa 7 | validación de ambos manifiestos | PASS: bundle `sha256:b781a68b…af65` |
| Topologías Compose sin deriva | regresión completa y diff desde cierre Etapa 6 | PASS: local/producción/GPU; sin cambios Compose |
| Aplicación pública con GPU apagada | `/` y `/api/v1/chat/health` | PASS: HTTP 200; chat degradado; RAG/Chroma listos |
| Producción sin restart | `lastStartTimestamp` antes/después | PASS: `2026-07-02T06:45:52.411-07:00` |
| GPU apagada al cierre Etapa 7 | describe final | PASS: `TERMINATED`, last stop `2026-08-02T16:24:53.277-07:00` |
| Recursos temporales Network Intelligence | listado final | PASS: 0 tests con prefijo `hemovet-stage7-` |
| Gate inicial Etapa 8 | rama, 8 commits publicados, tree y `dips.md` | PASS |
| Python 3.11 final | regresión completa `backend/tests` | PASS: 958 passed, 1 skipped, 4 subtests |
| Ruff completo Etapa 8 | `ruff check --no-cache backend` | PASS |
| Frontend Etapa 8 | Vitest, Biome, TypeScript y build | PASS: 108 passed, 14 archivos |
| E2E crítico Etapa 8 | Playwright desktop | PASS: 8 passed |
| Topologías y Caddy | Compose local/prod/GPU + `actionlint`/Bash | PASS |
| WIF sin environment | jobs negativos | PASS: `unauthorized_client` |
| WIF con ref no autorizada | run `30776824293` | PASS: rechazado por attribute condition |
| WIF + IAP consecutivo | runs `30774662155`, `30774700108` | PASS: `10.128.0.2:22` |
| Publicación OCI final | run `30776245995` | PASS: 3 tags y digests |
| SBOM/provenance | manifiestos de attestations OCI | PASS: SPDX + SLSA v1 en 3 imágenes |
| `hemovet.artifacts/v1` | script y read-back | PASS: mismo SHA, 3 imágenes |
| `hemovet.release/v1` | schema, cross-check artefactos/GPU/RAG | PASS |
| Endpoint privado derivado | URL legado → privada y digest de configuración | PASS |
| URL pública/provider drift | pruebas fail-closed | PASS: candidato ausente |
| Esquemas RAG separados | `markdown-v5` + `hemovet-rag-v2` | PASS |
| RAG real | dry-run corpus curado | PASS: 1,250 fuentes, 4,696 chunks, 0 cuarentena |
| Gate manual GPU/prod | prueba de condiciones workflow | PASS: `DEPLOY + main + confirm_sha` |
| Validación sin mutación | runs PUBLISH/VALIDATE | PASS: GPU metadata y deploy skipped |
| Logs sanitizados | 4 runs representativos | PASS: patrones sensibles ausentes |
| Estado productivo final | GCP + HTTP público | PASS: sin restart, HTTP 200, RAG listo |
| GPU/snapshot final | describe GCP | PASS: `TERMINATED` / `READY` |
| Gate inicial Etapa 9 | rama, refs, tree, `dips.md`, GPU y snapshot | PASS |
| Bundle coordinado | `validate_rollback_bundle.py` | PASS: app/OCI/env/source/GPU/RAG, un SHA |
| Rechazo de bundle divergente | contratos de rollback | PASS: digest, SHA, modelo o RAG divergente falla cerrado |
| Root aislado seguro | pruebas de `deploy-release.sh --isolated-root` | PASS: patrón, owner, modo y sentinel obligatorios |
| Instalación candidata válida | namespace Compose temporal | PASS: env/RAG/digests exactos |
| Fallo posterior y rollback | fallo controlado `up`, dos intentos | PASS: rc 42, `ROLLED_BACK` |
| Restauración de entorno | comparación byte/digest | PASS: anterior exacto en ambos intentos |
| Restauración RAG | lectura `RAG_COLLECTION_NAME` | PASS: colección anterior |
| Backend/frontend anteriores | log Compose sanitizado | PASS: referencias anteriores por digest |
| Colecciones Chroma inmutables | hashes de árboles anterior/candidato | PASS: sin delete/overwrite |
| Datos clínicos sintéticos | hash SQLite + conteos de seis tablas | PASS: sin cambios |
| Compatibilidad de migraciones | árbol Alembic + arranque backend real | PASS: mismo árbol; `0001`→`0012` |
| Readiness con proveedor lento | test health focal | PASS: núcleo listo, proveedor degradado, RAG independiente |
| Rollback GPU metadata | `515d… → af5… → 515d…` | PASS: byte-identical, VM apagada |
| Repetibilidad del rollback | dos fallos consecutivos | PASS: estado no corrupto |
| Python 3.11 Etapa 9 | suite `backend/tests` | PASS: 966 passed, 1 skipped, 4 subtests |
| Ruff / Bash / ShellCheck | gates locales | PASS |
| Topologías Compose | local/producción/GPU | PASS: 7/7/2 servicios esperados |
| WIF rechaza rama Stage 9 | run `30778878989` | PASS esperado: `unauthorized_client`; cero publish/deploy |
| Producción sin cutover | GCP timestamps + HTTP público | PASS: sin restart, HTTP 200, RAG listo |
| GPU/snapshot cierre Etapa 9 | describe GCP | PASS: `TERMINATED` / `READY` |
| Merge final controlado | PR 29 y ancestry Git | PASS: ee9fa759 y c81950b3 contenidos en e7713a72 |
| Publicación final por un SHA | run 30794470808 | PASS: tres imágenes y manifiestos e7713a72 |
| Gate manual sin deploy | jobs publish_gpu_release/deploy_prod/smoke | PASS: skipped |
| Digests finales remotos | Artifact Registry describe | PASS: backend cf1d…, frontend 66cf…, GPU aed7… |
| Registro/login | acceptance report | PASS |
| Autorización entre usuarios | acceptance report | PASS: recursos ajenos 403/404 |
| Mascotas y hemogramas | acceptance report | PASS: dos usuarios, dos mascotas, dos análisis |
| Chat general con RAG | acceptance report | PASS: proveedor invocado y fuente legible |
| Chat seleccionado | acceptance report | PASS: WBC 18.4 y provenance exacta |
| Chat histórico | acceptance report | PASS: paciente correcto, WBC 9.2/18.4 |
| Memoria de seguimiento | acceptance report | PASS: misma conversación, dos turnos |
| Guardrails clínicos | diagnosis/dose/out-of-scope | PASS |
| Streaming SSE | acceptance report | PASS: 11 eventos contiguos, done |
| Sesión del navegador | acceptance report | PASS: navegador/usuario ajenos 404 |
| Persistencia tras restart | acceptance report | PASS: usuario, mascota, análisis y conversaciones |
| Núcleo con GPU apagada | acceptance report | PASS: core/database/RAG listos, chat degradado |
| Historial con GPU apagada | acceptance report | PASS: cuatro mensajes, dos turnos |
| Timeout no bloquea núcleo | acceptance report | PASS: error genérico reintentable, core 7 ms |
| Recuperación sin restart | acceptance report | PASS: provider/chat ready en el mismo backend |
| Modelo final | /api/show | PASS: Qwen digest exacto y Q4_K_M |
| Residencia L4 final | /api/ps + nvidia-smi | PASS: full_gpu, size_vram=size, pico 32 % |
| Persistencia del modelo | volumen previo reutilizado | PASS: 2,497,296,445 bytes |
| Informe sanitizado | claves/valores sensibles + prueba versionada | PASS: 19 casos, cero credenciales |
| Restauración metadata GPU | comparación SHA-256 byte a byte | PASS: a4e9f60b… |
| Restauración metadata SSH prod | comparación SHA-256 byte a byte | PASS: 102c66bd… |
| Contenedores públicos intactos | seis IDs antes/después | PASS |
| Limpieza aislada | labels y roots hemovet-stage10-* | PASS: cero contenedores/volúmenes/roots |
| Cierre GPU/snapshot Etapa 10 | describe GCP | PASS: TERMINATED / READY |
