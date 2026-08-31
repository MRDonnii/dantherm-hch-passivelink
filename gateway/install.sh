#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: sudo gateway/install.sh --device /dev/serial/by-id/YOUR_ADAPTER [--port 4196]"
}

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this installer with sudo." >&2
  exit 1
fi

device=""
port="4196"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --device)
      device=${2:-}
      shift 2
      ;;
    --port)
      port=${2:-}
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z ${device} || ${device} != /dev/serial/by-id/* ]]; then
  echo "--device must be a stable /dev/serial/by-id/... path." >&2
  exit 2
fi
if [[ ! ${port} =~ ^[0-9]+$ ]] || (( port < 1 || port > 65535 )); then
  echo "--port must be between 1 and 65535." >&2
  exit 2
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

apt-get update
apt-get install -y python3 python3-venv python3-pip

if ! id passivelink >/dev/null 2>&1; then
  useradd --system --home /opt/dantherm-passivelink \
    --shell /usr/sbin/nologin --groups dialout passivelink
else
  usermod -aG dialout passivelink
fi

install -d -o passivelink -g passivelink /opt/dantherm-passivelink
install -d -o root -g passivelink -m 0750 /etc/dantherm-passivelink
install -o passivelink -g passivelink -m 0755 \
  "${script_dir}/passivelink_gateway.py" \
  /opt/dantherm-passivelink/passivelink_gateway.py
install -o passivelink -g passivelink -m 0644 \
  "${script_dir}/temperature_snapshot.py" \
  /opt/dantherm-passivelink/temperature_snapshot.py

if [[ ! -x /opt/dantherm-passivelink/venv/bin/python ]]; then
  runuser -u passivelink -- python3 -m venv /opt/dantherm-passivelink/venv
fi
runuser -u passivelink -- \
  /opt/dantherm-passivelink/venv/bin/pip install --upgrade pip
runuser -u passivelink -- \
  /opt/dantherm-passivelink/venv/bin/pip install pyserial==3.5

install -o root -g root -m 0644 \
  "${script_dir}/dantherm-passivelink.service" \
  /etc/systemd/system/dantherm-passivelink.service

config_file=/etc/dantherm-passivelink/gateway.env
if [[ -e ${config_file} ]]; then
  cp --archive "${config_file}" "${config_file}.previous"
fi
{
  printf 'RS485_DEVICE=%s\n' "${device}"
  printf 'GATEWAY_BIND=0.0.0.0\n'
  printf 'GATEWAY_PORT=%s\n' "${port}"
} > "${config_file}"
chown root:passivelink "${config_file}"
chmod 0640 "${config_file}"

systemctl daemon-reload
systemctl enable --now dantherm-passivelink.service
systemctl restart dantherm-passivelink.service

echo
echo "Dantherm PassiveLink gateway installed."
systemctl --no-pager --full status dantherm-passivelink.service || true
