#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# scripts/env.sh — Environment bootstrap for DIY Challenge Robot
# ══════════════════════════════════════════════════════════════════════════════
# Source this file (do NOT execute it) to set up a competition-ready shell:
#
#   source scripts/env.sh [profile]
#
# Profile is read from:
#   1. First argument to this script (highest priority)
#   2. $DIY_ROBOT_PROFILE environment variable (already exported by profiles/*.env)
#   3. Hostname-based auto-detection heuristic
#   4. Fallback: laptop
#
# After sourcing, the full ROS 2 environment is active and all DIY_* variables
# are set according to the chosen profile.
# ══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Resolve repo root ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Determine profile ─────────────────────────────────────────────────────────
_profile="${1:-${DIY_ROBOT_PROFILE:-}}"

if [[ -z "${_profile}" ]]; then
    _host="$(hostname)"
    case "${_host}" in
        jetson*|nano*|orin*) _profile=jetson ;;
        raspi*|rpi*|pi*)     _profile=raspi  ;;
        *)                   _profile=laptop ;;
    esac
    echo "[env.sh] Auto-detected profile: ${_profile} (hostname=${_host})"
fi

_profile_file="${REPO_ROOT}/profiles/${_profile}.env"
if [[ ! -f "${_profile_file}" ]]; then
    echo "[env.sh] ERROR: Profile file not found: ${_profile_file}" >&2
    echo "[env.sh]        Available: $(ls "${REPO_ROOT}/profiles/")" >&2
    return 1 2>/dev/null || exit 1
fi

# shellcheck source=/dev/null
source "${_profile_file}"

# ── Source ROS 2 base ─────────────────────────────────────────────────────────
if [[ -f /opt/ros/humble/setup.bash ]]; then
    source /opt/ros/humble/setup.bash
else
    echo "[env.sh] WARNING: /opt/ros/humble/setup.bash not found — skipping base source" >&2
fi

# ── Source micro-ROS workspace ────────────────────────────────────────────────
if [[ -n "${DIY_MICRO_ROS_WS:-}" && -f "${DIY_MICRO_ROS_WS}/install/setup.bash" ]]; then
    source "${DIY_MICRO_ROS_WS}/install/setup.bash"
fi

# ── Source Hesai ROS 2 driver ─────────────────────────────────────────────────
if [[ -n "${DIY_HESAI_WS:-}" && -f "${DIY_HESAI_WS}/install/setup.bash" ]]; then
    source "${DIY_HESAI_WS}/install/setup.bash"
elif [[ -n "${DIY_HESAI_WS:-}" && -f "${DIY_HESAI_WS}/install/local_setup.bash" ]]; then
    source "${DIY_HESAI_WS}/install/local_setup.bash"
fi

# ── Source third-party workspace (FAST-LIO2, LIO-SAM, etc.) ──────────────────
if [[ -n "${DIY_THIRD_PARTY_WS:-}" && -f "${DIY_THIRD_PARTY_WS}/install/setup.bash" ]]; then
    source "${DIY_THIRD_PARTY_WS}/install/setup.bash"
fi

# ── Source main ROS 2 workspace ───────────────────────────────────────────────
if [[ -n "${DIY_ROS_WS:-}" && -f "${DIY_ROS_WS}/install/setup.bash" ]]; then
    source "${DIY_ROS_WS}/install/setup.bash"
fi

# ── Apply log level if set ─────────────────────────────────────────────────────
if [[ -n "${DIY_LOG_LEVEL:-}" ]]; then
    export RCUTILS_LOGGING_SEVERITY_THRESHOLD="${DIY_LOG_LEVEL}"
fi

echo "[env.sh] Environment ready. Profile=${DIY_ROBOT_PROFILE}"
echo "[env.sh] ROS_DISTRO=${ROS_DISTRO:-<not set>}, WS=${DIY_ROS_WS:-<not set>}"
