#!/bin/bash
# MANTENIMIENTO TEMPORAL. Devuelve el host al driver que declara
# deploy/gpu/validate-host.sh (580.159.03) y aplica la prevencion que faltaba.
# Corre como root al arrancar, antes que hemovet-gpu.service (que espera a
# docker.service). Saca SSH del camino critico: no hay ventana que perder.
exec > >(tee -a /var/log/hemovet-restauracion.log|logger -t hemovet-restaurar -s 2>/dev/console) 2>&1
set -uo pipefail
echo "HEMOVET-RESTAURAR: inicio $(date -u +%FT%TZ)"

DROPIN=/etc/systemd/system/hemovet-gpu.service.d/zz-mantenimiento.conf
mkdir -p /etc/systemd/system/hemovet-gpu.service.d
printf '[Unit]\nOnFailure=\n' > "$DROPIN"
systemctl daemon-reload
systemctl stop hemovet-gpu-failure-shutdown.service 2>/dev/null
echo "HEMOVET-RESTAURAR: disparador neutralizado, OnFailure=[$(systemctl show hemovet-gpu.service -p OnFailure --value)]"

rm -f /etc/systemd/system/sshd.service; systemctl daemon-reload
systemctl restart ssh.socket 2>/dev/null || true; systemctl restart ssh.service

SNAP="https://snapshot.ubuntu.com/ubuntu/20260715T000000Z"
VER="580.159.03-0ubuntu0.24.04.1"
echo "deb [trusted=yes] $SNAP noble-updates restricted" > /etc/apt/sources.list.d/hemovet-snapshot-nvidia.list

dpkg --configure -a
DEBIAN_FRONTEND=noninteractive apt-get -y -f install
apt-get update -qq
if ! apt-cache madison nvidia-driver-580-server | grep -q "$VER"; then
  echo "HEMOVET-RESTAURAR: ABORTA, $VER no disponible"
  rm -f /etc/apt/sources.list.d/hemovet-snapshot-nvidia.list "$DROPIN"
  systemctl daemon-reload
  echo "HEMOVET-RESTAURAR: FIN-ABORTADO"; exit 1
fi
echo "HEMOVET-RESTAURAR: $VER disponible"

DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades --allow-change-held-packages \
  libnvidia-cfg1-580-server=$VER libnvidia-compute-580-server=$VER \
  nvidia-compute-utils-580-server=$VER nvidia-kernel-common-580-server=$VER \
  nvidia-utils-580-server=$VER nvidia-firmware-580-server-580.159.03=$VER
echo "HEMOVET-RESTAURAR: downgrade userspace rc=$?"

DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
  "linux-modules-nvidia-580-server-open-$(uname -r)=$VER" \
  || DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
     "linux-modules-nvidia-580-server-open-$(uname -r)"
echo "HEMOVET-RESTAURAR: modulo kernel rc=$?"

apt-mark hold $(dpkg -l | awk '/^ii/ && $2 ~ /^(lib)?nvidia/ {print $2}' | sed 's/:amd64//') \
  "linux-image-$(uname -r)" "linux-headers-$(uname -r)" \
  linux-image-gcp linux-headers-gcp linux-modules-nvidia-580-server-open-gcp

cat > /etc/apt/apt.conf.d/51hemovet-nvidia-blacklist <<'CONF'
// deploy/gpu/validate-host.sh DECLARA el driver esperado y nada IMPEDIA que apt
// lo cambiara: el 8-ago-2026 unattended-upgrades subio el userspace a 580.173.02
// y el host dejo de arrancar. Esta es la prevencion que faltaba.
Unattended-Upgrade::Package-Blacklist {
    "nvidia-";
    "libnvidia-";
    "cuda-";
    "linux-modules-nvidia-";
};
CONF

rm -f /etc/apt/sources.list.d/hemovet-snapshot-nvidia.list
apt-get update -qq
echo "HEMOVET-RESTAURAR: holds -> $(apt-mark showhold | tr '\n' ' ')"
echo "HEMOVET-RESTAURAR: instalado -> $(dpkg -l | awk '/^ii/ && $2=="nvidia-utils-580-server"{print $3}')"
echo "HEMOVET-RESTAURAR: FIN-OK $(date -u +%FT%TZ)"
