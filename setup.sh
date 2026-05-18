#!/usr/bin/env bash
# =============================================================================
# setup.sh — One-command first-time setup for DIY Challenge Repo
#
# Run this once after cloning:
#   git clone --recurse-submodules https://github.com/vasu536/DIY-Challenge-Repo.git
#   cd DIY-Challenge-Repo
#   bash setup.sh [PROFILE]
#
# PROFILE: jetson | raspi | laptop  (default: laptop)
#
# What this script does:
#   1. Initialises / updates git submodules (third-party packages)
#   2. Applies build-fix patches to three of those packages
#   3. Builds the third-party workspace (third_party_ws)
#   4. Builds the DIY packages (challenge_bringup, localization, etc.)
#   5. Runs the health check
#
# Prerequisites:
#   - ROS 2 Humble installed (/opt/ros/humble/setup.bash must exist)
#   - rosdep initialised (sudo rosdep init + rosdep update)
#   - git, colcon-common-extensions, python3-pip installed
# =============================================================================

set -euo pipefail

PROFILE="${1:-laptop}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THIRD_PARTY="$REPO_ROOT/third_party_ws"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[setup]${NC} $*"; }
warn()  { echo -e "${YELLOW}[setup]${NC} $*"; }
error() { echo -e "${RED}[setup] ERROR:${NC} $*" >&2; }

# ── 0. Sanity checks ──────────────────────────────────────────────────────────
if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  error "ROS 2 Humble not found at /opt/ros/humble/setup.bash"
  error "Install it first: https://docs.ros.org/en/humble/Installation.html"
  exit 1
fi

if ! command -v colcon &>/dev/null; then
  error "colcon not found. Install it:"
  error "  sudo apt install python3-colcon-common-extensions"
  exit 1
fi

# ── 1. Submodules ─────────────────────────────────────────────────────────────
info "Step 1/5 — Initialising git submodules..."
cd "$REPO_ROOT"
git submodule update --init --recursive
info "  All submodules checked out."

# ── 2. Apply patches ──────────────────────────────────────────────────────────
info "Step 2/5 — Applying build-fix patches to third-party packages..."

apply_patch() {
  local pkg="$1"
  local patchfile="$REPO_ROOT/patches/${pkg}.patch"
  local pkgdir="$THIRD_PARTY/src/${pkg}"

  if [[ ! -f "$patchfile" ]]; then
    warn "  No patch file for $pkg — skipping."
    return
  fi

  # Check if already applied (git apply --check returns 0 if clean)
  if git -C "$pkgdir" apply --check --reverse "$patchfile" &>/dev/null; then
    info "  $pkg: patch already applied, skipping."
  elif git -C "$pkgdir" apply --check "$patchfile" &>/dev/null; then
    git -C "$pkgdir" apply "$patchfile"
    info "  $pkg: patch applied."
  else
    warn "  $pkg: patch cannot be applied cleanly (may be outdated). Skipping."
    warn "  Check patches/${pkg}.patch and apply manually if needed."
  fi
}

apply_patch lidar_imu_calib
apply_patch livox_ros_driver2
apply_patch ndt_omp_ros2

# ── 3. Install ROS dependencies ───────────────────────────────────────────────
info "Step 3/5 — Installing ROS dependencies (rosdep)..."
source /opt/ros/humble/setup.bash
rosdep install --from-paths "$THIRD_PARTY/src" "$REPO_ROOT/src" \
               --ignore-src -r -y 2>&1 | tail -5

# ── 4. Build third-party workspace ────────────────────────────────────────────
info "Step 4/5 — Building third-party workspace (this takes a few minutes)..."
cd "$THIRD_PARTY"
colcon build --symlink-install 2>&1 | tail -20
source "$THIRD_PARTY/install/setup.bash"
info "  third_party_ws build complete."

# ── 5. Build DIY packages ─────────────────────────────────────────────────────
info "Step 5/5 — Building DIY packages..."
cd "$REPO_ROOT"
source scripts/env.sh "$PROFILE"

# Go up to the enclosing ros2_ws if this repo is inside one
ROS2_WS="$(cd "$REPO_ROOT/../.." && pwd)"
if [[ -f "$ROS2_WS/src/$(basename "$REPO_ROOT")/src/challenge_bringup/package.xml" ]]; then
  # We're inside ~/ros2_ws/src/DIY-Challenge-Repo — build from the ws root
  cd "$ROS2_WS"
else
  # Standalone clone — build from repo root
  cd "$REPO_ROOT"
fi

colcon build --symlink-install \
  --packages-select \
    challenge_bringup \
    diy_cmd_vel_mux \
    diy_estop_controller \
    diy_robot_description \
    diy_localization 2>&1 | tail -20

info ""
info "============================================="
info "  Setup complete! Next steps:"
info "============================================="
info "  1. Source the environment:"
info "     source $REPO_ROOT/scripts/env.sh $PROFILE"
info ""
info "  2. Run the health check:"
info "     $REPO_ROOT/scripts/health_check.sh $PROFILE"
info ""
info "  3. Launch the robot:"
info "     $REPO_ROOT/scripts/run_robot.sh $PROFILE"
info "============================================="
