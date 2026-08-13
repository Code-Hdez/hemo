sudo systemctl stop hemovet-gpu-failure-shutdown.service 2>/dev/null; sudo mkdir -p /etc/systemd/system/hemovet-gpu.service.d; printf "[Unit]\nOnFailure=\n" | sudo tee /etc/systemd/system/hemovet-gpu.service.d/zz-mantenimiento.conf >/dev/null; sudo systemctl daemon-reload; echo "OnFailure ahora: [$(systemctl show hemovet-gpu.service -p OnFailure --value)]"
  sudo rmdir /etc/systemd/system/hemovet-gpu.service.d 2>/dev/null
  sudo systemctl daemon-reload
  echo -n "OnFailure de hemovet-gpu.service: "
  systemctl show hemovet-gpu.service -p OnFailure --value
  echo -n "salvaguarda: "
  systemctl is-enabled hemovet-gpu-failure-shutdown 2>&1
}
trap restaurar EXIT

echo "### 0 · neutralizar el disparador (paquete ya verificado: HTTP 200 en el snapshot)"
sudo mkdir -p /etc/systemd/system/hemovet-gpu.service.d
printf '[Unit]\nOnFailure=\n' | sudo tee "$DROPIN" >/dev/null
sudo systemctl daemon-reload
echo -n "OnFailure ahora: '"; echo -n "$(systemctl show hemovet-gpu.service -p OnFailure --value)"; echo "'"

echo "### 1 · reparar estado de apt si quedó a medias"
sudo dpkg --configure -a 2>&1 | tail -3
sudo DEBIAN_FRONTEND=noninteractive apt-get -y -f install 2>&1 | tail -3

echo "### 2 · snapshot como fuente temporal"
echo "deb [trusted=yes] $SNAP noble-updates restricted" | sudo tee "$LISTA" >/dev/null
sudo apt-get update -qq 2>&1 | tail -3
apt-cache madison nvidia-driver-580-server | grep -q "$VER" || { echo "ABORTA: $VER no disponible"; exit 1; }
echo "OK: $VER disponible"

echo "### 3 · downgrade del conjunto NVIDIA"
OBJ="libnvidia-cfg1-580-server=$VER libnvidia-compute-580-server=$VER"
OBJ="$OBJ nvidia-compute-utils-580-server=$VER nvidia-kernel-common-580-server=$VER"
OBJ="$OBJ nvidia-utils-580-server=$VER nvidia-firmware-580-server-580.159.03=$VER"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
  --allow-change-held-packages $OBJ 2>&1 | tail -10

echo "### 4 · modulo del kernel"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
  "linux-modules-nvidia-580-server-open-$(uname -r)=$VER" 2>&1 | tail -6 \
  || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades \
     "linux-modules-nvidia-580-server-open-$(uname -r)" 2>&1 | tail -6

echo "### 5 · apt-mark hold del driver Y del kernel"
sudo apt-mark hold $(dpkg -l | awk '/^ii/ && $2 ~ /^(lib)?nvidia/ {print $2}' | sed 's/:amd64//') \
  "linux-image-$(uname -r)" "linux-headers-$(uname -r)" \
  linux-image-gcp linux-headers-gcp linux-modules-nvidia-580-server-open-gcp 2>&1 | tail -8

echo "### 6 · excluir NVIDIA de unattended-upgrades"
sudo tee /etc/apt/apt.conf.d/51hemovet-nvidia-blacklist >/dev/null <<'CONF'
// deploy/gpu/validate-host.sh DECLARA el driver esperado y nada IMPEDIA que apt
// lo cambiara: el 8-ago-2026 unattended-upgrades subio el userspace a 580.173.02
// y el host dejo de arrancar. Esto es la prevencion que faltaba.
Unattended-Upgrade::Package-Blacklist {
    "nvidia-";
    "libnvidia-";
    "cuda-";
    "linux-modules-nvidia-";
};
CONF
echo "blacklist escrita"

echo "### 7 · estado final"
apt-mark showhold | head -25
dpkg -l | grep -E "nvidia-utils-580|libnvidia-compute-580|linux-modules-nvidia" | awk '{print $2,$3}'
