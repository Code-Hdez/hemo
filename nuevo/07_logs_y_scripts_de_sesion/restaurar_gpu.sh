#!/bin/bash
# Restauración del host al driver que declara deploy/gpu/validate-host.sh.
# El desenmascarado de la salvaguarda va encadenado en TODAS las salidas.
set -uo pipefail
SNAP="https://snapshot.ubuntu.com/ubuntu/20260715T000000Z"
VER="580.159.03-0ubuntu0.24.04.1"
LISTA=/etc/apt/sources.list.d/hemovet-snapshot-nvidia.list

desenmascarar() {
  sudo rm -f "$LISTA"
  sudo systemctl unmask hemovet-gpu-failure-shutdown.service 2>/dev/null
  echo "SALVAGUARDA: $(systemctl is-enabled hemovet-gpu-failure-shutdown 2>&1)"
}
trap desenmascarar EXIT

echo "### 1 · enmascarar la salvaguarda (paquete ya verificado por HTTP 200)"
sudo systemctl mask hemovet-gpu-failure-shutdown.service
echo "enmascarada: $(systemctl is-enabled hemovet-gpu-failure-shutdown 2>&1)"

echo "### 2 · anadir el snapshot como fuente temporal"
echo "deb [trusted=yes] $SNAP noble-updates restricted" | sudo tee "$LISTA" >/dev/null
sudo apt-get update -qq -o Dir::Etc::sourcelist="$LISTA" \
  -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup="0" 2>&1 | tail -3

echo "### 3 · VERIFICAR que la version esta disponible (aborta si no)"
if ! apt-cache madison nvidia-driver-580-server | grep -q "$VER"; then
  echo "ABORTA: $VER no disponible tras anadir el snapshot"
  exit 1
fi
echo "OK: $VER disponible"

echo "### 4 · downgrade del conjunto NVIDIA"
PKGS=$(dpkg -l | awk '/^ii/ && ($2 ~ /^(lib)?nvidia.*580/ || $2 ~ /^nvidia-firmware-580/) {print $2}' | tr '\n' ' ')
echo "instalados: $PKGS"
OBJ=""
for p in $PKGS; do
  case "$p" in
    nvidia-firmware-580-server-*) OBJ="$OBJ nvidia-firmware-580-server-580.159.03=$VER" ;;
    libnvidia-nscq-580|nvidia-fabricmanager-580) : ;;   # NVLink: no aplica a un solo L4
    *) OBJ="$OBJ $p=$VER" ;;
  esac
done
echo "objetivo: $OBJ"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
  --allow-change-held-packages $OBJ 2>&1 | tail -12

echo "### 5 · modulo del kernel para 580.159.03"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
  "linux-modules-nvidia-580-server-open-$(uname -r)" 2>&1 | tail -5

echo "### 6 · apt-mark hold del driver Y del kernel"
sudo apt-mark hold $(dpkg -l | awk '/^ii/ && $2 ~ /^(lib)?nvidia/ {print $2}') \
  "linux-image-$(uname -r)" "linux-headers-$(uname -r)" \
  linux-image-gcp linux-headers-gcp linux-modules-nvidia-580-server-open-gcp 2>&1 | tail -6

echo "### 7 · excluir NVIDIA de unattended-upgrades"
sudo tee /etc/apt/apt.conf.d/51hemovet-nvidia-blacklist >/dev/null <<'CONF'
// La invariante del driver la declara deploy/gpu/validate-host.sh y nada impedia
// que apt la violara: el 8-ago-2026 unattended-upgrades subio el userspace a
// 580.173.02 y el host dejo de arrancar. Esto es la prevencion que faltaba.
Unattended-Upgrade::Package-Blacklist {
    "nvidia-";
    "libnvidia-";
    "cuda-";
    "linux-modules-nvidia-";
};
CONF
echo "blacklist escrita"

echo "### 8 · estado final antes de reiniciar"
apt-mark showhold | head -20
dpkg -l | grep -E "nvidia-utils-580|libnvidia-compute-580" | awk '{print $2,$3}'
