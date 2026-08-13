# Etapa 10 — Aceptación E2E de la revisión final

## Objetivo

Publicar una revisión completa que contenga la corrección de Etapa 9, demostrar
su comportamiento funcional y operativo en un namespace no público, validar
inferencia real sobre NVIDIA L4 y dejar producción exactamente en su estado
anterior.

## Estado inicial

| Elemento | Estado verificado |
| --- | --- |
| Rama | dev-agosto/feat-gpu-deployment-separation |
| HEAD local/remoto | b0c17df7190822205451493c53ba904f7e6461f5 |
| main previo | 7996a8e43c672b92da5772e571512c5719bd3f0e |
| Corrección requerida | ee9fa759, contenida en la rama |
| Working tree rastreado | limpio |
| Archivo ajeno | dips.md, no rastreado, 68,340 bytes, SHA-256 22ef723ec15957e215ef5dadc207572b8dc11b9e8b715b41dc89d9b8e0e145da |
| Producción | RUNNING; último arranque 2026-07-02T06:45:52.411-07:00 |
| GPU | TERMINATED |
| Snapshot | hemovet-llm-gpu-pre-stage6-20260802, READY |

## Alcance

- revisión controlada y merge mediante PR;
- publicación por WIF desde main sin clave JSON;
- tres imágenes OCI y manifiestos para un único GITHUB_SHA;
- aplicación candidata en Compose aislado, sin Caddy ni puertos públicos;
- datos sintéticos exclusivamente para autenticación, mascotas, hemogramas y
  conversaciones;
- arranque temporal de la GPU, validación de Qwen y uso real de L4;
- pruebas con proveedor disponible, reinicio y proveedor apagado;
- restauración de metadata, credenciales temporales y recursos de prueba.

## Elementos fuera de alcance

- ningún cutover o cambio de tráfico público;
- ninguna lectura o escritura de datos clínicos productivos;
- retirar Ollama local, SSH de emergencia o secrets antiguos;
- cambiar PostgreSQL, Chroma o la colección RAG de producción;
- iniciar la puesta en servicio de Etapa 11.

## Riesgos y rollback previstos

La prueba podía dejar costo GPU, metadata temporal, credenciales administrativas
o recursos Compose aislados. Se capturaron antes los bytes de metadata GPU y
SSH, los IDs de los seis contenedores públicos, estado/timestamps de ambas VMs y
estado del snapshot. El rollback fue restaurar esos bytes exactos, apagar la
GPU y retirar por nombre solamente los recursos con etiqueta
hemovet-stage10-*. La revisión af5ab60b… permaneció disponible como rollback
completo.

## Revisión publicada

PR 29 se fusionó a main como:

e7713a72369bb9365f6d5323e165fbf84488bfb4

La revisión contiene:

- ee9fa759670caa56eaceadc40b6561516ab9949f;
- 0b41fd95, respuesta general estructurada completa;
- fbeec829, reserva de tokens para el envelope;
- 8a24cdf5, conservación del presupuesto de entrada;
- 8b0666fa, finalización estable del envelope;
- c81950b31d0fb3f8018537e7c792fe7016c97dd2;
- el mismo árbol Git 0bea2d220fec4656e531c7772ced22829c26bd64.

El run 30794470808 terminó success. Tests, validación, build y publicación
pasaron; publish_gpu_release, deploy_prod y smoke productivo quedaron skipped
porque no se aprobó el gate manual. WIF no se amplió a ramas arbitrarias.

## Artefactos inmutables

| Componente | Digest |
| --- | --- |
| Backend | sha256:cf1dcab600cb880dbc07820896fd7816dac48956a4b9e6388df2f293a21b1826 |
| Frontend | sha256:66cf329d1dce2f544454876b97433cf621fe4769d5d6a086ae9ca3074a489faf |
| Runtime GPU | sha256:aed77e3c668587c12ac32751d484d1a287e2853b3ffb56760fe8222a5fd3cd0c |
| Modelo | sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0 |

Los tres digests OCI se leyeron de vuelta desde Artifact Registry. No se usó
latest. El artefacto GitHub fue hemovet-release-30794470808-1.

Manifiestos descargados del run:

