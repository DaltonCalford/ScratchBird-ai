#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

: "${SCRATCHBIRD_AI_BRIDGE_HOST:=127.0.0.1}"
: "${SCRATCHBIRD_AI_BRIDGE_PORT:=3095}"
: "${SCRATCHBIRD_AI_ADAPTER_MODE:=http}"
: "${SCRATCHBIRD_AI_HTTP_BASE_URL:=http://${SCRATCHBIRD_AI_BRIDGE_HOST}:${SCRATCHBIRD_AI_BRIDGE_PORT}}"
: "${SCRATCHBIRD_AI_BRIDGE_LOG:=/tmp/scratchbird-ai-bridge.log}"

cleanup() {
  if [[ -n "${BRIDGE_PID:-}" ]]; then
    kill "${BRIDGE_PID}" >/dev/null 2>&1 || true
    wait "${BRIDGE_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting ScratchBird AI HTTP bridge..."
python3 -m scratchbird_ai.http_bridge >"${SCRATCHBIRD_AI_BRIDGE_LOG}" 2>&1 &
BRIDGE_PID=$!

echo "Bridge pid: ${BRIDGE_PID}"
echo "Bridge log: ${SCRATCHBIRD_AI_BRIDGE_LOG}"
sleep 1

echo "Starting ScratchBird AI MCP server (adapter mode=${SCRATCHBIRD_AI_ADAPTER_MODE})..."
exec python3 -m scratchbird_ai.mcp_server
