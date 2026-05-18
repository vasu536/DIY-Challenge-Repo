#!/usr/bin/env python3
"""
challenge_master.launch.py — Top-level competition bringup
══════════════════════════════════════════════════════════
Single file that starts the entire robot stack for competition or debug runs.
Every subsystem is gated by a boolean argument so the same file works whether
you are running the full competition stack on the Jetson, a lightweight relay
setup on the Raspberry Pi, or a laptop-only replay / debug session.

ARGUMENT → DEVICE PROFILE MAPPING
──────────────────────────────────
Each argument mirrors a  DIY_*  environment variable set by a device profile:
  profiles/jetson.env   — full hardware stack (all subsystems enabled)
  profiles/raspi.env    — lightweight relay (no localization, no Nav2)
  profiles/laptop.env   — debug/replay (no hardware drivers)

Source a profile, then launch:
  source scripts/env.sh jetson
  ros2 launch challenge_bringup challenge_master.launch.py

CLI overrides are also supported without editing this file:
  ros2 launch challenge_bringup challenge_master.launch.py use_nav2:=true mux_mode:=TELEOP

STARTUP ORDER
─────────────
   1. diy_robot_description  — publishes URDF / TF tree  (MUST be first)
   2. micro_ros_agent        — opens STM32 serial link (before estop reads topics)
   3. estop_controller_node  — reads STM32 state, publishes /estop_active
   4. cmd_vel_mux_node       — velocity arbitration; reads /estop_active for gating
   5. hesai_ros_driver       — lidar driver feeding FAST-LIO2
   6. realsense2_camera      — RGB-D + stereo IR + IMU
   7. localization stack     — FAST-LIO2 + EKF1 + navsat_transform + EKF2
   8. joystick_drive         — conditionally enabled
   9. differential_drive     — motor driver subscribing /cmd_vel_safe (mux output)
  10. nav2 bringup           — conditionally enabled
  11. rviz2                  — conditionally enabled (off by default to save resources)

Launch arguments (all correspond to DIY_* profile variables):
  use_joystick       bool  Enable joystick teleop          (default false)
  use_nav2           bool  Enable Nav2 autonomous stack     (default false)
  use_realsense      bool  Enable RealSense D435i driver    (default true)
  use_motor_driver   bool  Enable differential-drive node   (default true)
  use_hesai          bool  Enable Hesai QT64 lidar driver   (default true)
  use_micro_ros      bool  Enable micro-ROS agent (STM32)   (default true)
  use_localization   bool  Enable FAST-LIO2 + EKF stack     (default true)
  use_rviz           bool  Launch RViz2                     (default false)
  mux_mode           str   cmd_vel_mux startup mode         (default AUTONOMOUS)
  fastlio_config     str   FAST-LIO2 config filename        (see diy_localization/config/)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir     = get_package_share_directory('challenge_bringup')
    nav2_params = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')  # MPPI + behaviour config
    map_yaml    = os.path.join(pkg_dir, 'maps',   'static_map.yaml')   # prior map for Nav2

    # ── LaunchConfiguration handles (lazy substitutions) ──────────────────────
    # These are NOT yet resolved strings — they are substitution objects that
    # ROS 2 launch evaluates at start-up.  Pass them directly to IfCondition()
    # or as node parameters.  Do NOT use them in Python if/else; use an
    # OpaqueFunction for that (see localization.launch.py for an example).
    use_joystick     = LaunchConfiguration('use_joystick')
    use_nav2         = LaunchConfiguration('use_nav2')
    use_realsense    = LaunchConfiguration('use_realsense')
    use_motor_driver = LaunchConfiguration('use_motor_driver')
    use_hesai        = LaunchConfiguration('use_hesai')
    use_micro_ros    = LaunchConfiguration('use_micro_ros')
    use_localization = LaunchConfiguration('use_localization')
    use_rviz         = LaunchConfiguration('use_rviz')
    mux_mode         = LaunchConfiguration('mux_mode')
    fastlio_config   = LaunchConfiguration('fastlio_config')

    return LaunchDescription([

        # ── BLOCK 1: Argument declarations ────────────────────────────────────
        # Defaults match the jetson.env full-hardware profile.
        # Override per-session at the CLI without editing this file:
        #   ros2 launch challenge_bringup challenge_master.launch.py use_nav2:=true
        DeclareLaunchArgument('use_joystick',     default_value='false'),
        DeclareLaunchArgument('use_nav2',         default_value='false'),
        DeclareLaunchArgument('use_realsense',    default_value='true'),
        DeclareLaunchArgument('use_motor_driver', default_value='true'),
        DeclareLaunchArgument('use_hesai',        default_value='true'),
        DeclareLaunchArgument('use_micro_ros',    default_value='true'),
        DeclareLaunchArgument('use_localization', default_value='true'),
        DeclareLaunchArgument('use_rviz',         default_value='false'),
        DeclareLaunchArgument('mux_mode',         default_value='AUTONOMOUS'),
        DeclareLaunchArgument(
            'fastlio_config',
            default_value='fast_lio_hesai_qt64.yaml',
            # Change to swap sensor configs without editing this file
        ),

        # ── BLOCK 2: Robot description  (URDF → TF static transforms) ─────────
        # MUST be first.  robot_state_publisher reads the URDF and broadcasts
        # every joint as a static TF transform (base_link → lidar_link, imu_link,
        # camera_link, etc.).  All downstream nodes depend on these transforms
        # to project sensor data into robot-body coordinates.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory('diy_robot_description'),
                    'launch',
                    'description.launch.py',
                )
            ),
        ),

        # ── BLOCK 3: micro-ROS agent  (STM32 ↔ ROS 2 serial bridge) ──────────
        # Opens a serial link to the STM32 over USB.  The STM32 firmware runs a
        # micro-ROS executor that publishes:
        #   /stm32/heartbeat  — 10 Hz liveness signal (watchdog source for estop)
        #   /stm32/estop      — hardware e-stop button state
        # These become full ROS 2 topics only after this agent is running.
        # Serial device and baud rate read from DIY_MICRO_ROS_* env vars set by
        # the active device profile (scripts/env.sh).
        Node(
            package='micro_ros_agent',
            executable='micro_ros_agent',
            name='micro_ros_agent',
            output='screen',
            condition=IfCondition(use_micro_ros),   # skip on laptop / no-hardware runs
            arguments=[
                'serial',
                '--dev', os.environ.get('DIY_MICRO_ROS_SERIAL',   '/dev/ttyACM0'),
                '-b',    os.environ.get('DIY_MICRO_ROS_BAUDRATE',  '921600'),
            ],
        ),

        # ── BLOCK 4: E-stop controller  (advisory ROS mirror of STM32 state) ──
        # Listens to /stm32/estop (hardware button) and /stm32/heartbeat
        # (watchdog), then publishes /estop_active (Bool, latched QoS).
        # The mux (BLOCK 5) reads /estop_active and zeroes all velocity output.
        #
        # Always launched (no condition guard) — on a watchdog timeout (no
        # heartbeat for >0.5 s) it automatically sets estop=true so the robot
        # stops safely even if the STM32 or micro-ROS agent crashes mid-run.
        Node(
            package='diy_estop_controller',
            executable='estop_controller_node',
            name='estop_controller_node',
            output='screen',
        ),

        # ── BLOCK 5: cmd_vel multiplexer  (velocity source arbitration) ───────
        # Arbitrates between /cmd_vel_joy (joystick) and /cmd_vel_nav (Nav2)
        # and emits the winning command on /cmd_vel_safe.
        # Startup mode controls which source is active at launch:
        #   AUTONOMOUS — forward /cmd_vel_nav  (competition default)
        #   TELEOP     — forward /cmd_vel_joy  (manual driving / testing)
        #   ESTOP      — zero velocity regardless of any inputs
        # Switch mode at runtime:  ros2 param set /cmd_vel_mux_node mode TELEOP
        Node(
            package='diy_cmd_vel_mux',
            executable='cmd_vel_mux_node',
            name='cmd_vel_mux_node',
            output='screen',
            parameters=[{'mode': mux_mode}],
        ),

        # ── BLOCK 6: Hesai QT64 lidar driver ──────────────────────────────────
        # Connects to the lidar over UDP and publishes /hesai/points
        # (sensor_msgs/PointCloud2 @ ~10 Hz).  This is FAST-LIO2's primary
        # input for scan matching and map building.
        # Network settings come from DIY_HESAI_* env vars set by the profile.
        Node(
            package='hesai_ros_driver',
            executable='hesai_ros_driver_node',
            name='hesai_ros_driver',
            output='screen',
            condition=IfCondition(use_hesai),
            parameters=[{
                'device_ip':  os.environ.get('DIY_HESAI_IP',       '192.168.1.201'),
                'lidar_port': int(os.environ.get('DIY_HESAI_PORT',  '2368')),
                'frame_id':   os.environ.get('DIY_HESAI_FRAME_ID',  'lidar_link'),
            }],
        ),

        # ── BLOCK 7: RealSense D435i  (RGB-D + stereo IR + IMU) ───────────────
        # Publishes:
        #   /camera/color/image_raw         — RGB (recording / visual tasks)
        #   /camera/depth/image_rect_raw    — depth map
        #   /camera/infra1/image_rect_raw   — left rectified IR  (VSLAM input)
        #   /camera/infra2/image_rect_raw   — right rectified IR (VSLAM input)
        #   /camera/imu                     — 6-DOF IMU @ 200 Hz
        # IR emitter MUST be disabled — with it on the projected dot pattern
        # corrupts passive stereo feature matching in both IR cameras.
        Node(
            package='realsense2_camera',
            executable='realsense2_camera_node',
            name='realsense2_camera',
            output='screen',
            condition=IfCondition(use_realsense),
            parameters=[{
                'enable_color':         True,
                'enable_depth':         True,
                'enable_infra1':        True,
                'enable_infra2':        True,
                'enable_gyro':          True,
                'enable_accel':         True,
                'enable_infra_emitter': False,  # MUST be off for stereo VSLAM
            }],
        ),

        # ── BLOCK 8: Localisation stack  (FAST-LIO2 + EKF1 + EKF2 + navsat) ──
        # Delegates to localization.launch.py with fixed runtime arguments.
        # use_rviz is suppressed here — BLOCK 12 manages the single shared
        # RViz instance to avoid duplicate visualisation windows on screen.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory('diy_localization'),
                    'launch',
                    'localization.launch.py',
                )
            ),
            condition=IfCondition(use_localization),
            launch_arguments={
                'mode':        'runtime',
                'use_gps':     'true',
                'config_file': fastlio_config,
                'use_rviz':    'false',    # master owns the single RViz instance
            }.items(),
        ),

        # ── BLOCK 9: Joystick teleop ───────────────────────────────────────────
        # Includes joystick_drive.launch.py which starts:
        #   joy_node         — reads gamepad → sensor_msgs/Joy
        #   teleop_twist_joy — converts Joy → geometry_msgs/Twist on /cmd_vel_joy
        # The mux must be in TELEOP mode to forward /cmd_vel_joy to the output:
        #   ros2 param set /cmd_vel_mux_node mode TELEOP
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_dir, 'launch', 'joystick_drive.launch.py')
            ),
            condition=IfCondition(use_joystick),
        ),

        # ── BLOCK 10: Motor driver  (differential drive) ──────────────────────
        # Subscribes to /cmd_vel_safe (the mux's arbitrated, estop-gated output)
        # and converts Twist → left/right wheel PWM commands.
        #
        # IMPORTANT: the remap /cmd_vel → /cmd_vel_safe is intentional.
        # Never wire any hardware actuator directly to /cmd_vel — all commands
        # must pass through the mux so estop and mode arbitration cannot be
        # bypassed by any individual node.
        Node(
            package='differential-drive',
            executable='differential-drive',
            name='differential_drive',
            output='screen',
            condition=IfCondition(use_motor_driver),
            remappings=[('/cmd_vel', '/cmd_vel_safe')],   # read mux output, not raw /cmd_vel
        ),

        # ── BLOCK 11: Nav2 autonomous navigation stack ─────────────────────────
        # Full Nav2 bringup: Controller (MPPI), Planner (NavFn/Smac), Behaviour
        # Trees, AMCL localisation against the prior map, global/local costmaps,
        # and lifecycle manager.
        # Requires use_localization=true for /tf and /odometry/filtered inputs.
        # Publishes /cmd_vel_nav which the mux forwards when in AUTONOMOUS mode.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory('nav2_bringup'),
                    'launch',
                    'bringup_launch.py',
                )
            ),
            condition=IfCondition(use_nav2),
            launch_arguments={
                'map':          map_yaml,     # pre-built prior map for AMCL
                'params_file':  nav2_params,  # MPPI critics + costmap config
                'use_sim_time': 'false',      # always false on real hardware
                'autostart':    'true',       # lifecycle nodes activate automatically
                'slam':         'false',      # use prior map, not online SLAM
            }.items(),
        ),

        # ── BLOCK 12: RViz2  (developer / debug visualisation) ─────────────────
        # Disabled by default to conserve CPU/GPU on the Jetson during competition.
        # Enable for debugging:  ros2 launch ... use_rviz:=true
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            condition=IfCondition(use_rviz),
        ),
    ])