| Archivo | SHA-256 bruto |
| --- | --- |
| artifact-set.json | 31c307fcf2b4b53b96f6fae51d67e754b0486dc12a77c0b8976199d3905c74a9 |
| gpu-runtime.json | 286d2ded52e7c4f706d398bc3b45b6bd25d69dad8a8ed0dd88f32fd0cd235301 |
| rag-summary.json | dd94f63a206c1d23934c0ca42a5bf2497f0e01d4b24682d1eff6ff14a0a2c196 |
| release-manifest.json | 7681af24669d750d88a209e80b2f777ac5bf45506bb79e1aa832cc01def27b25 |

La copia versionada solo normaliza formato JSON y source_dir del resumen RAG a
knowledge_base/expert_review/approved; los campos contractuales son idénticos.

## RAG

| Campo | Valor |
| --- | --- |
| Colección | hemovet_canine_hematology_v2__6832f37d4287 |
| Fingerprint | 6832f37d428731520ce903de60d0781df543df3a10c84f1fcdbf27056bef9b60 |
| Fuentes | 1,250 |
| Chunks | 4,696 |
| Cuarentena | 0 |
| Schema | hemovet-rag-v2 |

El volumen de prueba se clonó desde evidencia no productiva ya validada. Su
contenido permaneció separado de Chroma productivo y se eliminó al terminar.

## Entorno aislado

Se usó el proyecto Compose hemovet-stage10-final-e7713a con db, chroma,
backend, frontend, volume_permissions y rag_ingest. No se inició Caddy, no se
publicaron puertos y no se montaron volúmenes productivos. PostgreSQL,
pet-media, Chroma y cache de embeddings tuvieron volúmenes exclusivos.

El entorno privado se renderizó con modo 0600, pasó el validador y coincidió con
configuration_digest del manifiesto. Sus valores no se imprimieron ni se
versionaron. Los tokens y credenciales sintéticos del runner fueron destruidos
al cerrar.

## Casos de aceptación

Los 20 requisitos del usuario se cubrieron con 19 casos automatizados; registro
e inicio de sesión comparten un caso porque validan la misma sesión
autenticada.

| Requisito | Evidencia automatizada | Resultado |
| --- | --- | --- |
| Registro e inicio de sesión | registration_login_and_authentication | PASS |
| Autorización entre usuarios | pets_and_cross_user_authorization | PASS |
| Mascotas | pets_and_cross_user_authorization | PASS |
| Hemogramas | hemograms_history_and_user_isolation | PASS |
| Chat general | general_chat_with_readable_rag_sources | PASS |
| Chat seleccionado | selected_hemogram_uses_exact_values | PASS |
| Chat histórico | historical_chat_uses_patient_analyses | PASS |
| Seguimiento/memoria | follow_up_memory_and_persisted_turns | PASS |
| Valores reales | selected_hemogram_uses_exact_values | PASS, WBC 18.4 |
| Fuentes RAG | general_chat_with_readable_rag_sources | PASS |
| Sin diagnóstico | direct_diagnosis_is_refused | PASS |
| Sin dosis | medication_and_dose_are_refused | PASS |
| Fuera de alcance | out_of_scope_question_is_refused | PASS |
| Historial con GPU apagada | history_available_with_gpu_off | PASS |
| Estado degradado | core_degraded_with_provider_off | PASS |
| Recuperación automática | automatic_provider_recovery_without_backend_restart | PASS |
| Streaming SSE | streaming_sse_contract | PASS |
| Timeout aislado del núcleo | provider_timeout_does_not_block_core | PASS |
| Sesión de navegador | browser_session_and_user_isolation | PASS |
| Persistencia tras reinicio | data_and_conversations_survive_backend_restart | PASS |

El informe sanitizado tiene schema hemovet.stage10-acceptance/v1, 19 passed,
cero failed y SHA-256
1db7a73e62e0b836b6c4765ca3b562a1d947e964be68b706283354ae5044a15a.
No contiene email, token, password, prompt, respuesta ni Authorization.

## Memoria, datos y modos de chat

- el caso seleccionado usó el análisis autorizado exacto, con WBC 18.4 y
  provenance_matched=true;
