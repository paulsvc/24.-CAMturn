from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from lathecam.cam.commands import MotionCmd
from lathecam.cam.tools import LatheTool
from lathecam.models.stock import Stock


class FacingOp:
    """Facing operation: cuts perpendicular to the spindle axis across the front of the stock down past centerline."""

    def __init__(
        self,
        stock: Stock,
        tool: LatheTool,
        stepover_z_mm: float = 1.0,
        feed_mm_rev: float = 0.20,
        clearance_x_mm: float = 1.5,
        retract_z_mm: float = 1.0,
        target_z_mm: float = 0.0,
    ) -> None:
        self.stock = stock
        self.tool = tool
        self.stepover_z_mm = stepover_z_mm
        self.feed_mm_rev = feed_mm_rev
        self.clearance_x_mm = clearance_x_mm
        self.retract_z_mm = retract_z_mm
        self.target_z_mm = target_z_mm

    def generate(self) -> list[MotionCmd]:
        commands: list[MotionCmd] = []
        commands.append(MotionCmd.comment(f"Facing Operation: Z={self.stock.z_start_mm:.2f} -> Z={self.target_z_mm:.2f}"))

        start_x = self.stock.od_radius + self.clearance_x_mm
        # Plunge past centerline by nose radius to ensure no nib is left on the part face
        end_x = -max(0.2, self.tool.nose_radius_mm)

        current_z = self.stock.z_start_mm
        # If stock is already at target_z_mm or negative, we do at least one cleanup facing pass
        z_passes: list[float] = []
        if current_z > self.target_z_mm:
            while current_z > self.target_z_mm:
                current_z = max(self.target_z_mm, current_z - self.stepover_z_mm)
                z_passes.append(current_z)
        else:
            z_passes.append(self.target_z_mm)

        commands.append(MotionCmd.rapid(x=start_x, z=self.stock.z_start_mm + self.retract_z_mm))

        for z_cut in z_passes:
            # 1. Position at start of facing cut
            commands.append(MotionCmd.rapid(x=start_x, z=z_cut + self.retract_z_mm))
            commands.append(MotionCmd.rapid(x=start_x, z=z_cut))
            # 2. Linear plunge down past centerline
            commands.append(MotionCmd.linear(x=end_x, z=z_cut, f=self.feed_mm_rev))
            # 3. Retract along Z
            commands.append(MotionCmd.linear(x=end_x, z=z_cut + self.retract_z_mm, f=self.feed_mm_rev * 2.0))
            # 4. Rapid back to safe diameter
            commands.append(MotionCmd.rapid(x=start_x, z=z_cut + self.retract_z_mm))

        commands.append(MotionCmd.rapid(x=start_x, z=self.stock.z_start_mm + self.retract_z_mm))
        commands.append(MotionCmd.comment("End Facing Operation"))
        return commands


