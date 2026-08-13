#!/bin/bash
# PREVENCION: fija driver Y kernel, y excluye NVIDIA de unattended-upgrades.
# Es la pieza que faltaba: validate-host.sh DECLARA el driver esperado y nada
# IMPEDIA que apt lo cambiara. Corto a proposito: cabe en la ventana de arranque.
exec > >(tee -a /var/log/hemovet-prevencion.log|logger -t hemovet-prev -s 2>/dev/console) 2>&1
echo "HEMOVET-PREV: inicio $(date -u +%FT%TZ)"
rm -f /etc/systemd/system/sshd.service; systemctl daemon-reload
systemctl restart ssh.socket 2>/dev/null || true; systemctl restart ssh.service

NV=$(dpkg -l | awk '/^ii/ && $2 ~ /^(lib)?nvidia/ {print $2}' | sed 's/:amd64//' | tr '\n' ' ')
KR=$(dpkg -l | awk '/^ii/ && $2 ~ /^linux-(image|headers|modules|modules-nvidia)/ {print $2}' | tr '\n' ' ')
apt-mark hold $NV $KR linux-image-gcp linux-headers-gcp >/dev/null 2>&1
echo "HEMOVET-PREV: holds=$(apt-mark showhold | wc -l)"

cat > /etc/apt/apt.conf.d/51hemovet-nvidia-blacklist <<'CONF'
// deploy/gpu/validate-host.sh DECLARA el driver esperado y nada IMPEDIA que apt
// lo cambiara: el 8-ago-2026 unattended-upgrades subio el userspace a 580.173.02
// y anadio el kernel 6.17.0-1022, para el que no existe modulo 580.159.03.
// El host dejo de pasar la validacion de arranque. Esta es la prevencion.
Unattended-Upgrade::Package-Blacklist {
    "nvidia-";
    "libnvidia-";
    "cuda-";
    "linux-modules-nvidia-";
    "linux-image-";
    "linux-headers-";
};
CONF
echo "HEMOVET-PREV: blacklist=$([ -f /etc/apt/apt.conf.d/51hemovet-nvidia-blacklist ] && echo escrita)"
echo "HEMOVET-PREV: salvaguarda=$(systemctl is-enabled hemovet-gpu-failure-shutdown 2>&1)"
echo "HEMOVET-PREV: kernels instalados=$(ls /boot/vmlinuz-* 2>/dev/null | tr '\n' ' ')"
echo "HEMOVET-PREV: userspace=$(dpkg -l | awk '/^ii/ && $2=="nvidia-utils-580-server"{print $3}')"
echo "HEMOVET-PREV: FIN-OK"
