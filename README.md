# DIY Challenge Repo

ROS 2 Humble · Jetson Nano · Hesai QT64 · FAST-LIO2 · Nav2

Autonomous robot software stack for the DIY Robot Challenge 2026.  
Full documentation: **[docs/DIY_Challenge_Robot_Guide.pdf](docs/DIY_Challenge_Robot_Guide.pdf)**

---

## Quick Start

```bash
# 1. Clone with all third-party packages
git clone --recurse-submodules https://github.com/vasu536/DIY-Challenge-Repo.git
cd DIY-Challenge-Repo

# 2. Build everything (patches + rosdep + colcon)
bash setup.sh jetson          # or: laptop | raspi

# 3. Source the environment
source scripts/env.sh jetson

# 4. Verify hardware is ready
scripts/health_check.sh jetson

# 5. Launch the robot
scripts/run_robot.sh jetson
```

> **Cloned without `--recurse-submodules`?**  
> Run `git submodule update --init --recursive` to populate `third_party_ws/src/`.

---

## Repository Layout

```
DIY-Challenge-Repo/
├── src/                        ← ROS 2 packages (your code)
│   ├── challenge_bringup/      ← Top-level launch, Nav2 config, maps
│   ├── diy_cmd_vel_mux/        ← Priority-based velocity multiplexer
│   ├── diy_estop_controller/   ← STM32 heartbeat watchdog / e-stop
│   ├── diy_localization/       ← FAST-LIO2 + EKF1 + EKF2 + navsat
│   └── diy_robot_description/  ← URDF / robot_state_publisher
├── third_party_ws/src/         ← Git submodules (auto-cloned)
│   ├── FAST_LIO/               ← Lidar-inertial odometry
│   ├── LIO-SAM/                ← Offline mapping (loop closure)
│   ├── imu_utils_ros2_humble/  ← IMU Allan variance calibration
│   ├── lidar_imu_calib/        ← Lidar↔IMU extrinsic calibration
│   ├── livox_ros_driver2/      ← Hesai QT64 lidar driver
│   └── ndt_omp_ros2/           ← NDT-based scan matching
├── scripts/                    ← Operational shell scripts
├── profiles/                   ← Device environment files
├── patches/                    ← Build-fix patches applied by setup.sh
├── docs/                       ← PDF guide + source generator
└── setup.sh                    ← One-command first-time setup
```

---

## Hardware Stack

| Component | Part |
|-----------|------|
| Compute | NVIDIA Jetson Nano (4 GB, JetPack 5.x) |
| Lidar | Hesai QT64 (64-beam, 10 Hz, Ethernet) |
| Camera / IMU | Intel RealSense D435i |
| Motor controller | STM32 via micro-ROS (USB serial) |
| GPS | UBLOX (optional, for EKF2 global fusion) |

---

## Documentation Guide

The **[DIY_Challenge_Robot_Guide.pdf](docs/DIY_Challenge_Robot_Guide.pdf)** is the primary reference. Use the table below to jump to what you need:

| I want to… | PDF Section |
|---|---|
| Understand the overall system design and node graph | §1 — Repository Structure & Architecture |
| Learn what each ROS 2 package does | §2 — Package Reference |
| Tune SLAM / EKF / Nav2 parameters | §3 — Configuration & Calibration |
| Switch between Jetson / laptop / Raspberry Pi | §4 — Device Profiles |
| **Set up the robot from scratch (new hardware)** | **§5 — First-Time Setup on Robot Hardware** |
| SSH into the Jetson / headless access | §5.6 — Accessing the Jetson Nano |
| Understand GPU usage and lock CPU/GPU clocks | §5.7 — Jetson Nano Performance |
| Build and connect the micro-ROS agent (STM32) | §5.5 — micro-ROS Agent Setup |
| Calibrate the IMU or lidar-IMU extrinsics | §6 — Calibration Procedures |
| Run on competition day (pre-flight, launch, E-stop) | §7 — Competition Day Operations |
| Replay a bag / debug a node on your laptop | §8 — Developer Workflows |
| Look up what a script does and its arguments | §9 — Scripts Reference |
| Fix a common error or sensor issue | §10 — Troubleshooting |
| Add a new sensor, package, or swap the SLAM algorithm | §11 — Extending the Codebase |

---

## Scripts Overview

| Script | Purpose |
|--------|---------|
| `setup.sh [PROFILE]` | First-time setup: submodules → patches → rosdep → build |
| `scripts/env.sh [PROFILE]` | Source all workspace overlays in the correct order |
| `scripts/run_robot.sh [PROFILE]` | Launch the full robot stack |
| `scripts/health_check.sh [PROFILE]` | Pre-flight hardware and topic verification |
| `scripts/record_bag.sh [PROFILE]` | Record a labelled rosbag |
| `scripts/replay_bag.sh [BAG]` | Replay a bag on laptop with correct clock |
| `scripts/calibrate_imu.sh [PROFILE]` | IMU Allan variance calibration |
| `scripts/calibrate_extrinsics.sh [PROFILE]` | Lidar↔IMU extrinsic calibration |
| `scripts/debug_robot.sh [PROFILE]` | Single-node debug launch |
| `scripts/deploy_bundle.sh` | Push updated configs to the robot over SSH |

---

## Device Profiles

Profiles in `profiles/` set environment variables for each platform.  
Always source via `scripts/env.sh` (not directly):

```bash
source scripts/env.sh jetson   # Jetson Nano — full hardware stack
source scripts/env.sh laptop   # Development laptop — simulation / bag replay
source scripts/env.sh raspi    # Raspberry Pi — lightweight subset
```

---

## Third-Party Packages

These are managed as **git submodules** — they are not committed inline to keep the repo small. `setup.sh` initialises them and applies three build-fix patches automatically.

| Package | Purpose | Branch |
|---------|---------|--------|
| [FAST_LIO](https://github.com/hku-mars/FAST_LIO) | Lidar-inertial odometry (primary SLAM) | `ROS2` |
| [LIO-SAM](https://github.com/TixiaoShan/LIO-SAM) | Offline mapping with loop closure | `ros2` |
| [imu_utils_ros2_humble](https://github.com/HYD-PG/imu_utils_ros2_humble) | IMU noise calibration | `main` |
| [lidar_imu_calib](https://github.com/KnightSnape/lidar_imu_calib) | Lidar↔IMU extrinsic calibration | `main` |
| [livox_ros_driver2](https://github.com/Livox-SDK/livox_ros_driver2) | Hesai QT64 lidar driver | `master` |
| [ndt_omp_ros2](https://github.com/rsasaki0109/ndt_omp_ros2) | NDT-OMP scan matching | `humble` |

Build-fix patches for `lidar_imu_calib`, `livox_ros_driver2`, and `ndt_omp_ros2` live in `patches/` and are applied by `setup.sh`.

---

## Prerequisites

- Ubuntu 22.04 (JetPack 5.x on Jetson Nano)
- ROS 2 Humble (`/opt/ros/humble/setup.bash` must exist)
- `colcon-common-extensions`, `python3-rosdep`, `git`
- Jetson Nano: add user to `dialout` group for STM32 USB serial access

See **§5.1** of the PDF guide for the full prerequisites list.

---

## License

MIT — see [LICENSE](LICENSE) if present, otherwise use freely with attribution.
