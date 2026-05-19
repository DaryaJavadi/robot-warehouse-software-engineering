"""Hand-drawn area / line charts using flet.canvas (Flet 0.84 has no native LineChart)."""
from __future__ import annotations

import flet as ft
import flet.canvas as cv

from theme import Colors


def _smooth_path_points(values: list[float], width: float, height: float,
                        padding: float = 8.0) -> list[tuple[float, float]]:
    """Map values (0-1) to evenly-spaced (x, y) coords inside the box."""
    n = len(values)
    if n == 0:
        return []
    inner_w = width - padding * 2
    inner_h = height - padding * 2
    step = inner_w / max(n - 1, 1)
    pts = []
    for i, v in enumerate(values):
        x = padding + i * step
        y = padding + (1 - max(0.0, min(1.0, v))) * inner_h
        pts.append((x, y))
    return pts


def _build_path(values: list[float], width: float, height: float,
                fill: bool, stroke_color: str, fill_color: str) -> cv.Path:
    pts = _smooth_path_points(values, width, height)
    if not pts:
        return cv.Path(elements=[])

    elements: list = [cv.Path.MoveTo(*pts[0])]
    # Cubic Bezier between consecutive points for smoothing
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        cx1 = x0 + (x1 - x0) / 2
        cy1 = y0
        cx2 = x0 + (x1 - x0) / 2
        cy2 = y1
        elements.append(cv.Path.CubicTo(cx1, cy1, cx2, cy2, x1, y1))

    if fill:
        last_x, _ = pts[-1]
        first_x, _ = pts[0]
        elements.append(cv.Path.LineTo(last_x, height - 4))
        elements.append(cv.Path.LineTo(first_x, height - 4))
        elements.append(cv.Path.Close())
        paint = ft.Paint(color=fill_color, style=ft.PaintingStyle.FILL)
    else:
        paint = ft.Paint(
            color=stroke_color,
            style=ft.PaintingStyle.STROKE,
            stroke_width=2.5,
            stroke_cap=ft.StrokeCap.ROUND,
            stroke_join=ft.StrokeJoin.ROUND,
        )
    return cv.Path(elements=elements, paint=paint)


def area_chart(values: list[float], height: int = 180,
               x_labels: list[str] | None = None,
               y_labels: list[str] | None = None,
               legend: list[tuple[str, str]] | None = None,
               second_values: list[float] | None = None,
               second_color: str = "#93C5FD") -> ft.Container:
    """Area chart with optional X / Y axis labels and legend."""

    def _build_canvas(width: float):
        shapes: list = []
        # Subtle horizontal gridlines
        rows = 4
        for i in range(rows + 1):
            y = (height - 16) * i / rows + 8
            shapes.append(
                cv.Line(
                    x1=8, y1=y, x2=width - 8, y2=y,
                    paint=ft.Paint(color=Colors.BORDER_LIGHT, stroke_width=1),
                )
            )
        # Filled area
        shapes.append(_build_path(
            values, width, height - 16, fill=True,
            stroke_color=Colors.CHART_BLUE,
            fill_color="#DBEAFE99",
        ))
        # Stroke line on top of fill
        shapes.append(_build_path(
            values, width, height - 16, fill=False,
            stroke_color=Colors.CHART_BLUE,
            fill_color="",
        ))
        if second_values:
            shapes.append(_build_path(
                second_values, width, height - 16, fill=False,
                stroke_color=second_color,
                fill_color="",
            ))
        return cv.Canvas(shapes=shapes, expand=True)

    # We don't know the width until layout — use a Stack + a sized container that
    # fills horizontally. Use canvas resize event to redraw.
    canvas_holder = ft.Container(expand=True, height=height - 16)

    def on_resize(e: cv.CanvasResizeEvent):
        canvas_holder.content = _build_canvas(e.width or 600)
        canvas_holder.update()

    placeholder = cv.Canvas(shapes=[], expand=True, on_resize=on_resize)
    canvas_holder.content = placeholder

    children: list[ft.Control] = [canvas_holder]
    if x_labels:
        children.append(ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text(lbl, size=11, color=Colors.TEXT_FAINT)
                for lbl in x_labels
            ],
        ))
    if legend:
        legend_row = ft.Row(
            spacing=18,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Row(spacing=6, controls=[
                    ft.Container(width=8, height=8, bgcolor=color, border_radius=2),
                    ft.Text(name, size=11, color=Colors.TEXT_MUTED),
                ])
                for name, color in legend
            ],
        )
        children.append(legend_row)

    return ft.Container(
        height=height + (24 if x_labels else 0) + (24 if legend else 0),
        content=ft.Column(spacing=4, controls=children),
    )
