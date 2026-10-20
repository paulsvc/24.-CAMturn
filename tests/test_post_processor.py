from __future__ import annotations

import pytest

from lathecam.cam.commands import MotionCmd
from lathecam.post.fanuc import FanucPostProcessor
from lathecam.post.linuxcnc import LinuxCNCPostProcessor


def test_linuxcnc_preamble_and_footer() -> None:
    post = LinuxCNCPostProcessor(is_diameter_mode=True)
    cmds = [MotionCmd.rapid(x=10.0, z=5.0)]
    gcode = post.export(cmds, metadata={"tool_id": 1, "css_m_min": 180, "max_rpm": 2200})

    lines = [l.strip() for l in gcode.strip().split("\n")]
    assert lines[0] == "%"
    # Mandatory LinuxCNC turning preamble
    assert "G18 G21 G40 G49 G80 G90 G95 G7" in lines

    # Tool change with G43 offset activation
    assert "T1 M6 G43" in lines

    # Constant surface speed with LinuxCNC 'D' clamp word (Never G50)
    assert "G96 D2200 S180 M3" in lines
    assert "G50" not in gcode

    # Footer
    assert lines[-4:] == ["M5", "M9", "M30", "%"]


def test_critical_g7_diameter_vs_g18_arc_rule() -> None:
    """CRITICAL INVARIANT TEST:
    When G7 Diameter Mode is active:
    - X coordinates must be DOUBLED (radius 15.0 -> X30.000)
    - I and K incremental arc center offsets must REMAIN UNSCALED (I0.000, K-5.000).
    """
    post = LinuxCNCPostProcessor(is_diameter_mode=True)
    cmds = [
        # Radius mode: X=15.0mm (Diameter = 30.0mm)
        # Arc center offset from start: I=0.0 (X-offset), K=-5.0 (Z-offset)
        MotionCmd.arc(mode="G2", x=15.0, z=-10.0, i=0.0, k=-5.0, f=0.15)
    ]
    gcode = post.export(cmds)

    arc_line = [l for l in gcode.splitlines() if l.startswith("G2")][0]
    # Check X is 30.000 (scaled by 2.0)
    assert "X30.000" in arc_line
    # Check Z is -10.000 (unscaled)
    assert "Z-10.000" in arc_line
    # Check I is 0.000 (strictly radius offset, NOT multiplied by 2)
    assert "I0.000" in arc_line
    # Check K is -5.000 (strictly distance offset)
    assert "K-5.000" in arc_line
    assert "F0.150" in arc_line


def test_g8_radius_mode() -> None:
    """When G8 Radius Mode is active:
    - Preamble uses G8
    - X coordinates are NOT doubled (radius 15.0 -> X15.000)
    """
    post = LinuxCNCPostProcessor(is_diameter_mode=False)
    cmds = [
        MotionCmd.linear(x=15.0, z=-10.0, f=0.2),
        MotionCmd.arc(mode="G3", x=20.0, z=-15.0, i=5.0, k=0.0, f=0.2),
    ]
    gcode = post.export(cmds)

    assert "G18 G21 G40 G49 G80 G90 G95 G8" in gcode
    assert "G1 X15.000 Z-10.000" in gcode
    assert "G3 X20.000 Z-15.000 I5.000 K0.000" in gcode


def test_linuxcnc_canned_cycles() -> None:
    post = LinuxCNCPostProcessor(is_diameter_mode=True, unroll_canned_cycles=False)
    cmds = [
        # G76 Threading block
        MotionCmd(
            mode="G76",
            x=10.0,
            z=-20.0,
            raw_params={
                "p": 1.5,
                "z": -20.0,
                "i": -0.2,
                "j": 0.25,
                "k": 0.92,
                "r": 1.0,
                "q": 29.5,
                "h": 2,
                "e": 0.0,
                "l": 0,
            },
        ),
        # G83 Peck drilling block
        MotionCmd(
            mode="G83",
            x=0.0,
            z=-35.0,
            f=0.12,
            raw_params={
                "r_plane": 1.0,
                "peck_q": 3.0,
            },
        ),
    ]

    gcode = post.export(cmds)

    # Assert G76 line
    g76_line = [l for l in gcode.splitlines() if l.startswith("G76")][0]
    assert "P1.500" in g76_line
    assert "Z-20.000" in g76_line
    assert "I-0.200" in g76_line
    assert "J0.250" in g76_line
    assert "K0.920" in g76_line
    assert "R1.000" in g76_line
    assert "Q29.500" in g76_line
    assert "H2" in g76_line

    # Assert G83 line when unroll_canned_cycles=False
    g83_line = [l for l in gcode.splitlines() if l.startswith("G83")][0]
    assert "X0.000" in g83_line
    assert "Z-35.000" in g83_line
    assert "R1.000" in g83_line
    assert "Q3.000" in g83_line
    assert "F0.120" in g83_line


def test_linuxcnc_unrolled_peck_drilling() -> None:
    """Verifies default LinuxCNC 2-axis lathe drilling unrolls G83 into explicit G0/G1 pecks
    to prevent 'G18 canned cycle is not possible on a machine without Y axis'.
    """
    post = LinuxCNCPostProcessor(is_diameter_mode=True, unroll_canned_cycles=True)
    cmds = [
        MotionCmd(
            mode="G83",
            x=0.0,
            z=-12.0,
            f=0.12,
            raw_params={"r_plane": 1.0, "peck_q": 4.0},
        ),
        MotionCmd(mode="G80"),
    ]
    gcode = post.export(cmds)
    motion_lines = gcode.splitlines()[3:]  # Skip preamble which initializes modal state
    assert not any(l.startswith("G83") for l in motion_lines)
    assert not any(l.strip() == "G80" for l in motion_lines)
    assert "G1 Z-4.000 F0.120" in gcode
    assert "G0 Z1.000" in gcode
    assert "G0 Z-3.500" in gcode
    assert "G1 Z-8.000 F0.120" in gcode
    assert "G1 Z-12.000 F0.120" in gcode



def test_fanuc_post_processor() -> None:
    post = FanucPostProcessor(is_diameter_mode=True)
    cmds = [
        MotionCmd.arc(mode="G2", x=15.0, z=-10.0, i=0.0, k=-5.0, f=0.15),
        MotionCmd(
            mode="G76",
            x=10.0,
            z=-20.0,
            raw_params={"p": 1.5, "z": -20.0, "j": 0.25, "k": 0.92, "h": 2},
        ),
    ]
    gcode = post.export(cmds, metadata={"tool_id": 2, "css_m_min": 200, "max_rpm": 2500})
    assert "G50 S2500" in gcode
    assert "T0202" in gcode
    assert "G96 S200 M03" in gcode
    assert "G02 X30.000 Z-10.000 I0.000 K-5.000 F0.150" in gcode
    assert "G76 P020060" in gcode
    assert "G28 U0.0 W0.0" in gcode


