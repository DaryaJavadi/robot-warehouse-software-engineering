"""Reusable card primitives matching the FleetOps design."""
from __future__ import annotations

import flet as ft

from theme import Colors, CARD_RADIUS


def kpi_tile(icon, value: str, label: str, trend: str | None = None,
             trend_color: str | None = None, icon_bg: str | None = None,
             icon_color: str | None = None) -> ft.Container:
    """Top-row metric tile: icon + delta on first row, big value + label below."""
    trend_text = ft.Text(
        trend or "",
        size=13,
        weight=ft.FontWeight.W_500,
        color=trend_color or Colors.TEXT_MUTED,
    )
    return ft.Container(
        bgcolor=Colors.SURFACE,
        border=ft.Border.all(1, Colors.BORDER),
        border_radius=CARD_RADIUS,
        padding=20,
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Container(
                            width=44, height=44,
                            bgcolor=icon_bg or Colors.PRIMARY_SOFT,
                            border_radius=10,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(icon, color=icon_color or Colors.PRIMARY, size=22),
                        ),
                        trend_text,
                    ],
                ),
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(value, size=28, weight=ft.FontWeight.BOLD,
                                color=Colors.TEXT),
                        ft.Text(label, size=13, color=Colors.TEXT_MUTED),
                    ],
                ),
            ],
        ),
    )


def status_badge(label: str, kind: str = "info") -> ft.Container:
    palette = {
        "working": (Colors.PRIMARY, Colors.PRIMARY_SOFT),
        "ready":   (Colors.TEXT_MUTED, "#F1F5F9"),
        "idle":    (Colors.TEXT_MUTED, "#F1F5F9"),
        "maintenance": (Colors.DANGER, Colors.DANGER_SOFT),
        "active":  (Colors.SUCCESS, Colors.SUCCESS_SOFT),
        "high":    (Colors.DANGER, Colors.DANGER_SOFT),
        "normal":  (Colors.TEXT_MUTED, "#F1F5F9"),
        "in_progress": (Colors.PRIMARY, Colors.PRIMARY_SOFT),
        "warning": (Colors.PRIMARY, Colors.PRIMARY_SOFT),
        "critical": (Colors.DANGER, Colors.DANGER_SOFT),
        "available": (Colors.TEXT_MUTED, "#F1F5F9"),
    }
    fg, bg = palette.get(kind, (Colors.TEXT_MUTED, "#F1F5F9"))
    return ft.Container(
        bgcolor=bg,
        border_radius=999,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        content=ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=fg),
    )


def panel(title: str, subtitle: str | None = None,
          trailing: ft.Control | None = None,
          body: ft.Control | None = None,
          padding: int = 20) -> ft.Container:
    header_left = ft.Column(
        spacing=2,
        controls=[
            ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
            *([ft.Text(subtitle, size=12, color=Colors.TEXT_MUTED)] if subtitle else []),
        ],
    )
    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[header_left, trailing or ft.Container()],
    )
    return ft.Container(
        bgcolor=Colors.SURFACE,
        border=ft.Border.all(1, Colors.BORDER),
        border_radius=CARD_RADIUS,
        padding=padding,
        content=ft.Column(
            spacing=16,
            controls=[header, body or ft.Container()],
        ),
    )


def alert_card(kind: str, title: str, body: str, meta: str, time: str) -> ft.Container:
    is_critical = kind in ("critical", "danger")
    border = Colors.DANGER if is_critical else Colors.BORDER
    bg = Colors.DANGER_SOFT if is_critical else Colors.SURFACE
    return ft.Container(
        bgcolor=bg,
        border=ft.Border.all(1, border),
        border_radius=10,
        padding=14,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(title.upper(), size=10, weight=ft.FontWeight.W_700,
                                color=Colors.TEXT_MUTED, no_wrap=True),
                        ft.Text(time, size=11, color=Colors.TEXT_FAINT),
                    ],
                ),
                ft.Text(body, size=13, weight=ft.FontWeight.W_600, color=Colors.TEXT),
                ft.Row(
                    spacing=4,
                    controls=[
                        ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=12, color=Colors.TEXT_FAINT),
                        ft.Text(meta, size=11, color=Colors.TEXT_MUTED),
                    ],
                ),
            ],
        ),
    )


def progress_bar(value: float, color: str | None = None,
                 bg: str | None = None, height: int = 6) -> ft.Container:
    """Thin progress bar — value is 0-1."""
    return ft.Container(
        height=height,
        bgcolor=bg or Colors.BORDER_LIGHT,
        border_radius=999,
        content=ft.Row(
            controls=[
                ft.Container(
                    expand=int(max(0.01, min(value, 1)) * 1000),
                    bgcolor=color or Colors.PRIMARY,
                    border_radius=999,
                    height=height,
                ),
                ft.Container(
                    expand=int((1 - max(0.01, min(value, 1))) * 1000) or 1,
                    height=height,
                ),
            ],
        ),
    )
