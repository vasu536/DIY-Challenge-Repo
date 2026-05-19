#!/usr/bin/env python3
"""
generate_nav2_tuning_guide.py — Nav2 Tuning Guide
Produces docs/Nav2_Tuning_Guide.pdf using ReportLab.
Run from the repo root:   python3 docs/generate_nav2_tuning_guide.py
"""

import os
import tempfile as _tmpmod

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Preformatted,
)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ── Output path ───────────────────────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH  = os.path.join(REPO_ROOT, 'docs', 'Nav2_Tuning_Guide.pdf')

# ── Colour palette ─────────────────────────────────────────────────────────────
C_NAVY   = colors.HexColor('#1A2744')
C_BLUE   = colors.HexColor('#2563EB')
C_TEAL   = colors.HexColor('#0F766E')
C_ORANGE = colors.HexColor('#EA580C')
C_GREEN  = colors.HexColor('#16A34A')
C_LGREY  = colors.HexColor('#F1F5F9')
C_MGREY  = colors.HexColor('#94A3B8')
C_BLACK  = colors.HexColor('#0F172A')
C_WHITE  = colors.white
C_PURPLE = colors.HexColor('#7C3AED')


# ─────────────────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()
    s = {}
    s['title'] = ParagraphStyle('DocTitle', parent=base['Title'],
        fontSize=26, leading=32, textColor=C_WHITE, spaceAfter=6, alignment=TA_CENTER)
    s['subtitle'] = ParagraphStyle('DocSubtitle',
        fontSize=12, leading=17, textColor=colors.HexColor('#CBD5E1'),
        spaceAfter=4, alignment=TA_CENTER)
    s['h1'] = ParagraphStyle('H1', fontSize=16, leading=20, textColor=C_NAVY,
        spaceBefore=18, spaceAfter=6, fontName='Helvetica-Bold')
    s['h2'] = ParagraphStyle('H2', fontSize=13, leading=17, textColor=C_BLUE,
        spaceBefore=12, spaceAfter=4, fontName='Helvetica-Bold')
    s['h3'] = ParagraphStyle('H3', fontSize=11, leading=15, textColor=C_PURPLE,
        spaceBefore=8, spaceAfter=3, fontName='Helvetica-BoldOblique')
    s['body'] = ParagraphStyle('Body', fontSize=10, leading=14, textColor=C_BLACK,
        spaceAfter=6, alignment=TA_JUSTIFY)
    s['bullet'] = ParagraphStyle('Bullet', fontSize=10, leading=13, textColor=C_BLACK,
        spaceAfter=3, leftIndent=14, bulletIndent=4)
    s['code'] = ParagraphStyle('Code', fontName='Courier',
        fontSize=8.5, leading=12, textColor=C_BLACK,
        backColor=C_LGREY, borderPad=6, spaceAfter=6)
    s['code_label'] = ParagraphStyle('CodeLabel', fontName='Helvetica-Bold',
        fontSize=8, textColor=C_MGREY, spaceAfter=1)
    s['warn'] = ParagraphStyle('Warn', fontSize=9.5, leading=13,
        textColor=colors.HexColor('#7C2D12'),
        backColor=colors.HexColor('#FEF3C7'),
        borderPad=6, spaceAfter=6, fontName='Helvetica')
    s['note'] = ParagraphStyle('Note', fontSize=9.5, leading=13,
        textColor=colors.HexColor('#1E3A5F'),
        backColor=colors.HexColor('#DBEAFE'),
        borderPad=6, spaceAfter=6)
    s['tip'] = ParagraphStyle('Tip', fontSize=9.5, leading=13,
        textColor=colors.HexColor('#065F46'),
        backColor=colors.HexColor('#D1FAE5'),
        borderPad=6, spaceAfter=6)
    s['th'] = ParagraphStyle('TH', fontName='Helvetica-Bold',
        fontSize=9, textColor=C_WHITE, alignment=TA_CENTER)
    s['tc'] = ParagraphStyle('TC', fontName='Helvetica',
        fontSize=9, textColor=C_BLACK, leading=13)
    s['tc_sm'] = ParagraphStyle('TC_sm', fontName='Helvetica',
        fontSize=8, textColor=C_BLACK, leading=11)
    return s