- el caso histórico limitó el contexto al paciente correcto y utilizó los dos
  análisis WBC 9.2 y 18.4;
- el seguimiento reutilizó la misma conversación, conservó cuatro mensajes y
  dos turnos, y recuperó el parámetro WBC;
- el chat general invocó Qwen y devolvió una fuente RAG legible;
- el streaming produjo once eventos contiguos y finalizó en done;
- diagnóstico, dosis y fuera de alcance aplicaron sus políticas sin publicar
  contenido clínico en la evidencia.

## GPU e inferencia

La VM se encendió desde 2026-08-03T01:00:05.469-07:00 hasta
2026-08-03T01:07:34.992-07:00, 449.523 segundos.

| Métrica | Valor |
| --- | --- |
| GPU | NVIDIA L4, 23,034 MiB |
| Driver | 580.159.03 |
| Docker | 29.6.2 |
| NVIDIA Container Toolkit | 1.17.8 |
| Modelo | qwen3:4b-instruct-2507-q4_K_M |
| Cuantización | Q4_K_M |
| Dispositivo | full_gpu |
| Tamaño / VRAM del modelo | 2,895,118,335 / 2,895,118,335 bytes |
| VRAM observada | 2,996 MiB |
| Uso GPU máximo | 32 % |
| Memoria contenedor | 3.076 GiB |
| Latencia de revalidación | 514 ms |
| Volumen de pesos | 2,497,296,445 bytes |

/api/show confirmó identidad y cuantización; /api/ps confirmó residencia, no
identidad. nvidia-smi y el proceso del contenedor mostraron uso real de la L4.
El modelo persistido fue reutilizado.

La metadata final deseada de la GPU volvió al hash inicial
a4e9f60b8138553707291b247424a1bc7de8f369f74faa6048ec42176d2c1b71 y
la VM quedó TERMINATED. La revisión final permanece en disco como historial,
pero no quedó seleccionada para un arranque productivo.

## Modo degradado y recuperación

Con el proveedor apagado:

- core_ready=true;
- database_ready=true;
- rag_ready=true;
- chat_ready=false;
- status=degraded;
- frontend e historial continuaron disponibles;
- un timeout devolvió LLM_PROVIDER_CONNECT_TIMEOUT, HTTP 504 y retryable=true,
  sin bloquear la respuesta del núcleo, que tardó 7 ms.

Al encender el proveedor, chat_ready y provider_ready volvieron a true en el
mismo backend, sin restart. Tras apagar nuevamente la GPU, el historial
persistido siguió accesible.

## Pruebas de código y CI

Run 30794470808:

| Gate | Resultado |
| --- | --- |
| Migraciones | 6 passed |
| llm_chat | 632 passed, 1 skipped |
| Release y contratos | 48 passed |
| Evaluación LLM | 24 passed |
| Backend restante | 304 passed, 4 subtests |
| Ruff | PASS |
| Frontend unitario | 108 passed en 14 archivos |
| Biome / TypeScript / build | PASS |
| Playwright crítico | 8 passed |
| Compose local/prod/GPU | PASS |

También pasaron localmente Ruff, los 632 casos llm_chat y dos E2E focales de
polling/seguridad. La suite visual completa mostró fixtures antiguos
dependientes del tour y expectativas de pantalla sin mascota; no se modificó
producto ni se contó como gate. El flujo crítico usado por CI y la aceptación
funcional sí pasaron.

## Incidencias transparentes del harness

1. Una validación remota usó primero /app/scripts; la ruta real era
   /app/backend/scripts. El intento abortó antes de mutar datos y la repetición
   pasó.
2. La primera aserción de servicios comparó orden textual; se sustituyó por
   comparación de conjuntos y confirmó la topología exacta.
3. Una orden de hash de volumen tuvo quoting incorrecto; se repitió
   idempotentemente y verificó ambos hashes.
4. La limpieza inicial no pudo sobrescribir un config.json propiedad de root;
   se revalidaron los targets y se eliminó con sudo limitado a los seis
   directorios temporales exactos.

Ninguna incidencia se presentó como una prueba exitosa ni alcanzó producción.

## Restauración y ausencia de cutover

Los seis IDs públicos antes y después de la aceptación coincidieron:

