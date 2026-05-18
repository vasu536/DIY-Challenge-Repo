#!/usr/bin/env python3
"""
generate_gpu_guide.py — Jetson Nano GPU Guide for DIY Challenge Repo
Produces docs/Jetson_GPU_Guide.pdf using ReportLab.
Run from the repo root:   python3 docs/generate_gpu_guide.py
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
    PageBreak, HRFlowable, Preformatted, Image as RLImage,
)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ── Output path ───────────────────────────────────────────────────────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH  = os.path.join(REPO_ROOT, 'docs', 'Jetson_GPU_Guide.pdf')

# ── Colour palette ─────────────────────────────────────────────────────────────
C_NAVY   = colors.HexColor('#1A2744')
C_GREEN  = colors.HexColor('#16A34A')
C_TEAL   = colors.HexColor('#0F766E')
C_ORANGE = colors.HexColor('#EA580C')
C_LGREY  = colors.HexColor('#F1F5F9')
C_MGREY  = colors.HexColor('#94A3B8')
C_BLACK  = colors.HexColor('#0F172A')
C_WHITE  = colors.white
C_CUDA   = colors.HexColor('#76B900')   # NVIDIA green


# ─────────────────────────────────────────────────────────────────────────────
# Styles
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
    s['h2'] = ParagraphStyle('H2', fontSize=13, leading=17,
        textColor=colors.HexColor('#2563EB'),
        spaceBefore=12, spaceAfter=4, fontName='Helvetica-Bold')
    s['h3'] = ParagraphStyle('H3', fontSize=11, leading=15, textColor=C_NAVY,
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
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def H(text, level, styles):
    return Paragraph(text, styles[level])

def P(text, styles):
    return Paragraph(text, styles['body'])

def B(items, styles):
    return [Paragraph(f'• {item}', styles['bullet']) for item in items]

def code_block(label, text, styles):
    out = []
    if label:
        out.append(Paragraph(label, styles['code_label']))
    out.append(Preformatted(text, styles['code']))
    return out

def hr(styles):
    return HRFlowable(width='100%', thickness=0.5, color=C_MGREY, spaceAfter=8)

def warn_box(text, styles):
    return Paragraph('WARNING:  ' + text, styles['warn'])

def note_box(text, styles):
    return Paragraph('NOTE:  ' + text, styles['note'])

def tip_box(text, styles):
    return Paragraph('TIP:  ' + text, styles['tip'])

def SP(n=6):
    return Spacer(1, n)


# ─────────────────────────────────────────────────────────────────────────────
# Diagram: CPU vs GPU execution model
# ─────────────────────────────────────────────────────────────────────────────
def _make_cpu_gpu_diagram():
    tmp = _tmpmod.NamedTemporaryFile(suffix='.png', delete=False)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    fig.patch.set_facecolor('white')

    def draw_side(ax, title, cores, core_color, note):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.axis('off')
        ax.set_facecolor('#F8FAFC')
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.text(5, 5.6, title, ha='center', va='center', fontsize=13,
                fontweight='bold', color='#1A2744')
        # draw cores
        ncols = min(cores, 16)
        nrows = (cores + ncols - 1) // ncols
        cw, ch = 0.45, 0.45
        startx = (10 - ncols * (cw + 0.12)) / 2
        starty = 4.6
        drawn = 0
        for r in range(nrows):
            for c in range(ncols):
                if drawn >= cores:
                    break
                x = startx + c * (cw + 0.12)
                y = starty - r * (ch + 0.12)
                ax.add_patch(FancyBboxPatch((x, y), cw, ch,
                    boxstyle='round,pad=0.04', facecolor=core_color,
                    edgecolor='white', linewidth=1.2, zorder=3))
                drawn += 1

        # task bar
        ax.add_patch(FancyBboxPatch((0.6, 0.5), 8.8, 0.65,
            boxstyle='round,pad=0.08', facecolor='#E2E8F0',
            edgecolor='#CBD5E1', linewidth=1, zorder=2))
        ax.text(5, 0.82, note, ha='center', va='center',
                fontsize=8, color='#374151')

    draw_side(axes[0], 'CPU  (4 cores @ 1.48 GHz)', 4, '#2563EB',
              'Tasks run one at a time per core — sequential processing')
    draw_side(axes[1], 'GPU  (128 CUDA cores @ 921 MHz)', 128, '#76B900',
              'All 128 cores run in parallel — massive throughput for data tasks')

    plt.tight_layout(pad=1.2)
    fig.savefig(tmp.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return tmp.name


# ─────────────────────────────────────────────────────────────────────────────
# Diagram: CUDA programming model
# ─────────────────────────────────────────────────────────────────────────────
def _make_cuda_model_diagram():
    tmp = _tmpmod.NamedTemporaryFile(suffix='.png', delete=False)
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0.2, 5.8)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    def box(cx, cy, w, h, text, fc, tc='white', fs=8.5):
        ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h,
            boxstyle='round,pad=0.1', facecolor=fc,
            edgecolor='white', linewidth=1.5, zorder=3))
        ax.text(cx, cy, text, ha='center', va='center',
                color=tc, fontsize=fs, fontweight='bold', zorder=4,
                multialignment='center', linespacing=1.3)

    def arrow(x1, y1, x2, y2, label=''):
        ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
            arrowprops=dict(arrowstyle='->', color='#64748B', lw=1.5), zorder=2)
        if label:
            ax.text((x1+x2)/2, (y1+y2)/2+0.18, label, ha='center',
                    fontsize=7, color='#374151', style='italic')

    # CPU side
    box(2.2, 4.8, 3.2, 0.7, 'CPU (Host)', '#1A2744', fs=10)
    box(2.2, 3.6, 3.2, 0.7, 'CPU Memory\n(RAM)', '#2563EB', fs=8)
    box(2.2, 2.2, 3.2, 0.9, '1. Allocate GPU memory\n2. Copy data → GPU\n3. Launch kernel\n4. Copy result ← GPU',
        '#3B82F6', fs=7)

    # GPU side
    box(9.5, 4.8, 3.8, 0.7, 'GPU (Device) — Maxwell', '#76B900', tc='#1A2744', fs=10)
    box(9.5, 3.6, 3.8, 0.7, 'GPU Memory\n(VRAM, shared with CPU on Nano)', '#16A34A', fs=8)

    # Blocks/threads
    for i, lbl in enumerate(['Thread Block 0', 'Thread Block 1', 'Thread Block 2']):
        bx = 7.2 + i * 1.7
        box(bx, 2.2, 1.5, 0.55, lbl, '#065F46', fs=6.5)
        for t in range(4):
            tx = bx - 0.56 + t * 0.37
            ax.add_patch(FancyBboxPatch((tx-0.14, 1.25), 0.28, 0.38,
                boxstyle='round,pad=0.04', facecolor='#6EE7B7',
                edgecolor='white', linewidth=0.8, zorder=3))
            ax.text(tx, 1.44, f'T{t}', ha='center', va='center',
                    fontsize=5.5, color='#065F46', fontweight='bold', zorder=4)

    ax.text(9.5, 0.85, '128 CUDA cores execute all threads simultaneously',
            ha='center', fontsize=7.5, color='#374151', style='italic')

    # PCI/memory bus arrows
    arrow(3.9, 3.6, 7.5, 3.6, 'cudaMemcpy')
    arrow(3.9, 2.2, 7.0, 2.2, 'kernel<<<grid,block>>>()')

    ax.text(7, 5.5, 'CUDA Programming Model — Jetson Nano', ha='center',
            fontsize=11, color='#1A2744', fontweight='bold')

    fig.savefig(tmp.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return tmp.name


# ─────────────────────────────────────────────────────────────────────────────
# Diagram: GPU pipeline for YOLO obstacle detection in ROS 2
# ─────────────────────────────────────────────────────────────────────────────
def _make_yolo_pipeline_diagram():
    tmp = _tmpmod.NamedTemporaryFile(suffix='.png', delete=False)
    fig, ax = plt.subplots(figsize=(13, 3.8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0.2, 4.0)
    ax.axis('off')
    fig.patch.set_facecolor('white')

    nodes = [
        (1.2,  2.0, 2.0, 0.7, '/camera/color\n/image_raw',      '#0EA5E9'),
        (3.7,  2.0, 2.2, 0.7, 'Preprocess\n(resize+normalize)', '#2563EB'),
        (6.3,  2.0, 2.2, 0.7, 'TensorRT\nInference (GPU)',      '#76B900'),
        (8.9,  2.0, 2.2, 0.7, 'Postprocess\n(NMS decode)',      '#2563EB'),
        (11.5, 2.0, 2.2, 0.7, 'Publish\n/detected_objects',     '#16A34A'),
    ]
    for cx, cy, w, h, text, fc in nodes:
        tc = '#1A2744' if fc == '#76B900' else 'white'
        ax.add_patch(FancyBboxPatch((cx-w/2, cy-h/2), w, h,
            boxstyle='round,pad=0.1', facecolor=fc,
            edgecolor='white', linewidth=1.5, zorder=3))
        ax.text(cx, cy, text, ha='center', va='center',
                color=tc, fontsize=8, fontweight='bold', zorder=4,
                multialignment='center', linespacing=1.3)

    for i in range(len(nodes)-1):
        x1 = nodes[i][0] + nodes[i][2]/2
        x2 = nodes[i+1][0] - nodes[i+1][2]/2
        y  = nodes[i][1]
        ax.annotate('', xy=(x2, y), xytext=(x1, y),
            arrowprops=dict(arrowstyle='->', color='#64748B', lw=1.5), zorder=2)

    ax.text(7, 3.6, 'GPU-Accelerated Obstacle Detection Pipeline (ROS 2 Node)',
            ha='center', fontsize=10, color='#1A2744', fontweight='bold')
    ax.text(6.3, 1.05, 'ONNX model optimised\nby TensorRT at startup',
            ha='center', fontsize=7, color='#374151', style='italic')

    fig.savefig(tmp.name, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return tmp.name


# ─────────────────────────────────────────────────────────────────────────────
# Cover page
# ─────────────────────────────────────────────────────────────────────────────
def cover_page(styles):
    story = []
    story.append(Spacer(1, 3.5*cm))
    story.append(Paragraph('Jetson Nano GPU Guide', styles['title']))
    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(
        'Using the 128-core Maxwell GPU on the Jetson Nano for Robot Software',
        styles['subtitle']))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        'DIY Challenge Repo  ·  ROS 2 Humble  ·  CUDA 11.x  ·  TensorRT',
        styles['subtitle']))
    story.append(Spacer(1, 2.5*cm))

    tbl_data = [
        [Paragraph('Target Platform', styles['th']),
         Paragraph('NVIDIA Jetson Nano 4 GB (JetPack 5.x)', styles['tc'])],
        [Paragraph('GPU Architecture', styles['th']),
         Paragraph('Maxwell — 128 CUDA cores, 921 MHz', styles['tc'])],
        [Paragraph('CUDA Version', styles['th']),
         Paragraph('11.4 (from JetPack 5.x)', styles['tc'])],
        [Paragraph('TensorRT Version', styles['th']),
         Paragraph('8.x (from JetPack 5.x)', styles['tc'])],
        [Paragraph('ROS 2 Version', styles['th']),
         Paragraph('Humble', styles['tc'])],
        [Paragraph('Current GPU Usage', styles['th']),
         Paragraph('0% — navigation stack is CPU-only (this guide changes that)', styles['tc'])],
    ]
    tbl = Table(tbl_data, colWidths=[5.5*cm, 11.9*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), C_NAVY),
        ('BACKGROUND', (1,0), (1,-1), C_LGREY),
        ('ROWBACKGROUNDS', (1,0), (1,-1), [C_LGREY, colors.white]),
        ('GRID', (0,0), (-1,-1), 0.4, C_MGREY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(tbl)
    story.append(PageBreak())
    return story


# ─────────────────────────────────────────────────────────────────────────────
# Document body
# ─────────────────────────────────────────────────────────────────────────────
def build_story(styles):
    story = []
    story += cover_page(styles)

    # ── Section 1: What is the GPU and when does it help? ──────────────────────
    story.append(H('1. What Is the Jetson Nano GPU and When Does It Help?', 'h1', styles))
    story.append(hr(styles))

    story.append(H('1.1  Hardware overview', 'h2', styles))
    story.append(P(
        'The Jetson Nano contains a <b>128-core NVIDIA Maxwell GPU</b> on the same '
        'die as the 4-core ARM Cortex-A57 CPU. Unlike a gaming GPU that has '
        'thousands of cores, the Maxwell is a small but capable GPU designed for '
        'embedded inference workloads. The CPU and GPU share the same physical '
        'RAM (4 GB LPDDR4) — this means data does not have to travel over a '
        'PCIe bus; it can be passed between CPU and GPU with near-zero copy '
        'overhead.', styles))

    story.append(H('1.2  CPU vs GPU — the fundamental difference', 'h2', styles))
    story.append(P(
        'A CPU is optimised for running a small number of complex, sequential '
        'tasks quickly. A GPU is optimised for running a very large number of '
        'simple tasks simultaneously. The diagram below illustrates this:',
        styles))

    _cpu_gpu_png = _make_cpu_gpu_diagram()
    story.append(RLImage(_cpu_gpu_png, width=16.5*cm, height=6.8*cm))
    story.append(SP())

    story.append(P(
        '<b>Practical implication</b>: if your algorithm processes each lidar '
        'point, each image pixel, or each neural-network weight in sequence '
        '(like a Python for-loop), the GPU cannot help. If the same operation '
        'can be applied to thousands of data elements <i>at the same time</i>, '
        'the GPU can be 10-100× faster than the CPU.', styles))

    story.append(H('1.3  What currently runs on the CPU in this repo', 'h2', styles))
    story += B([
        '<b>FAST-LIO2</b> — Eigen matrix math + ikd-Tree on CPU (4 threads)',
        '<b>LIO-SAM</b> — GTSAM factor graphs + OpenMP CPU threads',
        '<b>Nav2 (MPPI planner)</b> — trajectory sampling on CPU',
        '<b>EKF nodes</b> — single-threaded Kalman filter math',
        '<b>cmd_vel_mux</b> — simple topic arbitration, trivially CPU',
        '<b>estop_controller</b> — heartbeat watchdog, trivially CPU',
    ], styles)
    story.append(note_box(
        'None of these are GPU bottlenecked — they are compute-bound on the CPU '
        'in ways that map poorly to GPU parallelism. Adding GPU code to these '
        'nodes would not meaningfully improve performance and would add '
        'significant complexity.', styles))

    story.append(H('1.4  Where the GPU CAN help in a robot like this', 'h2', styles))
    tbl_data = [
        [Paragraph('Use Case', styles['th']),
         Paragraph('GPU Benefit', styles['th']),
         Paragraph('Complexity', styles['th']),
         Paragraph('Typical Speedup', styles['th'])],
        [Paragraph('Object detection (YOLO)', styles['tc']),
         Paragraph('TensorRT runs neural network inference', styles['tc']),
         Paragraph('Medium', styles['tc']),
         Paragraph('10-50×', styles['tc'])],
        [Paragraph('Point cloud filtering / downsampling', styles['tc']),
         Paragraph('CUDA parallelises voxel grid on all points at once', styles['tc']),
         Paragraph('Medium', styles['tc']),
         Paragraph('3-10×', styles['tc'])],
        [Paragraph('Stereo depth from D435i images', styles['tc']),
         Paragraph('CUDA Semi-Global Matching', styles['tc']),
         Paragraph('High', styles['tc']),
         Paragraph('5-20×', styles['tc'])],
        [Paragraph('Image preprocessing (resize, normalise)', styles['tc']),
         Paragraph('CUDA/cuDNN accelerates for DNN pipelines', styles['tc']),
         Paragraph('Low (via cuDNN)', styles['tc']),
         Paragraph('2-5×', styles['tc'])],
        [Paragraph('Nav2 MPPI trajectory sampling', styles['tc']),
         Paragraph('Experimental GPU MPPI in Nav2 Jazzy+', styles['tc']),
         Paragraph('High (Nav2 Humble does not support it)', styles['tc']),
         Paragraph('2-8×', styles['tc'])],
    ]
    tbl = Table(tbl_data, colWidths=[4.8*cm, 6.2*cm, 3.2*cm, 3.2*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_LGREY, colors.white]),
        ('GRID', (0,0), (-1,-1), 0.4, C_MGREY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story += [SP(), tbl, SP()]
    story.append(PageBreak())

    # ── Section 2: CUDA Basics ─────────────────────────────────────────────────
    story.append(H('2. CUDA Programming Basics', 'h1', styles))
    story.append(hr(styles))
    story.append(P(
        'CUDA (Compute Unified Device Architecture) is NVIDIA\'s programming '
        'model for GPU computing. You write special C++ functions called '
        '<b>kernels</b> that run on the GPU. The CUDA compiler (<code>nvcc</code>) '
        'compiles them alongside your normal C++ code.', styles))

    story.append(H('2.1  Key concepts', 'h2', styles))
    story += B([
        '<b>Host</b>: the CPU and its RAM. Your normal C++ code runs here.',
        '<b>Device</b>: the GPU and its memory. CUDA kernels run here.',
        '<b>Kernel</b>: a GPU function marked <code>__global__</code>. '
        'Called from CPU, runs on GPU.',
        '<b>Thread</b>: the smallest unit of work on the GPU. Thousands run simultaneously.',
        '<b>Block</b>: a group of threads that share fast on-chip memory.',
        '<b>Grid</b>: the collection of all blocks for one kernel launch.',
        '<b>cudaMalloc / cudaFree</b>: allocate/free GPU memory.',
        '<b>cudaMemcpy</b>: copy data between CPU and GPU memory.',
    ], styles)

    story.append(H('2.2  CUDA programming model diagram', 'h2', styles))
    _cuda_png = _make_cuda_model_diagram()
    story.append(RLImage(_cuda_png, width=16.5*cm, height=7.0*cm))
    story.append(SP())

    story.append(H('2.3  Minimal working CUDA example', 'h2', styles))
    story.append(P(
        'The example below adds two arrays on the GPU — the GPU equivalent of '
        'a simple for-loop. This is the smallest useful CUDA program.', styles))
    story += code_block('vector_add.cu — minimal CUDA kernel example', """\