def H(text, level, styles): return Paragraph(text, styles[level])
def P(text, styles): return Paragraph(text, styles['body'])
def B(items, styles): return [Paragraph(f'• {item}', styles['bullet']) for item in items]

def code_block(label, text, styles):
    out = []
    if label:
        out.append(Paragraph(label, styles['code_label']))
    out.append(Preformatted(text, styles['code']))
    return out

def hr(styles): return HRFlowable(width='100%', thickness=0.5, color=C_MGREY, spaceAfter=8)
def warn_box(t, styles): return Paragraph('WARNING:  ' + t, styles['warn'])
def note_box(t, styles): return Paragraph('NOTE:  ' + t, styles['note'])
def tip_box(t, styles): return Paragraph('TIP:  ' + t, styles['tip'])
def SP(n=6): return Spacer(1, n)


# ─────────────────────────────────────────────────────────────────────────────
# Diagram: MPPI critic weight bar chart
# ─────────────────────────────────────────────────────────────────────────────
def _make_critic_chart():
    tmp = _tmpmod.NamedTemporaryFile(suffix='.png', delete=False)
    critics = [
        ('PathAlignCritic',    14.0, '#2563EB'),
        ('ObstaclesCritic',    20.0, '#DC2626'),   # critical_weight
        ('PreferForwardCritic', 5.0, '#16A34A'),
        ('GoalCritic',          5.0, '#D97706'),
        ('PathFollowCritic',    5.0, '#7C3AED'),
        ('GoalAngleCritic',     3.0, '#0F766E'),
        ('PathAngleCritic',     2.0, '#94A3B8'),
        ('ConstraintCritic',    4.0, '#EA580C'),
    ]
    names = [c[0].replace('Critic','') for c in critics]
    weights = [c[1] for c in critics]
    bar_colors = [c[2] for c in critics]

    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor('white')
    bars = ax.barh(names, weights, color=bar_colors, edgecolor='white', linewidth=0.5)
    ax.set_xlabel('Weight', fontsize=10)
    ax.set_title('MPPI Critic Weights (current nav2_params.yaml)', fontsize=11, fontweight='bold')
    ax.set_xlim(0, 25)
    ax.axvline(x=14, color='#2563EB', linestyle='--', alpha=0.5, linewidth=1)
    for bar, w in zip(bars, weights):
        ax.text(w + 0.3, bar.get_y() + bar.get_height()/2, f'{w}',
            va='center', fontsize=9, fontweight='bold', color='#1E293B')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor('white')
    plt.tight_layout()
    fig.savefig(tmp.name, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return tmp.name


def _on_cover(canvas, doc):
    w, h = A4
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, h - 7*cm, w, 7*cm, fill=1, stroke=0)
    canvas.setFillColor(C_PURPLE)
    canvas.rect(0, h - 7.35*cm, w, 0.35*cm, fill=1, stroke=0)

def _on_page(canvas, doc):
    w, h = A4
    canvas.setFillColor(C_LGREY)
    canvas.rect(0, 0, w, 1.4*cm, fill=1, stroke=0)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(C_MGREY)
    canvas.drawString(2*cm, 0.55*cm, 'DIY Challenge — Nav2 Tuning Guide')
    canvas.drawRightString(w - 2*cm, 0.55*cm, f'Page {doc.page}')


