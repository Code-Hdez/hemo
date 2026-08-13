#!/bin/bash
# Restaura el host de HemoVet al estado exacto sobre el que corrió la línea base
# del 7-ago-2026: kernel 6.17.0-1021-gcp con el módulo NVIDIA 580.159.03 y el
# espacio de usuario a juego. Todo en chroot sobre el disco montado: cero
# arranques de la VM con GPU, que es un recurso escaso por STOCKOUT.
set -uo pipefail
R=/mnt/gpu
SNAP20=https://snapshot.ubuntu.com/ubuntu/20260720T000000Z
VER=580.159.03-0ubuntu0.24.04.1
KMOD=6.17.0-1021.24~24.04.1

sudo mount /dev/sdb16 $R/boot 2>/dev/null; sudo mount /dev/sdb15 $R/boot/efi 2>/dev/null
for d in proc sys dev dev/pts run; do sudo mount --bind /$d $R/$d 2>/dev/null; done
sudo cp /etc/resolv.conf $R/etc/resolv.conf

echo "=== kernels en /boot ==="; ls $R/boot/vmlinuz-* | sed 's#.*vmlinuz-##' | tr '\n' ' '; echo

sudo chroot $R /bin/bash -euo pipefail <<CHROOT
export DEBIAN_FRONTEND=noninteractive
echo "deb [trusted=yes] $SNAP20 noble-updates restricted" > /etc/apt/sources.list.d/hemovet-snap20.list
apt-get update -qq 2>&1 | tail -2

echo "### quitar holds previos para poder operar"
apt-mark unhold \$(apt-mark showhold) >/dev/null 2>&1 || true

echo "### userspace -> $VER"
apt-get install -y --allow-downgrades --allow-change-held-packages \
  libnvidia-cfg1-580-server=$VER libnvidia-compute-580-server=$VER \
  nvidia-compute-utils-580-server=$VER nvidia-kernel-common-580-server=$VER \
  nvidia-utils-580-server=$VER nvidia-firmware-580-server-580.159.03=$VER 2>&1 | tail -4

echo "### modulo del kernel 1021 (build pre-+3, embebe 580.159.03)"
apt-get install -y --allow-downgrades \
  linux-modules-nvidia-580-server-open-6.17.0-1021-gcp=$KMOD 2>&1 | tail -4

echo "### version real del .ko instalado"
modinfo -F version /lib/modules/6.17.0-1021-gcp/kernel/nvidia-580-server-open/nvidia.ko* 2>/dev/null \
  || find /lib/modules/6.17.0-1021-gcp -name 'nvidia.ko*' -exec modinfo -F version {} \; 2>/dev/null | head -1

echo "### arrancar por defecto el kernel 1021"
sed -i 's/^GRUB_DEFAULT=.*/GRUB_DEFAULT="gnulinux-advanced-\$(grub-probe --target=fs_uuid \/boot 2>\/dev\/null)>gnulinux-6.17.0-1021-gcp-advanced-\$(grub-probe --target=fs_uuid \/ 2>\/dev\/null)"/' /etc/default/grub || true
grep -n '^GRUB_DEFAULT' /etc/default/grub

echo "### prevencion: holds del driver Y del kernel"
apt-mark hold \$(dpkg -l | awk '/^ii/ && \$2 ~ /^(lib)?nvidia/ {print \$2}' | sed 's/:amd64//') \
  linux-image-6.17.0-1021-gcp linux-modules-6.17.0-1021-gcp \
  linux-modules-nvidia-580-server-open-6.17.0-1021-gcp \
  linux-image-gcp linux-headers-gcp linux-modules-nvidia-580-server-open-gcp >/dev/null 2>&1 || true
echo "holds: \$(apt-mark showhold | wc -l)"

cat > /etc/apt/apt.conf.d/51hemovet-nvidia-blacklist <<'CONF'
// deploy/gpu/validate-host.sh DECLARA el driver esperado y nada IMPEDIA que apt
// lo cambiara: el 8-ago-2026 unattended-upgrades subio el userspace a 580.173.02
// y anadio el kernel 6.17.0-1022, para el que no existe modulo 580.159.03.
// El host dejo de pasar la validacion de arranque y se apagaba solo.
Unattended-Upgrade::Package-Blacklist {
    "nvidia-";
    "libnvidia-";
    "cuda-";
    "linux-modules-nvidia-";
    "linux-image-";
    "linux-headers-";
};
CONF
echo "blacklist: escrita"

rm -f /etc/apt/sources.list.d/hemovet-snap20.list
apt-get update -qq 2>&1 | tail -1
echo "### estado final"
dpkg -l | awk '/^ii/ && \$2 ~ /nvidia-utils-580-server|linux-modules-nvidia/ {print "  ", \$2, \$3}'
CHROOT
RC=$?
echo "=== chroot rc=$RC ==="

echo "=== regenerar grub con el kernel 1021 por defecto ==="
sudo chroot $R /bin/bash -c "update-grub 2>&1 | tail -6"

echo "=== desmontar ==="
for d in run dev/pts dev sys proc; do sudo umount -l $R/$d 2>/dev/null; done
sudo umount -l $R/boot/efi $R/boot 2>/dev/null
sync
echo "LISTO"