| Servicio | ID |
| --- | --- |
| backend | 199a8e5a0e42 |
| caddy | 484e61a6b054 |
| chroma | 996af33d69d5 |
| db | 6c3af7fc7519 |
| frontend | 919da92adbb7 |
| ollama | 83bcdc6d74e6 |

hemovet-prod conservó el mismo lastStartTimestamp. El sitio público respondió
HTTP 200 con 1,167 bytes y la colección pública mantuvo 4,696 chunks. La
metadata SSH de producción se restauró exactamente al SHA-256
102c66bdf9fa28ac73456e8648c88a1d3546c8484e62cab504e7b7fbcd6d8349.

Se eliminaron solamente seis directorios /tmp de Etapa 10, dos proyectos de
volúmenes aislados, el proyecto Compose final y las copias locales de las dos
imágenes de aplicación en la VM de producción. El uso de disco volvió de 93 %
a 83 %. No se eliminó ningún volumen, contenedor, imagen OCI, colección o dato
productivo.

La clave OS Login temporal se retiró. Permanecieron exactamente las dos claves
previas. El snapshot siguió READY con 58,891,150,336 bytes.

## Rollback

La revisión canónica anterior completa es
af5ab60b418bc931c4c4cabc8b8ef92893325fb6:

| Componente | Digest |
| --- | --- |
| Backend | sha256:c710984c1c3d42959bf54ef387490903a06aa9eb92a4c00acdeb6c26ee5c72ae |
| Frontend | sha256:8feb146ec8092fc4df480331015a71e5271eaa255daa8cb3b5454d97aedbb296 |
| Runtime GPU | sha256:de0833bd3afd746a50281ba867b1504a836bcde54b493bf9c65c3d9c2a389179 |
| Modelo | sha256:0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0 |

El archivo rollback-plan-af5ab60b….json fue validado contra su
hemovet.release/v1. Selecciona también la colección y fingerprint RAG exactos.
No requiere tags mutables. El rollback coordinado y repetible fue probado en
Etapa 9; en Etapa 10 el estado público anterior nunca se sustituyó.

## Costos

- GPU: 0.1248675 horas. Con el techo on-demand documentado de USD 0.706832276/h,
  el máximo estimado es USD 0.0883; Spot real es inferior y la factura exacta
  no fue verificada.
- Snapshot: no se creó uno nuevo; continúa el costo previo estimado de
  aproximadamente USD 2.74/mes.
- Artifact Registry: se añadieron manifests y capas de tres imágenes; el costo
  depende de deduplicación y facturación real.
- GitHub-hosted runners: consumo del run 30794470808, sin importe GCP.

## Riesgos pendientes

1. MEDIO — La revisión está aceptada, pero no hizo cutover público. Etapa 11
   debe validar backups, ventana, cancelación y rollback antes de reemplazar el
   stack anterior.
2. MEDIO — Producción conserva Ollama local, Default Compute SA, SSH legado y
   secrets de emergencia por diseño reversible.
3. BAJO — Las pruebas visuales no críticas conservan fixtures desactualizados
   del tour. No afecta los 8 E2E críticos ni los 19 casos funcionales, pero
   conviene normalizarlas en mantenimiento separado.
4. MEDIO — El descarte silencioso de red produjo el timeout normativo HTTP 504
   después de 10.2 segundos. La indisponibilidad inmediata conserva 503 y el
   frontend evita nuevos envíos al observar chat_ready=false, pero la ventana de
   Etapa 11 debe decidir si se reduce ese timeout antes del cutover.
5. BAJO — La IP privada GPU continúa vinculada a la instancia; su estabilidad
   depende de no recrearla.

## Estado del repositorio

El merge funcional está en main. Este informe, los manifiestos y las pruebas de
evidencia se versionan después en la rama dedicada para no generar un nuevo
GITHUB_SHA de aplicación y no invalidar la revisión aceptada. dips.md se
mantiene sin seguimiento y con hash intacto.

## Decisión de avance

La revisión final está publicada y aceptada de extremo a extremo en aislamiento;
producción, datos y tráfico permanecen en el estado anterior. Etapa 11 puede
planificarse únicamente tras aprobación explícita y una ventana controlada.