def build_pdf():
    styles = make_styles()
    doc = SimpleDocTemplate(
        OUT_PATH, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2.2*cm,
    )

    def H1(t): return H(t, 'h1', styles)
    def H2(t): return H(t, 'h2', styles)
    def H3(t): return H(t, 'h3', styles)
    def Pb(t): return P(t, styles)
    def Bl(items): return B(items, styles)
    def CB(lbl, txt): return code_block(lbl, txt, styles)
    def HR(): return hr(styles)
    def WARN(t): return warn_box(t, styles)
    def NOTE(t): return note_box(t, styles)
    def TIP(t): return tip_box(t, styles)

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    story.append(SP(60))
    story.append(Paragraph('DIY Challenge Robot', styles['title']))
    story.append(SP(4))
    story.append(Paragraph('Nav2 Tuning Guide', styles['title']))
    story.append(SP(10))
    story.append(Paragraph(
        'MPPI Controller &amp; 8 Critics • Costmap Parameters<br/>'
        'Open Outdoor vs Tight Indoor Tuning • Failure Mode Diagnosis',
        styles['subtitle']))
    story.append(SP(6))
    story.append(Paragraph('ROS 2 Humble • nav2_params.yaml reference values included',
        styles['subtitle']))
    story.append(PageBreak())

    # ── TOC ────────────────────────────────────────────────────────────────────
    toc_data = [
        [Paragraph('Section', styles['th']), Paragraph('Topic', styles['th'])],
        ['1', 'Nav2 Stack Overview for This Robot'],
        ['2', 'MPPI Controller — How It Works'],
        ['3', 'The 8 MPPI Critics — Current Weights & Effects'],
        ['4', 'Costmap Parameters Explained'],
        ['5', 'Planner Parameters (SmacPlannerHybrid)'],
        ['6', 'Scenario Tuning: Open Outdoor vs Tight Indoor'],
        ['7', 'Common Nav2 Failure Modes & Parameter Fixes'],
        ['8', 'Behavior Server & Recovery Tuning'],
        ['9', 'Quick-Reference Parameter Table'],
    ]
    toc_table = Table(toc_data, colWidths=[2*cm, 14*cm])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('TEXTCOLOR',  (0,0), (-1,0), C_WHITE),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LGREY]),
        ('FONTNAME',   (0,1), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,1), (-1,-1), 10),
        ('ALIGN',      (0,0), (0,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('GRID',       (0,0), (-1,-1), 0.4, C_MGREY),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story += [H1('Table of Contents'), SP(4), toc_table, PageBreak()]

    # ── §1 Stack Overview ─────────────────────────────────────────────────────
    story.append(H1('1  Nav2 Stack Overview for This Robot'))
    story.append(Pb(
        'This robot uses the Nav2 Humble stack with MPPI as the local trajectory '
        'controller and SmacPlannerHybrid as the global path planner. '
        'The main configuration file is '
        '<tt>src/challenge_bringup/config/nav2_params.yaml</tt>.'
    ))

    stack_data = [
        [Paragraph('Component', styles['th']), Paragraph('Plugin / Node', styles['th']),
         Paragraph('Frequency', styles['th']), Paragraph('Purpose', styles['th'])],
        ['BT Navigator', 'bt_navigator', 'on goal', 'Behaviour-tree goal execution'],
        ['Global Planner', 'SmacPlannerHybrid', '10 Hz', 'A* Hybrid-A* (kinematic) path'],
        ['Local Controller', 'MPPIController', '20 Hz', 'Sampled trajectory optimization'],
        ['Global Costmap', '2-D costmap', '1 Hz', 'Inflation + global obstacles'],
        ['Local Costmap', '2-D + VoxelLayer', '10 Hz', 'Rolling 4×4m window'],
        ['Behavior Server', 'bt_navigator', 'on request', 'Spin, backup, wait recoveries'],
        ['Collision Monitor', 'collision_monitor', '10 Hz', 'Hard stop on imminent collision'],
    ]
    stack_table = Table(stack_data, colWidths=[3.5*cm, 4*cm, 2.5*cm, 6.5*cm])
    stack_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LGREY]),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.4, C_MGREY),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story += [SP(4), stack_table, SP(8)]

    story.append(H2('1.1  Robot Footprint &amp; Velocity Limits'))
    story += CB('From nav2_params.yaml:', '''\
# Robot footprint (metres) — outer corners of 406mm square chassis
footprint: "[[0.35, 0.20], [0.35, -0.20], [-0.35, -0.20], [-0.35, 0.20]]"

# MPPI velocity envelope
FollowPath:
  vx_max:  0.6    # m/s forward max
  vx_min: -0.1    # m/s reverse max
  vy_max:  0.0    # differential drive — no lateral
  wz_max:  1.2    # rad/s yaw rate max
  controller_frequency: 20.0
''')
    story.append(PageBreak())

    # ── §2 MPPI How It Works ──────────────────────────────────────────────────
    story.append(H1('2  MPPI Controller — How It Works'))
    story.append(Pb(
        'Model Predictive Path Integral (MPPI) is a sampling-based controller. '
        'At each 20 Hz control cycle it simulates <b>1,000 random trajectories</b> '
        'forward by 40 time steps of 0.05 s each (= 2 seconds look-ahead). '
        'Each trajectory is scored by a weighted sum of critic costs. '
        'The optimal control is the weighted average of all trajectories, '
        'biased toward the lowest-cost ones.'
    ))
    story.append(H2('2.1  Key MPPI Parameters'))
    story += CB('nav2_params.yaml — FollowPath:', '''\
MPPIController:
  time_steps: 40        # prediction horizon (steps)
  model_dt: 0.05        # seconds per step → 2 s look-ahead
  batch_size: 1000      # trajectory samples per cycle
  vx_std: 0.2           # velocity noise sigma (forward)
  wz_std: 0.4           # angular velocity noise sigma
  temperature: 0.3      # softmax sharpness (lower = sharper selection)
  gamma: 0.015          # discount factor (lower = more greedy)
  iteration_count: 1    # optimisation iterations per cycle
''')
    story.append(H2('2.2  Tuning Philosophy'))
    story += Bl([
        '<b>batch_size</b>: Higher = better coverage of trajectory space but more CPU. '
        '1000 is the practical limit for Jetson at 20 Hz.',
        '<b>time_steps × model_dt</b>: The planning horizon. 2 s at 0.6 m/s = 1.2 m look-ahead. '
        'Increase time_steps for faster courses; decrease for tight manoeuvres.',
        '<b>temperature</b>: Lower values make the controller more aggressive in selecting '
        'low-cost trajectories; higher values average more trajectories (smoother but slower).',
    ])
    story.append(NOTE(
        'MPPI runs entirely on CPU in Nav2 Humble — all 1000 trajectories are evaluated '
        'sequentially on the ARM cores. There is no GPU acceleration in this stack.'
    ))
    story.append(PageBreak())

    # ── §3 Critics ────────────────────────────────────────────────────────────
    story.append(H1('3  The 8 MPPI Critics — Current Weights &amp; Effects'))
    story.append(Pb(
        'Each critic scores every sampled trajectory. Critics with higher weight '
        'dominate the final trajectory selection. The current values below are from '
        '<tt>src/challenge_bringup/config/nav2_params.yaml</tt>.'
    ))
    chart_png = _make_critic_chart()
    from reportlab.platypus import Image as RLImage
    story.append(RLImage(chart_png, width=16*cm, height=6*cm))
    story.append(Pb('<i>Figure 1 — Current MPPI critic weights. ObstaclesCritic critical_weight=20 '
        'dominates collision avoidance; PathAlignCritic=14 dominates path tracking.</i>'))
    story.append(SP(8))

    tc_sm = styles['tc_sm']
    critics_data = [
        [Paragraph('Critic', styles['th']), Paragraph('Weight', styles['th']),
         Paragraph('What It Penalises', styles['th']), Paragraph('Tuning Effect', styles['th'])],
        [Paragraph('PathAlignCritic', tc_sm), Paragraph('14.0', tc_sm),
         Paragraph('Path occupancy ratio — penalises trajectories that deviate from the global path', tc_sm),
         Paragraph('Higher → robot tracks global plan closely; lower → more free-space shortcuts', tc_sm)],
        [Paragraph('ObstaclesCritic<br/>(critical_weight)', tc_sm), Paragraph('20.0', tc_sm),
         Paragraph('Proximity to obstacles below critical threshold (0.10 m); collision_cost=10000', tc_sm),
         Paragraph('Always keep high; collision_cost makes crossing threshold catastrophic', tc_sm)],
        [Paragraph('ObstaclesCritic<br/>(repulsion_weight)', tc_sm), Paragraph('1.5', tc_sm),
         Paragraph('Repulsion cost in inflation zone beyond collision threshold', tc_sm),
         Paragraph('Higher → robot avoids inflation zone more aggressively', tc_sm)],
        [Paragraph('GoalCritic', tc_sm), Paragraph('5.0<br/>(threshold 1.4 m)', tc_sm),
         Paragraph('Distance to goal within threshold_to_consider radius', tc_sm),
         Paragraph('Active only near goal; higher → faster final approach', tc_sm)],
        [Paragraph('PreferForwardCritic', tc_sm), Paragraph('5.0', tc_sm),
         Paragraph('Backward motion — penalises negative vx', tc_sm),
         Paragraph('Higher → robot avoids reversing; lower → more willing to back up', tc_sm)],
        [Paragraph('PathFollowCritic', tc_sm), Paragraph('5.0<br/>(offset 5)', tc_sm),
         Paragraph('Distance from trajectory point to corresponding path point at offset_from_furthest', tc_sm),
         Paragraph('Higher → strong position tracking; lower → only direction tracking', tc_sm)],
        [Paragraph('GoalAngleCritic', tc_sm), Paragraph('3.0<br/>(threshold 0.5 m)', tc_sm),
         Paragraph('Heading error at goal within threshold_to_consider', tc_sm),
         Paragraph('Higher → robot arrives more accurately oriented; active in final 0.5 m', tc_sm)],
        [Paragraph('PathAngleCritic', tc_sm), Paragraph('2.0', tc_sm),
         Paragraph('Angle between trajectory direction and path direction at offset_from_furthest=20', tc_sm),
         Paragraph('Higher → robot aligns heading with path more strictly during travel', tc_sm)],
        [Paragraph('ConstraintCritic', tc_sm), Paragraph('4.0', tc_sm),
         Paragraph('Hard velocity constraints violation — penalises trajectories outside vx/wz bounds', tc_sm),
         Paragraph('Should stay at 4.0+; going too low risks constraint violations in the trajectory', tc_sm)],
    ]
    critics_table = Table(critics_data, colWidths=[3.8*cm, 1.8*cm, 5.5*cm, 5.4*cm])
    critics_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LGREY]),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.4, C_MGREY),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story += [SP(4), critics_table, PageBreak()]

    # ── §4 Costmap Parameters ─────────────────────────────────────────────────
    story.append(H1('4  Costmap Parameters Explained'))
    story.append(H2('4.1  Global Costmap'))
    story += CB('nav2_params.yaml — global_costmap:', '''\
global_costmap:
  global_costmap:
    ros__parameters:
      update_frequency: 1.0
      publish_frequency: 1.0
      global_frame: map
      robot_base_frame: base_link
      use_sim_time: false
      robot_radius: 0.35          # insribed radius of footprint
      resolution: 0.05            # metres per cell — 5 cm
      track_unknown_space: true
      plugins: ["static_layer", "obstacle_layer", "inflation_layer"]

      inflation_layer:
        cost_scaling_factor: 3.0  # exponential decay — higher = faster falloff
        inflation_radius: 0.45    # metres around obstacles to inflate

      obstacle_layer:
        raytrace_max_range: 6.0   # max range for ray-clearing free space
        obstacle_max_range: 5.0   # max range for marking obstacles
''')
    story.append(SP(4))
    story.append(H2('4.2  Local Costmap (Rolling Window)'))
    story += CB('nav2_params.yaml — local_costmap:', '''\
local_costmap:
  local_costmap:
    ros__parameters:
      update_frequency: 10.0
      publish_frequency: 10.0
      global_frame: odom
      robot_base_frame: base_link
      rolling_window: true
      width: 4                    # metres — 4×4 m window
      height: 4
      resolution: 0.05            # 5 cm cells
      plugins: ["voxel_layer", "inflation_layer"]

      voxel_layer:
        z_resolution: 0.05        # vertical cell size
        z_voxels: 16              # 16 × 0.05 = 0.8 m height

      inflation_layer:
        cost_scaling_factor: 3.0
        inflation_radius: 0.40    # slightly tighter than global
''')
    story.append(H2('4.3  Inflation Radius Tuning'))
    story += Bl([
        '<b>inflation_radius</b> should be at least your robot half-width + safety margin. '
        'Current: 0.40–0.45 m for a 0.35 m half-width robot — 5–10 cm margin.',
        '<b>cost_scaling_factor</b>: higher values mean cost falls off faster with distance. '
        '3.0 creates a medium-soft gradient. Increase to 5–8 for open courses; keep at 3 for tight.',
        'Global costmap inflation can be wider (0.45) than local (0.40) because the global '
        'planner benefits from earlier obstacle avoidance at path-planning time.',
    ])
    story.append(PageBreak())

    # ── §5 Planner ────────────────────────────────────────────────────────────
    story.append(H1('5  Planner Parameters (SmacPlannerHybrid)'))
    story.append(Pb(
        'SmacPlannerHybrid implements Hybrid-A* — a state-lattice planner that '
        'respects non-holonomic differential drive kinematics. '
        'It produces smooth, kinematically feasible global paths.'
    ))
    story += CB('nav2_params.yaml — SmacPlannerHybrid:', '''\
GridBased:
  plugin: "nav2_smac_planner/SmacPlannerHybrid"
  downsample_costmap: false
  downsampling_factor: 1
  tolerance: 0.25           # metres — goal tolerance for planner
  allow_unknown: true       # plan through unknown cells
  max_iterations: 1000000
  max_on_approach_iterations: 1000
  max_planning_time: 5.0    # seconds budget per plan
  motion_model_for_search: "REEDS_SHEPP"
  angle_quantization_bins: 72
  analytic_expansion_ratio: 3.5
  minimum_turning_radius: 0.40  # metres — derived from wz_max / vx_max
  reverse_penalty: 2.1
  change_penalty: 0.0
  non_straight_penalty: 1.20
  cost_penalty: 2.0
  retrospective_penalty: 0.025
  lookup_table_size: 20.0
  cache_obstacle_heuristic: false
  debug_visualizations: false
  expected_planner_frequency: 10.0
''')
    story.append(H2('5.1  Key Planner Tuning Points'))
    story += Bl([
        '<b>minimum_turning_radius</b>: Keep at ≥ the physical turning radius. '
        'Computed as: min_turning_radius ≈ vx_max / wz_max = 0.6 / 1.2 = 0.5 m. '
        'Current value 0.40 m is slightly aggressive — increase to 0.5 if plans look jagged.',
        '<b>reverse_penalty</b>: 2.1× cost for reversing. Increase to 5.0+ if robot reverses too aggressively.',
        '<b>non_straight_penalty</b>: Extra cost for turning maneuvers. '
        'Increase to 1.5–2.0 if planner produces unnecessarily sinuous paths.',
        '<b>allow_unknown=true</b>: Lets the planner route through unexplored regions. '
        'Set false if the full map is known to prevent phantom routing.',
    ])
    story.append(PageBreak())

    # ── §6 Scenario Tuning ────────────────────────────────────────────────────
    story.append(H1('6  Scenario Tuning: Open Outdoor vs Tight Indoor'))
    story.append(H2('6.1  Open Outdoor Course (DIY Challenge Typical)'))
    story.append(Pb(
        'The competition course is a large outdoor area with sparse obstacles '
        '(cones, barriers, natural terrain). Priorities: speed, path tracking, '
        'minimal unnecessary turns.'
    ))
    outdoor_data = [
        [Paragraph('Parameter', styles['th']), Paragraph('Current', styles['th']),
         Paragraph('Recommended Range', styles['th']), Paragraph('Rationale', styles['th'])],
        ['vx_max', '0.6', '0.5–0.8', 'Rules allow up to ~1 m/s; 0.6 is conservative'],
        ['PathAlignCritic weight', '14.0', '12–18', 'High weight to stay on global plan in open space'],
        ['ObstaclesCritic repulsion_weight', '1.5', '1.0–2.0', 'Soft repulsion OK; no narrow corridors'],
        ['inflation_radius (local)', '0.40', '0.35–0.45', 'Full robot width + small margin'],
        ['time_steps', '40', '40–60', 'More look-ahead helps at higher speed'],
        ['minimum_turning_radius (planner)', '0.40', '0.5–0.7', 'Match actual turn capability at speed'],
        ['cost_scaling_factor', '3.0', '2.0–4.0', 'Softer gradient OK with sparse obstacles'],
    ]
    out_table = Table(outdoor_data, colWidths=[4.5*cm, 1.8*cm, 3.5*cm, 6.7*cm])
    out_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LGREY]),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.4, C_MGREY),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story += [SP(4), out_table, SP(8)]

    story.append(H2('6.2  Tight Indoor / Narrow Corridor Course'))
    story.append(Pb(
        'If the course includes corridors, doorways, or narrow gates, '
        'the robot must navigate more carefully at lower speed.'
    ))
    indoor_data = [
        [Paragraph('Parameter', styles['th']), Paragraph('Suggested Change', styles['th']),
         Paragraph('Rationale', styles['th'])],
        ['vx_max', '0.3–0.4 m/s', 'Slower allows more time to respond to obstacles'],
        ['PathAlignCritic weight', '8–10', 'Reduce to allow slight detours around tight obstacles'],
        ['ObstaclesCritic repulsion_weight', '3.0–5.0', 'Strong repulsion from walls critical in corridors'],
        ['inflation_radius (local)', '0.25–0.30', 'Tighter inflation to fit through narrow gaps'],
        ['cost_scaling_factor', '5.0–8.0', 'Sharp gradient forces robot to stay central in corridors'],
        ['time_steps', '25–30', 'Shorter horizon for slow-speed precision manoeuvring'],
        ['minimum_turning_radius', '0.25–0.35', 'Allow tighter turns for door-clearing'],
    ]
    ind_table = Table(indoor_data, colWidths=[4.5*cm, 3.5*cm, 8.5*cm])
    ind_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LGREY]),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.4, C_MGREY),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story += [SP(4), ind_table, PageBreak()]

    # ── §7 Failure Modes ─────────────────────────────────────────────────────
    story.append(H1('7  Common Nav2 Failure Modes &amp; Parameter Fixes'))

    failures = [
        ('Robot oscillates around path', 'Too-high PathAlignCritic or PathFollowCritic weight',
         'Reduce PathAlignCritic from 14 → 10; increase temperature from 0.3 → 0.5 for smoother selection'),
        ('Robot cuts corners dangerously', 'PathAlignCritic weight too low OR inflation_radius too small',
         'Increase PathAlignCritic weight; increase inflation_radius by 0.05 m increments'),
        ('Robot freezes near obstacle (no path)', 'Inflation too wide; costmap too conservative',
         'Reduce local inflation_radius; check global costmap for phantom obstacles (stale cells)'),
        ('Robot never reaches goal (tolerance failure)', 'xy_goal_tolerance too tight; goal in costmap obstacle',
         'Set xy_goal_tolerance: 0.30; verify goal is not inside an inflated obstacle cell'),
        ('Robot reverses unexpectedly during navigation', 'reverse_penalty too low; path requires reverse',
         'Increase reverse_penalty to 3.0–5.0 in SmacPlannerHybrid; add PreferForwardCritic weight'),
        ('Robot spins in place endlessly', 'Recovery loop triggered; costmap stuck obstacle',
         'Clear costmap: ros2 service call /global_costmap/clear_entirely_global_costmap; reduce recovery max_rotational_vel'),
        ('Slow, jerky motion in open space', 'batch_size / time_steps too low for the speed',
         'Increase time_steps to 56 (= 2.8 s horizon); increase batch_size if CPU allows'),
        ('Goal tolerance never met (yaw)', 'yaw_goal_tolerance too tight (0.20 rad ≈ 11°)',
         'Increase yaw_goal_tolerance to 0.35–0.50 if heading precision not required'),
    ]

    for symptom, cause, fix in failures:
        row = Table(
            [[Paragraph(f'<b>Symptom:</b> {symptom}', styles['tc']),
              Paragraph(f'<b>Cause:</b> {cause}', styles['tc']),
              Paragraph(f'<b>Fix:</b> {fix}', styles['tc'])]],
            colWidths=[5*cm, 5*cm, 6.5*cm]
        )
        row.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), C_LGREY),
            ('GRID', (0,0), (-1,-1), 0.3, C_MGREY),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
        ]))
        story.append(row)
        story.append(SP(3))

    story.append(PageBreak())

    # ── §8 Behavior Server ───────────────────────────────────────────────────
    story.append(H1('8  Behavior Server &amp; Recovery Tuning'))
    story.append(Pb(
        'The nav2_behaviors server provides recovery actions triggered by the '
        'Behaviour Tree when the robot gets stuck. Current configured behaviors: '
        'Spin, BackUp, DriveOnHeading, Wait.'
    ))
    story += CB('nav2_params.yaml — behavior_server:', '''\
behavior_server:
  ros__parameters:
    costmap_topic: local_costmap/costmap_raw
    footprint_topic: local_costmap/published_footprint
    cycle_frequency: 10.0
    behavior_plugins: ["spin", "backup", "drive_on_heading", "wait"]

    spin:
      plugin: "nav2_behaviors/Spin"
    backup:
      plugin: "nav2_behaviors/BackUp"
    drive_on_heading:
      plugin: "nav2_behaviors/DriveOnHeading"
    wait:
      plugin: "nav2_behaviors/Wait"

    # Speed limits during recoveries
    max_rotational_vel: 1.0     # rad/s (was 3.2 accel limit)
    min_rotational_vel: 0.4
    rotational_acc_lim: 3.2
''')
    story.append(H2('8.1  Recovery Tuning'))
    story += Bl([
        '<b>max_rotational_vel</b>: 1.0 rad/s is the spin recovery rate. '
        'Reduce to 0.5 for tighter spaces; increase for faster recovery exit.',
        '<b>Spin recovery</b>: triggered when the robot is stuck and cannot plan. '
        'If spin does not clear the blockage, check for real physical obstructions.',
        '<b>BackUp recovery</b>: drives backward 0.3 m by default. '
        'The distance and speed are set in the Behaviour Tree XML — edit '
        'navigate_w_replanning_and_recovery.xml to change.',
        '<b>Wait recovery</b>: waits for a dynamic obstacle to move. '
        'Useful if the course has human or robot cross-traffic.',
        'Recovery sequence (default BT): try plan → spin → backup → replan. '
        'After N failures the goal is aborted.',
    ])
    story.append(PageBreak())

    # ── §9 Quick Reference ───────────────────────────────────────────────────
    story.append(H1('9  Quick-Reference Parameter Table'))
    story.append(Pb('All values from <tt>src/challenge_bringup/config/nav2_params.yaml</tt>.'))

    qr_data = [
        [Paragraph('Parameter', styles['th']), Paragraph('Value', styles['th']),
         Paragraph('Location', styles['th'])],
        ['controller_frequency', '20 Hz', 'controller_server'],
        ['planner_frequency', '10 Hz', 'planner_server.expected_planner_frequency'],
        ['vx_max / vx_min / wz_max', '0.6 / -0.1 / 1.2', 'FollowPath.MotionModel'],
        ['time_steps / model_dt', '40 / 0.05 s = 2 s horizon', 'FollowPath.MPPIController'],
        ['batch_size', '1000', 'FollowPath.MPPIController'],
        ['temperature / gamma', '0.3 / 0.015', 'FollowPath.MPPIController'],
        ['PathAlignCritic weight', '14.0', 'critics[PathAlignCritic]'],
        ['ObstaclesCritic critical_weight', '20.0', 'critics[ObstaclesCritic]'],
        ['collision_cost', '10000.0', 'critics[ObstaclesCritic]'],
        ['collision_margin_distance', '0.10 m', 'critics[ObstaclesCritic]'],
        ['GoalCritic threshold_to_consider', '1.4 m', 'critics[GoalCritic]'],
        ['GoalAngleCritic threshold', '0.5 m', 'critics[GoalAngleCritic]'],
        ['xy_goal_tolerance', '0.20 m', 'goal_checker'],
        ['yaw_goal_tolerance', '0.20 rad (~11°)', 'goal_checker'],
        ['required_movement_radius', '0.3 m in 8 s', 'progress_checker'],
        ['global inflation_radius', '0.45 m', 'global_costmap.inflation_layer'],
        ['local inflation_radius', '0.40 m', 'local_costmap.inflation_layer'],
        ['cost_scaling_factor', '3.0', 'both costmaps'],
        ['global resolution', '0.05 m/cell', 'global_costmap'],
        ['local size / resolution', '4×4 m / 0.05 m', 'local_costmap'],
        ['minimum_turning_radius', '0.40 m', 'SmacPlannerHybrid'],
        ['reverse_penalty', '2.1', 'SmacPlannerHybrid'],
        ['max_rotational_vel (recovery)', '1.0 rad/s', 'behavior_server'],
    ]
    qr_table = Table(qr_data, colWidths=[6*cm, 3.5*cm, 7*cm])
    qr_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LGREY]),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.4, C_MGREY),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story += [SP(4), qr_table, SP(12)]

    story.append(HR())
    story.append(Pb(
        '<i>End of Nav2 Tuning Guide. '
        'For the full YAML see src/challenge_bringup/config/nav2_params.yaml. '
        'For environment setup and launch, see the Competition Day Playbook.</i>'
    ))

    doc.build(story, onFirstPage=_on_cover, onLaterPages=_on_page)
    print(f'Written: {OUT_PATH}')


if __name__ == '__main__':
    build_pdf()