// vector_add.cu
#include <stdio.h>

// The __global__ keyword marks this as a GPU kernel.
// Each GPU thread runs this function once with a different blockIdx/threadIdx.
__global__ void vectorAdd(float* A, float* B, float* C, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;  // which element am I?
    if (i < n) {
        C[i] = A[i] + B[i];   // each thread adds one pair of elements
    }
}

int main() {
    int n = 1024;
    size_t bytes = n * sizeof(float);

    // 1. Allocate CPU (host) memory
    float *h_A = (float*)malloc(bytes);
    float *h_B = (float*)malloc(bytes);
    float *h_C = (float*)malloc(bytes);
    for (int i = 0; i < n; i++) { h_A[i] = i; h_B[i] = i * 2; }

    // 2. Allocate GPU (device) memory
    float *d_A, *d_B, *d_C;
    cudaMalloc(&d_A, bytes);
    cudaMalloc(&d_B, bytes);
    cudaMalloc(&d_C, bytes);

    // 3. Copy data from CPU → GPU
    cudaMemcpy(d_A, h_A, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_B, h_B, bytes, cudaMemcpyHostToDevice);

    // 4. Launch 1024 threads in blocks of 256
    int blockSize = 256;
    int gridSize  = (n + blockSize - 1) / blockSize;   // = 4 blocks
    vectorAdd<<<gridSize, blockSize>>>(d_A, d_B, d_C, n);

    // 5. Copy result GPU → CPU
    cudaMemcpy(h_C, d_C, bytes, cudaMemcpyDeviceToHost);

    printf("C[0]=%f  C[1023]=%f\\n", h_C[0], h_C[1023]);  // 0, 3069

    // 6. Free GPU memory
    cudaFree(d_A); cudaFree(d_B); cudaFree(d_C);
    free(h_A);     free(h_B);     free(h_C);
    return 0;
}""", styles)
    story += code_block('Compile and run on Jetson Nano', """\
