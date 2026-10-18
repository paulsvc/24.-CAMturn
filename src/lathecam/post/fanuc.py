from __future__ import annotations

from typing import Any, Sequence

from lathecam.cam.commands import MotionCmd
from lathecam.post.base_post import BasePostProcessor


class FanucPostProcessor(BasePostProcessor):
    """Post-processor generating Fanuc 0i-TF turning dialect G-code (.nc).
    
    Key Fanuc 0i-TF conventions:
    - Preamble: G18 G21 G40 G80 G99 (G99 = Feed per revolution in Fanuc Type A)
    - Tool change: T{tool:02d}{offset:02d} (e.g., T0101)
    - Max RPM clamp & CSS: G50 S{max_rpm} followed by G96 S{css} M03
    - Constant RPM: G97 S{rpm} M03
    - Diameter Mode (X = 2.0 * radius) with incremental arc center offsets I (radius) and K (axial)
    - Two-line G76 threading cycle and G74 axial peck drilling cycle.
    """

    def __init__(self, is_diameter_mode: bool = True) -> None:
        super().__init__(is_diameter_mode=is_diameter_mode)

    def _fmt(self, val: float) -> str:
        return f"{val:.3f}"

    def export(
        self,
        commands: Sequence[MotionCmd],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        meta = metadata or {}
        lines: list[str] = []

        lines.append("%")
        prog_num = meta.get("program_number", "O0001")
        comment_hdr = meta.get("program_name", "LATHECAM FANUC 0I-TF")
        lines.append(f"{prog_num} ({comment_hdr.upper()})")
        lines.append("G18 G21 G40 G80 G99")

        if "tool_id" in meta:
            t_id = int(meta["tool_id"])
            lines.append(f"T{t_id:02d}{t_id:02d}")
        if "css_m_min" in meta or "max_rpm" in meta:
            d_rpm = int(meta.get("max_rpm", 2500))
            s_css = int(meta.get("css_m_min", 200))
            lines.append(f"G50 S{d_rpm}")
            lines.append(f"G96 S{s_css} M03")

        x_scale = 2.0 if self.is_diameter_mode else 1.0

        for cmd in commands:
            if cmd.mode == "COMMENT":
                text = cmd.raw_params.get("comment", "") if cmd.raw_params else ""
                lines.append(f"({text.upper()})")
                continue

            if cmd.mode == "TOOL_CHANGE":
                t_id = int(cmd.raw_params.get("tool_id", 1)) if cmd.raw_params else 1
                lines.append(f"T{t_id:02d}{t_id:02d}")
                continue

            if cmd.mode == "SPINDLE_CSS":
                params = cmd.raw_params or {}
                d_rpm = int(params.get("max_rpm", 2500))
                s_css = int(params.get("css_m_min", 200))
                lines.append(f"G50 S{d_rpm}")
                lines.append(f"G96 S{s_css} M03")
                continue

            if cmd.mode == "SPINDLE_RPM":
                params = cmd.raw_params or {}
                s_rpm = int(params.get("rpm", 1000))
                lines.append(f"G97 S{s_rpm} M03")
                continue

            if cmd.mode in ("G0", "G1"):
                code = "G00" if cmd.mode == "G0" else "G01"
                parts = [code]
                if cmd.x is not None:
                    parts.append(f"X{self._fmt(cmd.x * x_scale)}")
                if cmd.z is not None:
                    parts.append(f"Z{self._fmt(cmd.z)}")
                if cmd.f is not None and cmd.mode == "G1":
                    parts.append(f"F{self._fmt(cmd.f)}")
                lines.append(" ".join(parts))
                continue

            if cmd.mode in ("G2", "G3"):
                code = "G02" if cmd.mode == "G2" else "G03"
                parts = [code]
                if cmd.x is not None:
                    parts.append(f"X{self._fmt(cmd.x * x_scale)}")
                if cmd.z is not None:
                    parts.append(f"Z{self._fmt(cmd.z)}")
                if cmd.i is not None:
                    parts.append(f"I{self._fmt(cmd.i)}")
                if cmd.k is not None:
                    parts.append(f"K{self._fmt(cmd.k)}")
                if cmd.f is not None:
                    parts.append(f"F{self._fmt(cmd.f)}")
                lines.append(" ".join(parts))
                continue

            if cmd.mode in ("G41", "G42", "G40"):
                parts = [cmd.mode]
                if cmd.x is not None:
                    parts.append(f"X{self._fmt(cmd.x * x_scale)}")
                if cmd.z is not None:
                    parts.append(f"Z{self._fmt(cmd.z)}")
                if cmd.f is not None and cmd.mode != "G40":
                    parts.append(f"F{self._fmt(cmd.f)}")
                lines.append(" ".join(parts))
                continue

            if cmd.mode == "G76":
                p = cmd.raw_params or {}
                pitch = float(p.get("p", 1.5))
                z_end = float(p.get("z", cmd.z if cmd.z is not None else -10.0))
                j_first = float(p.get("j", 0.2))
                k_depth = float(p.get("k", 0.92))
                h_spring = int(p.get("h", 1))
                major_r = cmd.x if cmd.x is not None else 8.0
                minor_x = (major_r - k_depth) * x_scale

                # Fanuc 2-block G76:
                # Line 1: G76 P(m)(r)(a) Q(min_cut_microns) R(finish_allowance)
                # Line 2: G76 X(minor_dia) Z(z_end) P(depth_microns) Q(first_cut_microns) F(pitch)
                p_word = f"{h_spring:02d}0060"
                p_microns = int(round(k_depth * 1000))
                q_microns = int(round(j_first * 1000))
                lines.append(f"G76 P{p_word} Q50 R0.02")
                lines.append(
                    f"G76 X{self._fmt(minor_x)} Z{self._fmt(z_end)} P{p_microns} Q{q_microns} F{self._fmt(pitch)}"
                )
                continue

            if cmd.mode in ("G83", "G73"):
                p = cmd.raw_params or {}
                z_depth = float(cmd.z if cmd.z is not None else -10.0)
                q_peck_microns = int(round(float(p.get("peck_q", 2.0)) * 1000))
                feed = float(cmd.f if cmd.f is not None else 0.12)
                lines.append("G74 R1.0")
                lines.append(f"G74 X0.000 Z{self._fmt(z_depth)} Q{q_peck_microns} F{self._fmt(feed)}")
                continue

            if cmd.mode == "G80":
                lines.append("G80")
                continue

        lines.append("G28 U0.0 W0.0")
        lines.append("M05")
        lines.append("M09")
        lines.append("M30")
        lines.append("%")
        return "\n".join(lines) + "\n"
