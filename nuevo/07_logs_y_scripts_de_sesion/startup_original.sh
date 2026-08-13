#!/bin/bash
rm -f /etc/systemd/system/sshd.service
systemctl daemon-reload
systemctl restart ssh.socket 2>/dev/null || true
systemctl restart ssh.service