# nvcc is the CUDA compiler (comes with JetPack)
nvcc -o vector_add vector_add.cu
./vector_add
# Output: C[0]=0.000000  C[1023]=3069.000000""", styles)

    story.append(H('2.4  What changes vs normal C++', 'h2', styles))
    tbl_data = [
        [Paragraph('Concept', styles['th']),
         Paragraph('Normal C++', styles['th']),
         Paragraph('CUDA equivalent', styles['th'])],
        [Paragraph('Function on GPU', styles['tc']),
         Paragraph('— (not possible)', styles['tc']),
         Paragraph('__global__ void kernel(...)', styles['tc'])],
        [Paragraph('Allocate memory', styles['tc']),
         Paragraph('malloc() / new', styles['tc']),
         Paragraph('cudaMalloc()', styles['tc'])],
        [Paragraph('Free memory', styles['tc']),
         Paragraph('free() / delete', styles['tc']),
         Paragraph('cudaFree()', styles['tc'])],
        [Paragraph('Copy data', styles['tc']),
         Paragraph('memcpy()', styles['tc']),
         Paragraph('cudaMemcpy()', styles['tc'])],
        [Paragraph('Launch function', styles['tc']),
         Paragraph('func(args)', styles['tc']),
         Paragraph('func<<<grid, block>>>(args)', styles['tc'])],
        [Paragraph('File extension', styles['tc']),
         Paragraph('.cpp', styles['tc']),
         Paragraph('.cu', styles['tc'])],
        [Paragraph('Compiler', styles['tc']),
         Paragraph('g++', styles['tc']),
         Paragraph('nvcc', styles['tc'])],
    ]
    tbl = Table(tbl_data, colWidths=[4.5*cm, 5.5*cm, 7.4*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_LGREY, colors.white]),
        ('GRID', (0,0), (-1,-1), 0.4, C_MGREY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story += [SP(), tbl, SP()]
    story.append(PageBreak())

    # ── Section 3: TensorRT — the right way to use the GPU for inference ───────
    story.append(H('3. TensorRT — GPU Inference Without Writing CUDA', 'h1', styles))
    story.append(hr(styles))
    story.append(P(
        'For robot applications, <b>you almost never need to write raw CUDA kernels</b>. '
        'NVIDIA\'s <b>TensorRT</b> library is a high-performance deep learning '
        'inference engine that: (1) takes a trained neural network (ONNX format), '
        '(2) optimises it automatically for the specific GPU it is running on, '
        'and (3) runs it as fast as possible — all without you writing a single '
        'line of CUDA. This is the practical way to use the Jetson GPU.', styles))

    story.append(H('3.1  The TensorRT workflow', 'h2', styles))
    story += B([
        '<b>Train</b> your model (e.g. YOLOv8) on a desktop/cloud GPU using PyTorch',
        '<b>Export</b> to ONNX format (<code>model.export(format="onnx")</code>)',
        '<b>Convert</b> on the Jetson: TensorRT parses the ONNX and builds a '
        '<code>.engine</code> file optimised for the Maxwell GPU (takes ~5 min, done once)',
        '<b>Run</b> the <code>.engine</code> file at inference time — TensorRT handles all '
        'GPU memory management, kernel selection, and parallelism automatically',
    ], styles)

    story.append(H('3.2  Install TensorRT (already in JetPack)', 'h2', styles))
    story += code_block('Verify TensorRT is installed from JetPack', """\
# TensorRT is pre-installed with JetPack 5.x. Verify:
python3 -c "import tensorrt; print(tensorrt.__version__)"
# Expected: 8.x.x

dpkg -l | grep -i tensorrt    # list all TensorRT packages

# Also check the C++ headers are present:
ls /usr/include/x86_64-linux-gnu/NvInfer.h 2>/dev/null || \\
ls /usr/include/aarch64-linux-gnu/NvInfer.h  # Jetson is aarch64""", styles)

    story.append(H('3.3  Install torch2trt and onnxruntime-gpu (optional helpers)', 'h2', styles))
    story += code_block('Install Python TensorRT helpers', """\
# onnxruntime-gpu — run ONNX models on GPU without converting to TensorRT engine
pip3 install onnxruntime-gpu

# torch2trt — convert PyTorch models directly to TensorRT (skips ONNX step)
git clone https://github.com/NVIDIA-AI-IOT/torch2trt
cd torch2trt && sudo python3 setup.py install""", styles)

    story.append(H('3.4  Convert YOLOv8 to TensorRT — step by step', 'h2', styles))
    story.append(P(
        'This section walks through adding GPU-based object detection to the '
        'robot. The detector publishes <code>/detected_objects</code> '
        '(vision_msgs/Detection2DArray) which Nav2 collision monitor can '
        'subscribe to as a dynamic obstacle source.', styles))
    story += code_block('Step 1: Export YOLOv8 to ONNX (on laptop/desktop)', """\
# Install ultralytics on your laptop (not Jetson — uses more RAM)
pip install ultralytics

# Download a pretrained model and export to ONNX
python3 - << 'EOF'
from ultralytics import YOLO
model = YOLO("yolov8n.pt")           # 'n' = nano (smallest, fastest)
model.export(format="onnx",
             imgsz=640,
             simplify=True,
             dynamic=False)          # saves yolov8n.onnx
EOF

# Copy yolov8n.onnx to the Jetson:
scp yolov8n.onnx ubuntu@jetson.local:~/models/""", styles)

    story += code_block('Step 2: Build TensorRT engine on the Jetson (run once)', """\
# SSH into Jetson first, then:
mkdir -p ~/models && cd ~/models

# Use trtexec (comes with TensorRT) to build the engine
/usr/src/tensorrt/bin/trtexec \\
    --onnx=yolov8n.onnx \\
    --saveEngine=yolov8n_fp16.engine \\
    --fp16 \\                         # half-precision: 2x speed on Maxwell GPU
    --workspace=1024                  # MB of GPU workspace

# This takes 3-8 minutes. The output .engine file is hardware-specific.
# Do NOT copy the .engine file between different machines.""", styles)

    story += code_block('Step 3: Run inference from Python (test)', """\
import tensorrt as trt
import numpy as np
import pycuda.driver as cuda
import pycuda.autoinit
import cv2

# Load the engine
logger = trt.Logger(trt.Logger.WARNING)
with open("/home/ubuntu/models/yolov8n_fp16.engine", "rb") as f:
    runtime = trt.Runtime(logger)
    engine  = runtime.deserialize_cuda_engine(f.read())

context = engine.create_execution_context()

# Allocate GPU buffers (one per input/output binding)
inputs, outputs, bindings = [], [], []
stream = cuda.Stream()
for i in range(engine.num_io_tensors):
    name  = engine.get_tensor_name(i)
    shape = engine.get_tensor_shape(name)
    dtype = trt.nptype(engine.get_tensor_dtype(name))
    size  = int(np.prod(shape))
    host_mem   = cuda.pagelocked_empty(size, dtype)
    device_mem = cuda.mem_alloc(host_mem.nbytes)
    bindings.append(int(device_mem))
    if engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
        inputs.append({'host': host_mem, 'device': device_mem})
    else:
        outputs.append({'host': host_mem, 'device': device_mem})

# Run one inference on a test image
img = cv2.imread("test.jpg")
img = cv2.resize(img, (640, 640))
img = img.astype(np.float32) / 255.0
img = img.transpose(2, 0, 1)         # HWC -> CHW
np.copyto(inputs[0]['host'], img.ravel())

# Copy input CPU -> GPU, run, copy output GPU -> CPU
cuda.memcpy_htod_async(inputs[0]['device'], inputs[0]['host'], stream)
context.execute_async_v2(bindings, stream.handle, None)
cuda.memcpy_dtoh_async(outputs[0]['host'], outputs[0]['device'], stream)
stream.synchronize()

print("Inference complete. Output shape:", outputs[0]['host'].shape)""", styles)

    story.append(warn_box(
        'The TensorRT .engine file is built for a specific GPU architecture AND '
        'TensorRT version. Always build it on the Jetson Nano itself, not on '
        'your laptop. If you update JetPack, rebuild the engine.', styles))
    story.append(PageBreak())

    # ── Section 4: ROS 2 node with GPU inference ──────────────────────────────
    story.append(H('4. Adding a GPU Inference Node to the ROS 2 Stack', 'h1', styles))
    story.append(hr(styles))
    story.append(P(
        'The practical approach is to wrap the TensorRT inference in a '
        'standard ROS 2 Python node. The node subscribes to the camera '
        'image topic, runs GPU inference, and publishes detections. No '
        'changes to FAST-LIO2 or Nav2 are required.', styles))

    story.append(H('4.1  Pipeline overview', 'h2', styles))
    _yolo_png = _make_yolo_pipeline_diagram()
    story.append(RLImage(_yolo_png, width=16.5*cm, height=4.8*cm))
    story.append(SP())

    story.append(H('4.2  Create the ROS 2 package', 'h2', styles))
    story += code_block('Create diy_obstacle_detector package', """\
cd ~/ros2_ws/src/DIY-Challenge-Repo/src
ros2 pkg create --build-type ament_python diy_obstacle_detector \\
    --dependencies rclpy sensor_msgs vision_msgs cv_bridge""", styles)

    story.append(H('4.3  GPU inference node (complete implementation)', 'h2', styles))
    story += code_block('src/diy_obstacle_detector/diy_obstacle_detector/detector_node.py', """\
#!/usr/bin/env python3
'''
GPU-accelerated YOLOv8 obstacle detector - ROS 2 Humble node.
Subscribes to /camera/color/image_raw, runs TensorRT inference on the
Jetson GPU, publishes /detected_objects (vision_msgs/Detection2DArray).
'''
import numpy as np
import cv2
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit          # initialises CUDA context automatically

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray, Detection2D, BoundingBox2D
from cv_bridge import CvBridge


class DetectorNode(Node):
    def __init__(self):
        super().__init__('diy_obstacle_detector')

        # Parameters — set via launch file or ros2 param set
        self.declare_parameter('engine_path',  '/home/ubuntu/models/yolov8n_fp16.engine')
        self.declare_parameter('conf_threshold', 0.45)
        self.declare_parameter('input_size',    640)

        engine_path  = self.get_parameter('engine_path').value
        self.conf_th = self.get_parameter('conf_threshold').value
        self.inp_sz  = self.get_parameter('input_size').value

        # Load TensorRT engine
        self.get_logger().info(f'Loading TensorRT engine: {engine_path}')
        logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, 'rb') as f:
            runtime = trt.Runtime(logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()

        # Allocate pinned CPU buffers and GPU buffers for TensorRT IO
        self.inputs, self.outputs, self.bindings = [], [], []
        self.stream = cuda.Stream()
        for i in range(self.engine.num_io_tensors):
            name  = self.engine.get_tensor_name(i)
            shape = self.engine.get_tensor_shape(name)
            dtype = trt.nptype(self.engine.get_tensor_dtype(name))
            size  = int(np.prod(shape))
            host_mem   = cuda.pagelocked_empty(size, dtype)
            device_mem = cuda.mem_alloc(host_mem.nbytes)
            self.bindings.append(int(device_mem))
            entry = {'host': host_mem, 'device': device_mem, 'shape': shape}
            if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                self.inputs.append(entry)
            else:
                self.outputs.append(entry)

        self.bridge = CvBridge()
        self.sub    = self.create_subscription(
            Image, '/camera/color/image_raw', self.image_cb, 10)
        self.pub    = self.create_publisher(
            Detection2DArray, '/detected_objects', 10)

        self.get_logger().info('Detector ready — GPU inference active.')

    def image_cb(self, msg: Image):
        # Convert ROS Image → OpenCV BGR
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h_orig, w_orig = frame.shape[:2]

        # Preprocess: resize → normalise → CHW layout
        inp = cv2.resize(frame, (self.inp_sz, self.inp_sz))
        inp = inp.astype(np.float32) / 255.0
        inp = inp.transpose(2, 0, 1)   # (H, W, C) -> (C, H, W)

        # Copy to pinned host buffer and run GPU inference
        np.copyto(self.inputs[0]['host'], inp.ravel())
        cuda.memcpy_htod_async(self.inputs[0]['device'],
                               self.inputs[0]['host'], self.stream)
        self.context.execute_async_v2(self.bindings, self.stream.handle)
        cuda.memcpy_dtoh_async(self.outputs[0]['host'],
                               self.outputs[0]['device'], self.stream)
        self.stream.synchronize()   # wait for GPU to finish

        # Decode YOLOv8 output: shape (1, 84, 8400) → filter by confidence
        raw = self.outputs[0]['host'].reshape(1, 84, -1)[0]  # (84, 8400)
        raw = raw.T                                           # (8400, 84)
        scores = raw[:, 4:].max(axis=1)
        mask   = scores > self.conf_th
        raw    = raw[mask]
        scores = scores[mask]

        det_array = Detection2DArray()
        det_array.header = msg.header
        sx = w_orig / self.inp_sz
        sy = h_orig / self.inp_sz

        for row, score in zip(raw, scores):
            cx, cy, w, h = row[:4]
            det = Detection2D()
            det.bbox.center.position.x = float(cx * sx)
            det.bbox.center.position.y = float(cy * sy)
            det.bbox.size_x = float(w * sx)
            det.bbox.size_y = float(h * sy)
            det_array.detections.append(det)

        self.pub.publish(det_array)


def main(args=None):
    rclpy.init(args=args)
    node = DetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()""", styles)

    story.append(H('4.4  Add to challenge_master.launch.py (optional)', 'h2', styles))
    story += code_block('Integration snippet for challenge_master.launch.py', """\
# Add this block inside generate_launch_description():
from launch_ros.actions import Node as LaunchNode

obstacle_detector = LaunchNode(
    package='diy_obstacle_detector',
    executable='detector_node',
    name='diy_obstacle_detector',
    parameters=[{
        'engine_path':    '/home/ubuntu/models/yolov8n_fp16.engine',
        'conf_threshold': 0.45,
        'input_size':     640,
    }],
    remappings=[('/camera/color/image_raw', '/camera/color/image_raw')],
)

# Then add obstacle_detector to the return list in generate_launch_description()""", styles)

    story.append(H('4.5  Connect detections to Nav2 collision monitor', 'h2', styles))
    story.append(P(
        'The Nav2 Collision Monitor can subscribe to '
        '<code>/detected_objects</code> as a dynamic obstacle source, '
        'causing the robot to slow down or stop when objects are detected '
        'in the camera field of view.', styles))
    story += code_block('Add to collision_monitor_params.yaml', """\
collision_monitor:
  ros__parameters:
    polygon_action: "stop"
    observation_sources: [lidar_scan, camera_detections]

    # Existing lidar source ...

    camera_detections:
      type: "Detection2D"
      topic: "/detected_objects"
      min_height: 0.1
      max_height: 2.0""", styles)
    story.append(PageBreak())

    # ── Section 5: GPU-accelerated point cloud processing ────────────────────
    story.append(H('5. GPU-Accelerated Point Cloud Processing (CUDA)', 'h1', styles))
    story.append(hr(styles))
    story.append(P(
        'If FAST-LIO2 is struggling with processing speed at high lidar frequencies, '
        'a GPU voxel-grid filter applied upstream can reduce the point count '
        'from ~65,000 QT64 points to ~5,000 before FAST-LIO2 ever sees them. '
        'This is one of the few places where writing a small amount of CUDA code '
        'directly provides a meaningful benefit.', styles))

    story.append(H('5.1  Option A: use CUDAlib (no raw CUDA needed)', 'h2', styles))
    story += code_block('Install and use cuda-pcl for point cloud filtering', """\
# cuda-pcl is NVIDIA's GPU-accelerated PCL equivalent
git clone https://github.com/NVIDIA-AI-IOT/cuda-pcl.git
cd cuda-pcl && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4 && sudo make install

# Use CudaVoxelGrid in your ROS 2 node instead of pcl::VoxelGrid:
# #include <cudaVoxelGrid.h>
# CudaVoxelGrid<pcl::PointXYZI> vg;
# vg.setLeafSize(0.1f, 0.1f, 0.1f);
# vg.setInputCloud(input_cloud);
# vg.filter(*output_cloud);   // runs on GPU""", styles)

    story.append(H('5.2  Option B: write a minimal CUDA voxel filter kernel', 'h2', styles))
    story.append(P(
        'The following is a conceptual skeleton showing how a GPU voxel filter '
        'works. Each CUDA thread checks whether a point belongs to an occupied '
        'voxel cell and keeps only one representative per cell.', styles))
    story += code_block('voxel_filter_kernel.cu — conceptual skeleton', """\
// Each thread processes one input point.
// Atomically marks a voxel as occupied; only the first thread to claim
// a voxel writes its point to the output.
__global__ void voxelFilterKernel(
    const float4* __restrict__ input,   // x, y, z, intensity
    float4*       output,
    int*          output_count,
    int           n_points,
    float         leaf_size)
{
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n_points) return;

    float4 p = input[idx];

    // Compute voxel bin index (simple hash)
    int ix = (int)(p.x / leaf_size);
    int iy = (int)(p.y / leaf_size);
    int iz = (int)(p.z / leaf_size);

    // Only ONE representative per voxel reaches the output.
    // (Full implementation uses a hash table in shared memory)
    int slot = atomicAdd(output_count, 1);
    output[slot] = p;
}

// Host call:
// dim3 block(256);
// dim3 grid((n_points + 255) / 256);
// voxelFilterKernel<<<grid, block>>>(d_input, d_output, d_count, n, 0.1f);""", styles)

    story.append(note_box(
        'For most teams, Option A (cuda-pcl) is the right choice — complex '
        'hash-table voxel grids are hard to implement efficiently in raw CUDA. '
        'Use cuda-pcl unless you have a specific reason to write your own kernel.', styles))
    story.append(PageBreak())

    # ── Section 6: Verify GPU usage and performance monitoring ───────────────
    story.append(H('6. Verify GPU Usage and Monitor Performance', 'h1', styles))
    story.append(hr(styles))
    story += code_block('Check that the GPU is actually being used', """\
# Install jtop (Jetson system monitor — install once)
sudo pip3 install jetson-stats
sudo systemctl restart jtop.service  # needed after first install

# Run jtop — provides a live dashboard with CPU, GPU, RAM, temp
jtop

# Key column in jtop to watch:
#   GPU %  — should jump from ~0% to 30-80% when inference is running
#   RAM    — GPU uses system RAM; watch for OOM during model load
#   Temp   — keep GPU below 75°C

# Alternative: tegrastats (built-in, no install needed)
tegrastats --interval 500
# Look for:  GPU xxx%  in the output line""", styles)

    story += code_block('Benchmark TensorRT inference speed', """\
# trtexec can benchmark the engine directly (before adding to ROS 2):
/usr/src/tensorrt/bin/trtexec \\
    --loadEngine=/home/ubuntu/models/yolov8n_fp16.engine \\
    --batch=1 \\
    --iterations=200

# Expected output for YOLOv8n FP16 on Jetson Nano:
#   mean: ~12-18 ms/inference  →  ~55-85 FPS
# Compare to CPU (onnxruntime, no GPU):
#   mean: ~180-300 ms/inference  →  ~3-5 FPS""", styles)

    story += code_block('Python micro-benchmark — time one inference call', """\
import time, numpy as np, pycuda.driver as cuda, pycuda.autoinit, tensorrt as trt

# (load engine and create context as shown in Section 4.3)

dummy_input = np.random.rand(3, 640, 640).astype(np.float32)
np.copyto(inputs[0]['host'], dummy_input.ravel())

# Warm-up (first call initialises caches)
for _ in range(5):
    cuda.memcpy_htod_async(inputs[0]['device'], inputs[0]['host'], stream)
    context.execute_async_v2(bindings, stream.handle)
    cuda.memcpy_dtoh_async(outputs[0]['host'], outputs[0]['device'], stream)
    stream.synchronize()

# Timed runs
t0 = time.perf_counter()
N = 100
for _ in range(N):
    cuda.memcpy_htod_async(inputs[0]['device'], inputs[0]['host'], stream)
    context.execute_async_v2(bindings, stream.handle)
    cuda.memcpy_dtoh_async(outputs[0]['host'], outputs[0]['device'], stream)
    stream.synchronize()
print(f"Mean latency: {(time.perf_counter()-t0)/N*1000:.1f} ms")
print(f"Throughput:   {N/(time.perf_counter()-t0):.1f} FPS")""", styles)

    story.append(tip_box(
        'Always run jetson_clocks before benchmarking or running inference '
        'at competition. The GPU clock defaults to a lower frequency at boot '
        'and can be 2× slower without clock locking. '
        'See Section 5.7 of DIY_Challenge_Robot_Guide.pdf for the persistent '
        'systemd service that locks clocks at startup.', styles))
    story.append(PageBreak())

    # ── Section 7: Quick-Reference Checklist ─────────────────────────────────
    story.append(H('7. Quick-Reference Checklist', 'h1', styles))
    story.append(hr(styles))

    story.append(H('One-time setup (do once on the Jetson)', 'h2', styles))
    story += B([
        'Verify JetPack version: <code>cat /etc/nv_tegra_release</code>',
        'Verify CUDA: <code>nvcc --version</code> → 11.4.x',
        'Verify TensorRT: <code>python3 -c "import tensorrt; print(tensorrt.__version__)"</code>',
        'Install jetson-stats: <code>sudo pip3 install jetson-stats</code>',
        'Create models directory: <code>mkdir -p ~/models</code>',
        'Export YOLOv8n to ONNX on laptop, copy to <code>~/models/yolov8n.onnx</code>',
        'Build TensorRT engine on Jetson with <code>trtexec --fp16</code>',
        'Verify engine with trtexec benchmark → should show &gt;50 FPS for YOLOv8n',
    ], styles)

    story.append(H('Every run (before launching the robot)', 'h2', styles))
    story += B([
        '<code>sudo nvpmodel -m 0</code> — switch to MAXN (10W) power mode',
        '<code>sudo jetson_clocks</code> — lock CPU/GPU to max frequency',
        '<code>jtop</code> — confirm GPU clock is at maximum (921 MHz or close)',
        'Check GPU temperature is below 40°C at idle before a long run',
    ], styles)

    story.append(H('Troubleshooting GPU issues', 'h2', styles))
    tbl_data = [
        [Paragraph('Problem', styles['th']),
         Paragraph('Likely Cause', styles['th']),
         Paragraph('Fix', styles['th'])],
        [Paragraph('GPU % stays at 0% in jtop', styles['tc']),
         Paragraph('TensorRT engine not loaded / node not running', styles['tc']),
         Paragraph('Check ros2 node list, check engine path parameter', styles['tc'])],
        [Paragraph('CUDA out of memory error', styles['tc']),
         Paragraph('Model too large for 4 GB shared RAM', styles['tc']),
         Paragraph('Use yolov8n (nano) not larger variants; add 4 GB swap', styles['tc'])],
        [Paragraph('trtexec shows <20 FPS on YOLOv8n', styles['tc']),
         Paragraph('GPU clock not locked', styles['tc']),
         Paragraph('Run sudo jetson_clocks, check nvpmodel -q shows mode 0', styles['tc'])],
        [Paragraph('Engine file fails to load', styles['tc']),
         Paragraph('Engine built on different TensorRT version', styles['tc']),
         Paragraph('Rebuild engine on THIS Jetson after any JetPack update', styles['tc'])],
        [Paragraph('Inference latency spikes', styles['tc']),
         Paragraph('Thermal throttling (GPU > 85°C)', styles['tc']),
         Paragraph('Add heatsink/fan; check jtop Temp column', styles['tc'])],
    ]
    tbl = Table(tbl_data, colWidths=[4.0*cm, 6.0*cm, 7.4*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_LGREY, colors.white]),
        ('GRID', (0,0), (-1,-1), 0.4, C_MGREY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('WORDWRAP', (0,0), (-1,-1), True),
    ]))
    story += [SP(), tbl, SP()]

    story.append(H('Further reading', 'h2', styles))
    story += B([
        'CUDA C++ Programming Guide: https://docs.nvidia.com/cuda/cuda-c-programming-guide/',
        'TensorRT Developer Guide: https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/',
        'YOLOv8 on Jetson (NVIDIA blog): https://developer.nvidia.com/blog/real-time-object-detection-on-jetson-nano/',
        'Jetson Nano Developer Kit User Guide: https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-devkit',
        'cuda-pcl (GPU point cloud library): https://github.com/NVIDIA-AI-IOT/cuda-pcl',
    ], styles)

    return story


