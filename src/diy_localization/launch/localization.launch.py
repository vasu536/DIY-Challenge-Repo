#!/usr/bin/env python3
"""
diy_localization — localization.launch.py
══════════════════════════════════════════
Brings up the full localisation stack:

  runtime (default):
    FAST-LIO2 (lidar-inertial odometry)  →  EKF1 (odom frame)
                                         →  navsat_transform + EKF2 (map frame, GPS)

  mapping:
    Use offline_mapping.launch.py instead — this launch handles runtime only.

WHY OpaqueFunction
──────────────────
ROS 2 launch substitutions are lazy (not resolved at Python parse time).
We need the actual string values of ``mode`` and ``use_gps`` at Python level
to decide which Nodes to add.  OpaqueFunction lets us call `.perform(context)`
on any LaunchConfiguration inside the callback, converting the lazy substitution
into a real Python string that we can use in if/else logic.

DATA FLOW  (runtime, GPS enabled)
──────────────────────────────────
  /hesai/points  ──╮
  /imu/data      ──╰─ FAST-LIO2 (fastlio_mapping)  ──→  /lidar_odometry
                                                         │
                                    EKF1 (ekf_filter_node_odom)
                                    →  /odometry/filtered   [odom → base_link TF]
                                                         │
  /gps/fix       ──╮                                     │
  /imu/data      ──╰─ navsat_transform_node  ──→  /odometry/gps
  /odometry/filtered ─╮                               │
                      ╰─ EKF2 (ekf_filter_node_map)  ──→  /odometry/global  [map → odom TF]

Arguments
─────────
  mode           runtime | mapping   (default: runtime)
  use_gps        true | false        (default: true)
  config_file    FAST-LIO2 YAML name (default: fast_lio_hesai_qt64.yaml)
  use_rviz       true | false        (default: false)
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, SetRemap
from launch_ros.substitutions import FindPackageShare


# ─────────────────────────────────────────────────────────────────────────────
# OpaqueFunction callback — all runtime branching logic lives here.
# `context` lets us call .perform() to get resolved string values from
# LaunchConfiguration substitutions, enabling Python-level if/else decisions.
# ─────────────────────────────────────────────────────────────────────────────
def launch_setup(context, *args, **kwargs):
    # Resolve lazy LaunchConfiguration substitutions into plain Python strings
    # so we can use them in if/else branches below.
    pkg_loc     = get_package_share_directory("diy_localization")
    config_dir  = os.path.join(pkg_loc, "config")

    mode        = LaunchConfiguration("mode").perform(context)
    use_gps     = LaunchConfiguration("use_gps").perform(context)
    config_file = LaunchConfiguration("config_file").perform(context)
    use_rviz    = LaunchConfiguration("use_rviz").perform(context)

    nodes = []

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCK 1 — FAST-LIO2 lidar-inertial odometry  (runtime mode only)
    # ─────────────────────────────────────────────────────────────────────────
    # FAST-LIO2 does NOT use the standard ROS 2 parameter file mechanism.
    # Its internal config loader reads two node parameters at startup:
    #   config_path — absolute directory path containing the YAML (trailing / required)
    #   config_file — filename only, e.g. "fast_lio_hesai_qt64.yaml"
    #
    # We remap FAST-LIO2's hard-coded output /Odometry → /lidar_odometry so the
    # topic name is consistent with what EKF1 expects (ekf_local.yaml odom0).
    if mode == "runtime":
        fastlio_node = Node(
            package="fast_lio",
            executable="fastlio_mapping",
            name="fastlio_mapping",
            output="screen",
            parameters=[
                {
                    "config_path": config_dir + "/",   # directory — trailing slash required
                    "config_file": config_file,         # YAML filename without path prefix
                }
            ],
            remappings=[
                # FAST-LIO2 hard-codes /Odometry; rename to project standard topic
                ("/Odometry", "/lidar_odometry"),
            ],
        )
        nodes.append(fastlio_node)

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCK 2 — EKF1 (local odom-frame estimator)
    # ─────────────────────────────────────────────────────────────────────────
    # EKF1 fuses lidar odometry + raw IMU in the odom → base_link frame.
    # Configured via config/ekf_local.yaml:
    #   odom0 = /lidar_odometry   (6-DOF pose from FAST-LIO2)
    #   imu0  = /imu/data         (angular velocity + linear acceleration)
    # Publishes /odometry/filtered and maintains the odom → base_link TF.
    ekf_local_node = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node_odom",
        output="screen",
        parameters=[os.path.join(config_dir, "ekf_local.yaml")],
        remappings=[
            ("odometry/filtered", "/odometry/filtered"),  # fused odom-frame estimate
        ],
        condition=IfCondition(str(mode == "runtime").lower()),
    )
    nodes.append(ekf_local_node)

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCK 3 — navsat_transform + EKF2  (global map frame, GPS fusion)
    # ─────────────────────────────────────────────────────────────────────────
    # Only active when use_gps=true AND mode=runtime.
    #
    # navsat_transform_node:
    #   Converts raw GPS (lat/lon/alt) + heading from EKF1 into an Odometry
    #   message in the EKF's local frame.  Publishes /odometry/gps.
    #
    # EKF2 (ekf_filter_node_map):
    #   Second EKF that fuses /odometry/filtered (local) with /odometry/gps
    #   (GPS-derived) to maintain a globally consistent map-frame position.
    #   Publishes /odometry/global and maintains the map → odom TF.
    if use_gps == "true" and mode == "runtime":
        navsat_node = Node(
            package="robot_localization",
            executable="navsat_transform_node",
            name="navsat_transform_node",
            output="screen",
            parameters=[os.path.join(config_dir, "navsat_transform.yaml")],
            remappings=[
                ("imu/data",          "/imu/data"),           # heading source for datum init
                ("gps/fix",           "/gps/fix"),            # raw NavSatFix from GPS receiver
                ("odometry/filtered", "/odometry/filtered"),  # EKF1 output (headig + position)
                ("odometry/gps",      "/odometry/gps"),       # output → EKF2 input
                ("gps/filtered",      "/gps/filtered"),       # projected GPS (optional output)
            ],
        )
        nodes.append(navsat_node)

        # EKF2 — fuses local odometry with GPS-derived odometry in the map frame
        ekf_global_node = Node(
            package="robot_localization",
            executable="ekf_node",
            name="ekf_filter_node_map",
            output="screen",
            parameters=[os.path.join(config_dir, "ekf_global.yaml")],
            remappings=[
                # Publish on a separate topic so EKF1's /odometry/filtered is preserved
                ("odometry/filtered", "/odometry/global"),
            ],
        )
        nodes.append(ekf_global_node)

    # ─────────────────────────────────────────────────────────────────────────
    # BLOCK 4 — Optional RViz  (localisation display)
    # ─────────────────────────────────────────────────────────────────────────
    # Uses challenge_bringup/rviz/localization.rviz if it exists; otherwise
    # skips launch silently to avoid crashing on a missing config file.
    if use_rviz == "true":
        rviz_config = os.path.join(
            get_package_share_directory("challenge_bringup"), "rviz", "localization.rviz"
        )
        if os.path.exists(rviz_config):
            nodes.append(
                Node(
                    package="rviz2",
                    executable="rviz2",
                    name="rviz2",
                    arguments=["-d", rviz_config],  # load preset display configuration
                    output="screen",
                )
            )

    return nodes


# ─────────────────────────────────────────────────────────────────────────────
# Entry point — declare args then hand off to OpaqueFunction for node construction
# ─────────────────────────────────────────────────────────────────────────────
def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "mode",
                default_value="runtime",
                description="runtime | mapping",
            ),
            DeclareLaunchArgument(
                "use_gps",
                default_value="true",
                description="Enable GPS fusion (EKF2 + navsat_transform)",
            ),
            DeclareLaunchArgument(
                "config_file",
                default_value="fast_lio_hesai_qt64.yaml",
                description="FAST-LIO2 config YAML filename inside diy_localization/config/",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="false",
                description="Launch RViz with localization config",
            ),
            # All node construction is deferred to launch_setup() so we can
            # branch on resolved argument values at Python runtime.
            OpaqueFunction(function=launch_setup),
        ]
    )
