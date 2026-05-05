"""Design tokens for FleetOps."""
from __future__ import annotations

import flet as ft


class Colors:
    PRIMARY = "#2563EB"
    PRIMARY_DARK = "#1D4ED8"
    PRIMARY_SOFT = "#EFF6FF"
    PRIMARY_BORDER = "#DBEAFE"

    DANGER = "#EF4444"
    DANGER_SOFT = "#FEF2F2"
    DANGER_BORDER = "#FECACA"

    WARNING = "#F59E0B"
    WARNING_SOFT = "#FFFBEB"

    SUCCESS = "#10B981"
    SUCCESS_SOFT = "#ECFDF5"

    BG = "#F8FAFC"
    SURFACE = "#FFFFFF"
    SIDEBAR = "#FFFFFF"
    SIDEBAR_HOVER = "#F1F5F9"

    TEXT = "#0F172A"
    TEXT_MUTED = "#64748B"
    TEXT_FAINT = "#94A3B8"
    BORDER = "#E2E8F0"
    BORDER_LIGHT = "#F1F5F9"

    CHART_BLUE = "#3B82F6"
    CHART_BLUE_FILL = "#DBEAFE"


CARD_RADIUS = 12
CARD_PADDING = 20

CARD_SHADOW = ft.BoxShadow(
    blur_radius=12,
    spread_radius=0,
    color="#0F172A14",
    offset=ft.Offset(0, 2),
)


def card(content, padding=CARD_PADDING, bgcolor=None, border_color=None) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=bgcolor or Colors.SURFACE,
        border_radius=CARD_RADIUS,
        border=ft.Border.all(1, border_color or Colors.BORDER),
    )


def text(value: str, size: int = 14, weight: ft.FontWeight | None = None,
         color: str | None = None) -> ft.Text:
    return ft.Text(value, size=size, weight=weight, color=color or Colors.TEXT)


def muted(value: str, size: int = 13) -> ft.Text:
    return ft.Text(value, size=size, color=Colors.TEXT_MUTED)


def h1(value: str) -> ft.Text:
    return ft.Text(value, size=28, weight=ft.FontWeight.BOLD, color=Colors.TEXT)


def h2(value: str) -> ft.Text:
    return ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT)
