# Runtime GPU de HemoVet

Este bundle instala un servicio `systemd` idempotente que consume únicamente
la proyección GPU de un manifiesto `hemovet.release/v1`. No clona Git, no usa
`latest`, no contiene claves y no despliega la aplicación.

El servicio lee `hemovet-gpu-desired-release` desde metadata. Solo acepta
`pending_boot_validation`, `next_boot`, `update_while_running=false`, la imagen
OCI canónica de `ollama-runtime`, el digest del bundle instalado y el modelo
Qwen aprobado. La autenticación usa un token efímero de la service account de
la VM y un `DOCKER_CONFIG` en `/run`.

Archivos operativos:

- `install-bootstrap.sh`: instalación atómica del bundle y unidad `systemd`.
- `startup.sh`: configuración CDI, cuarentena reversible del runtime legado y
  reconciliación de boot.
- `reconcile-release.sh`: lock, validación, pull por digest, bootstrap del
  modelo, inferencia y estado aplicado.
- `validate-runtime.sh`: `/api/tags`, `/api/show`, `/api/ps`, inferencia L4 y
  métricas sin registrar el prompt ni la respuesta.
- `rollback-release.sh`: rollback manual a una revisión almacenada.
- `shutdown-on-failure.sh`: registra evidencia mínima y solicita el apagado
  del host cuando el bootstrap termina en estado fallido.
- `hemovet-gpu-failure-shutdown.service`: acción `OnFailure` del reconciliador;
  no se habilita por separado ni se ejecuta durante un arranque válido.

Estado persistente: `/var/lib/hemovet-gpu`. Pesos:
`hemovet_gpu_ollama_models`. Logs: `journalctl -u hemovet-gpu.service` y consola
serial. El reconciliador normal nunca sustituye un runtime activo; una revisión
nueva se aplica en el siguiente boot.

Si el contrato de revisión, el host o la validación del runtime fallan, systemd
ejecuta la unidad de fallo. Esta escribe de forma atómica y con modo `0600`
`/var/lib/hemovet-gpu/bootstrap-failure.json`, emite un evento sanitizado a
`journald` y consola serial, y solicita `systemctl --no-block poweroff`. El
runtime/modelo anterior y sus manifiestos no se eliminan. Para diagnosticar:

```bash
sudo systemctl status hemovet-gpu.service --no-pager
sudo journalctl -u hemovet-gpu.service \
  -u hemovet-gpu-failure-shutdown.service -b --no-pager
sudo cat /var/lib/hemovet-gpu/bootstrap-failure.json
```
