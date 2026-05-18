# Reuse Plan Step 1 (From Betsybot-Software)

This document maps reusable legacy code to the 2026 SAD in [docs/diy-sad.html](docs/diy-sad.html) and defines the first migration baseline in this repository.

## What We Reuse Now

1. Motor/CAN control package from last year:
- Source: /home/vg1617/ros2_ws/src/Betsybot-Software/src/differential-drive
- Imported into this repo as: src/diy_motor_control_legacy
- Key behavior: subscribes `/cmd_vel`, drives TalonFX on `can1`, publishes wheel odom and joint states.

2. Joystick control launch pattern:
- Legacy reference: /home/vg1617/ros2_ws/src/Betsybot-Software/src/master_launch/launch/Joystick_drive.launch.py
- Implemented here in: src/challenge_bringup/launch/joystick_drive.launch.py
- Update: teleop output remapped to `/cmd_vel_joy` (SAD requires explicit mode gating).

3. Nav2 bringup/config skeleton:
- Legacy references:
  - /home/vg1617/ros2_ws/src/Betsybot-Software/src/betsybot/launch/bringup_launch.py
  - /home/vg1617/ros2_ws/src/Betsybot-Software/src/betsybot/config/nav2_params.yaml
- Implemented here in:
  - src/challenge_bringup/launch/challenge_master.launch.py
  - src/challenge_bringup/config/nav2_params.yaml
- SAD alignment updates:
  - Costmap observation source moved to `/hesai/points`
  - Planner set to Smac Hybrid
  - Controller set to MPPI

4. Collision monitor baseline:
- Legacy reference: /home/vg1617/ros2_ws/src/Betsybot-Software/src/betsybot/config/collision_monitor_params.yaml
- Implemented here in: src/challenge_bringup/config/collision_monitor_params.yaml
- Update: uses `/hesai/points`, outputs `/cmd_vel_safe`.

## What Exists In Legacy But Not Yet Reused

1. Hesai driver source tree exists in old repo and is already buildable via previous setup.
2. RealSense package exists in old repo but is usually better consumed from apt-installed `realsense2_ros`.
3. SuperOdom exists but SAD requires FAST-LIO2 for runtime odometry and LIO-SAM for offline mapping.

## Critical SAD Gaps (Must Build New)

1. E-stop path and fail-safe watchdog (STM32-centered, hardware priority).
2. Command arbitration node (joystick vs autonomous vs estop), producing `/cmd_vel_safe`.
3. Mission state machine and zone behavior switcher.
4. PCL obstacle classifier + map differencing.
5. EKF1/EKF2 configuration and navsat_transform wiring.

## First-Step Development Baseline Added Here

1. Reused motor package:
- src/diy_motor_control_legacy

2. New bringup package:
- src/challenge_bringup/package.xml
- src/challenge_bringup/CMakeLists.txt
- src/challenge_bringup/launch/challenge_master.launch.py
- src/challenge_bringup/launch/joystick_drive.launch.py
- src/challenge_bringup/config/nav2_params.yaml
- src/challenge_bringup/config/collision_monitor_params.yaml
- src/challenge_bringup/maps/static_map.yaml

## Action Plan (SAD-Aligned Next 5 Work Items)

1. Implement `diy_cmd_vel_mux` node:
- Inputs: `/cmd_vel_joy`, `/cmd_vel_nav`, `/estop_active`
- Output: `/cmd_vel_safe`
- Modes: JOYSTICK, AUTONOMOUS, ESTOP_LOCK

2. Integrate `diy_estop_controller` interface:
- Bridge STM32 status to ROS (`/estop_active`, heartbeat timeout)
- Force zero velocity on fail-safe.

3. Bring FAST-LIO2 + EKF online:
- FAST-LIO2 output to `/lidar_odometry`
- EKF1 local odom and EKF2 global map fusion with RTK.

4. Add mission scaffolding package:
- State transitions from SAD: WAIT -> NAVIGATE -> ZONE_ENTRY -> BEHAVIOR -> LAP_COMPLETE.

5. Add obstacle classifier package:
- RANSAC ground removal, clustering, class outputs to `/obstacle_class`.

## Notes

- Imported motor control package is legacy and tightly coupled to TalonFX/Phoenix6 and differential drive assumptions.
- It should be treated as a bootstrap implementation while the final STM32 + micro-ROS safety architecture is introduced.