class ThreadingOp:
    """LinuxCNC G76 Canned Threading Cycle with unrolled G33 preview passes."""

    def __init__(
        self,
        pitch_mm: float,
        major_dia_mm: float,
        z_start_mm: float = 0.0,
        z_end_mm: float = -20.0,
        thread_depth_mm: float | None = None,
        infeed_angle_deg: float = 29.5,
        initial_cut_depth_mm: float = 0.20,
        depth_degression: float = 1.0,
        spring_passes: int = 1,
        taper_len_mm: float = 0.0,
        end_taper_type: int = 0,
    ) -> None:
        self.pitch_mm = pitch_mm
        self.major_dia_mm = major_dia_mm
        self.major_radius = major_dia_mm / 2.0
        self.z_start_mm = z_start_mm
        self.z_end_mm = z_end_mm
        # Standard metric external thread height: 0.61343 * pitch
        self.thread_depth_mm = thread_depth_mm if thread_depth_mm is not None else 0.61343 * pitch_mm
        self.infeed_angle_deg = infeed_angle_deg
        self.initial_cut_depth_mm = initial_cut_depth_mm
        self.depth_degression = depth_degression
        self.spring_passes = spring_passes
        self.taper_len_mm = taper_len_mm
        self.end_taper_type = end_taper_type

    def generate(self) -> list[MotionCmd]:
        commands: list[MotionCmd] = []
        commands.append(MotionCmd.comment(f"Threading Operation: M{self.major_dia_mm:.1f}x{self.pitch_mm:.2f} Z={self.z_start_mm:.1f} -> {self.z_end_mm:.1f}"))

        safe_x = self.major_radius + 2.0
        lead_in_z = self.z_start_mm + 2.0 * self.pitch_mm  # Acceleration distance

        # Position at start
        commands.append(MotionCmd.rapid(x=safe_x, z=lead_in_z))

        # LinuxCNC G76 block
        # P = Pitch
        # Z = End of thread
        # I = Thread peak offset (negative for external threads: clearance from drive line)
        # J = Initial cut depth
        # K = Full thread depth
        # R = Depth degression (1.0 = constant volume)
        # Q = Infeed angle (typically 29.5 deg)
        # H = Spring passes
        # E = Taper entry/exit length
        # L = Taper exit type
        g76_params = {
            "p": self.pitch_mm,
            "z": self.z_end_mm,
            "i": -0.2,  # Clearance offset
            "j": self.initial_cut_depth_mm,
            "k": self.thread_depth_mm,
            "r": self.depth_degression,
            "q": self.infeed_angle_deg,
            "h": self.spring_passes,
            "e": self.taper_len_mm,
            "l": self.end_taper_type,
        }
        commands.append(MotionCmd(
            mode="G76",
            x=self.major_radius,
            z=self.z_end_mm,
            raw_params=g76_params,
        ))

        commands.append(MotionCmd.rapid(x=safe_x, z=lead_in_z))
        commands.append(MotionCmd.comment("End Threading Operation"))
        return commands

    def generate_unrolled_g33_preview(self) -> list[MotionCmd]:
        """Generates unrolled G33 preview passes with constant chip-area degression and modified flank infeed."""
        preview_cmds: list[MotionCmd] = []
        safe_x = self.major_radius + 1.5
        lead_in_z = self.z_start_mm + 2.0 * self.pitch_mm

        infeed_rad = math.radians(self.infeed_angle_deg)
        total_k = self.thread_depth_mm
        first_j = self.initial_cut_depth_mm

        # Estimate number of passes using constant chip volume
        num_passes = max(2, int(math.ceil((total_k / first_j) ** 2)))

        for n in range(1, num_passes + 1):
            depth = min(total_k, first_j * math.sqrt(n))
            current_radius = self.major_radius - depth
            z_infeed_shift = depth * math.tan(infeed_rad)

            # Move to start with flank infeed shift
            pass_start_z = lead_in_z - z_infeed_shift
            pass_end_z = self.z_end_mm - z_infeed_shift

            preview_cmds.append(MotionCmd.rapid(x=safe_x, z=pass_start_z))
            preview_cmds.append(MotionCmd.linear(x=current_radius, z=pass_start_z))
            # G33 synchronized move
            preview_cmds.append(MotionCmd(mode="G33", x=current_radius, z=pass_end_z, k=self.pitch_mm))
            preview_cmds.append(MotionCmd.rapid(x=safe_x, z=pass_end_z))
            preview_cmds.append(MotionCmd.rapid(x=safe_x, z=lead_in_z))

        # Spring passes
        for _ in range(self.spring_passes):
            current_radius = self.major_radius - total_k
            z_infeed_shift = total_k * math.tan(infeed_rad)
            pass_start_z = lead_in_z - z_infeed_shift
            pass_end_z = self.z_end_mm - z_infeed_shift

            preview_cmds.append(MotionCmd.rapid(x=safe_x, z=pass_start_z))
            preview_cmds.append(MotionCmd.linear(x=current_radius, z=pass_start_z))
            preview_cmds.append(MotionCmd(mode="G33", x=current_radius, z=pass_end_z, k=self.pitch_mm))
            preview_cmds.append(MotionCmd.rapid(x=safe_x, z=pass_end_z))
            preview_cmds.append(MotionCmd.rapid(x=safe_x, z=lead_in_z))

        return preview_cmds


