#!/data/data/com.termux/files/usr/bin/bash
# Очистка утечки Bun .so (libopentui.so) из /tmp Ubuntu-контейнера freebuff.
# Удаляет только файлы старше 30 минут, чтобы не трогать библиотеку живого процесса.
set -u
ROOTFS_TMP="/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/tmp"
find "$ROOTFS_TMP" -maxdepth 1 -type f -name '.*-00000000.so' -mmin +30 -delete 2>/dev/null || true
find "$ROOTFS_TMP/freebuff-bun-tmp" -maxdepth 1 -type f -name '.*-00000000.so' -mmin +30 -delete 2>/dev/null || true
exit 0
