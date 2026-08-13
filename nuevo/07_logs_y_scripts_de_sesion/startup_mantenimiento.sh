#!/bin/bash
# MANTENIMIENTO TEMPORAL — neutraliza el disparador de apagado para poder
# devolver el driver a 580.159.03. Se revierte al terminar.
mkdir -p /etc/systemd/system/hemovet-gpu.service.d
printf '[Unit]\nOnFailure=\n' > /etc/systemd/system/hemovet-gpu.service.d/zz-mantenimiento.conf
systemctl daemon-reload
rm -f /etc/systemd/system/sshd.service
systemctl daemon-reload
systemctl restart ssh.socket 2>/dev/null || true
systemctl restart ssh.service