class PartingOp:
    """Peck Parting and Grooving Operation with chip-break retracts."""

    def __init__(
        self,
        stock: Stock,
        tool: LatheTool,
        target_z_mm: float,
        target_x_radius_mm: float = 0.0,
        peck_depth_mm: float = 1.5,
        feed_mm_rev: float = 0.06,
        chip_break_retract_mm: float = 0.5,
    ) -> None:
        self.stock = stock
        self.tool = tool
        self.target_z_mm = target_z_mm
        self.target_x_radius_mm = target_x_radius_mm
        self.peck_depth_mm = peck_depth_mm
        self.feed_mm_rev = feed_mm_rev
        self.chip_break_retract_mm = chip_break_retract_mm

    def generate(self) -> list[MotionCmd]:
        commands: list[MotionCmd] = []
        commands.append(MotionCmd.comment(f"Begin Parting/Grooving Op at Z={self.target_z_mm:.2f} -> X={self.target_x_radius_mm:.2f}"))

        safe_x = self.stock.od_radius + 1.5
        commands.append(MotionCmd.rapid(x=safe_x, z=self.target_z_mm))

        current_x = self.stock.od_radius

        while current_x > self.target_x_radius_mm + 1e-4:
            next_x = max(self.target_x_radius_mm, current_x - self.peck_depth_mm)
            # Linear feed plunge
            commands.append(MotionCmd.linear(x=next_x, z=self.target_z_mm, f=self.feed_mm_rev))

            # Chip break retract (only if we still have more to cut)
            if next_x > self.target_x_radius_mm + 1e-4:
                retract_x = min(safe_x, next_x + self.chip_break_retract_mm)
                commands.append(MotionCmd.rapid(x=retract_x, z=self.target_z_mm))
                # Rapid back to previous peck bottom before continuing
                commands.append(MotionCmd.rapid(x=next_x + 0.1, z=self.target_z_mm))

            current_x = next_x

        # Dwell/retract back to safe clearance
        commands.append(MotionCmd.rapid(x=safe_x, z=self.target_z_mm))
        commands.append(MotionCmd.comment("End Parting/Grooving Op"))
        return commands


class DrillingOp:
    """Axial Center-line Drilling Operation using LinuxCNC G83 (peck) or G73 (chip break)."""

    def __init__(
        self,
        z_depth_mm: float,
        peck_q_mm: float = 3.0,
        feed_mm_rev: float = 0.12,
        r_plane_mm: float = 1.0,
        rpm: int = 1000,
        cycle_type: str = "G83",
    ) -> None:
        self.z_depth_mm = z_depth_mm
        self.peck_q_mm = peck_q_mm
        self.feed_mm_rev = feed_mm_rev
        self.r_plane_mm = r_plane_mm
        self.rpm = rpm
        self.cycle_type = cycle_type

    def generate(self) -> list[MotionCmd]:
        commands: list[MotionCmd] = []
        commands.append(MotionCmd.comment(f"Drilling Operation ({self.cycle_type}): Depth={self.z_depth_mm:.2f}mm"))

        # Switch spindle to constant RPM mode for axial drilling
        commands.append(MotionCmd(mode="SPINDLE_RPM", raw_params={"rpm": self.rpm}))

        # Position at centerline X=0.0 and safe clearance
        commands.append(MotionCmd.rapid(x=0.0, z=self.r_plane_mm + 2.0))

        # Emit canned cycle command
        commands.append(MotionCmd(
            mode=self.cycle_type,
            x=0.0,
            z=self.z_depth_mm,
            f=self.feed_mm_rev,
            raw_params={
                "r_plane": self.r_plane_mm,
                "peck_q": self.peck_q_mm,
            },
        ))

        # Cancel canned cycle
        commands.append(MotionCmd(mode="G80"))
        commands.append(MotionCmd.rapid(x=0.0, z=self.r_plane_mm + 5.0))
        commands.append(MotionCmd.comment("End Drilling Operation"))
        return commands