# ─────────────────────────────────────────────────────────────────────────────
# Page template callbacks
# ─────────────────────────────────────────────────────────────────────────────
def _on_page(canvas, doc, styles):
    canvas.saveState()
    W, H = A4
    # Header bar
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, H - 1.2*cm, W, 1.2*cm, fill=True, stroke=False)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(C_WHITE)
    canvas.drawString(1.8*cm, H - 0.8*cm, 'Jetson Nano GPU Guide')
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(W - 1.8*cm, H - 0.8*cm,
                           f'DIY Challenge Repo  ·  CUDA 11.x / TensorRT 8.x')
    # Footer
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(C_MGREY)
    canvas.drawCentredString(W / 2, 0.7*cm, f'Page {doc.page}')
    canvas.restoreState()


def _on_cover(canvas, doc):
    W, H = A4
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, 0, W, H, fill=True, stroke=False)
    # NVIDIA green accent bar
    canvas.setFillColor(C_CUDA)
    canvas.rect(0, H * 0.58, W, 0.35*cm, fill=True, stroke=False)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    styles = make_styles()

    doc = SimpleDocTemplate(
        OUT_PATH,
        pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.8*cm,  bottomMargin=1.6*cm,
        title='Jetson Nano GPU Guide',
        author='DIY Challenge Repo',
    )

    story = build_story(styles)

    doc.build(
        story,
        onFirstPage=_on_cover,
        onLaterPages=lambda c, d: _on_page(c, d, styles),
    )
    print(f'PDF generated: {OUT_PATH}')


if __name__ == '__main__':
    main()
