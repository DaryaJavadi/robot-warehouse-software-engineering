"""Inventory Zones screen — DB-backed."""
from __future__ import annotations

import flet as ft

import db
from theme import Colors
from components.cards import kpi_tile, panel, status_badge, progress_bar
import csv
from datetime import datetime
from pathlib import Path

from components.dialogs import show_snack, form_dialog, confirm, info_dialog


def _refresh(page: ft.Page) -> None:
    fn = (page.data or {}).get("refresh")
    if callable(fn):
        fn()


def _open_traffic_alert(page: ft.Page, title: str, meta: str,
                        critical: bool) -> None:
    body = ft.Column(spacing=10, controls=[
        ft.Container(
            bgcolor=Colors.DANGER_SOFT if critical else Colors.PRIMARY_SOFT,
            border=ft.Border.all(1, Colors.DANGER if critical
                                 else Colors.PRIMARY_BORDER),
            border_radius=8,
            padding=12,
            content=ft.Column(spacing=4, controls=[
                ft.Text(title, size=14, weight=ft.FontWeight.W_700,
                        color=Colors.DANGER if critical else Colors.PRIMARY),
                ft.Text(meta, size=11, color=Colors.TEXT_MUTED),
            ]),
        ),
        ft.Text("Suggested actions", size=12, weight=ft.FontWeight.W_700,
                color=Colors.TEXT_MUTED),
        ft.Text("• Run zone optimizer to redistribute load.\n"
                "• Reroute affected robots via Mission Controls.\n"
                "• Schedule a maintenance window for the bottleneck zone.",
                size=12, color=Colors.TEXT),
        ft.OutlinedButton(
            content=ft.Text("Acknowledge alert", size=13,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT),
            on_click=lambda _: (
                db.insert_alert("info", "TRAFFIC ACK",
                                f"Operator acknowledged: {title}",
                                "Traffic", "just now"),
                show_snack(page, "Acknowledged.", kind="success"),
                _refresh(page),
            ),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            ),
        ),
    ])
    info_dialog(page, "Traffic Alert", body)


def _export_inventory_csv(page: ft.Page) -> None:
    zones = db.list_zones()
    out_dir = Path(__file__).parent.parent / "exports"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"inventory-{ts}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "category", "used", "capacity",
                         "utilization_pct", "status"])
        for z in zones:
            pct = (z["used"] / z["capacity"] * 100) if z["capacity"] else 0
            writer.writerow([z["id"], z["name"], z["category"],
                             z["used"], z["capacity"],
                             f"{pct:.1f}", z["status"]])
    show_snack(page,
               f"Exported {len(zones)} zone(s) → exports/{out_path.name}",
               kind="success")


def _open_live_feed(page: ft.Page) -> None:
    alerts = db.list_alerts(limit=20)
    zones = sorted(db.list_zones(),
                   key=lambda z: (z["used"] / z["capacity"] if z["capacity"]
                                  else 0),
                   reverse=True)[:5]
    rows: list[ft.Control] = [
        ft.Text("Most recent alerts", size=12,
                weight=ft.FontWeight.W_700, color=Colors.TEXT_MUTED),
    ]
    if not alerts:
        rows.append(ft.Text("No alerts.", size=12, color=Colors.TEXT_MUTED))
    for a in alerts[:6]:
        rows.append(ft.Row(spacing=8, controls=[
            ft.Container(width=10, height=10,
                         bgcolor=Colors.DANGER if a["kind"] == "critical"
                         else Colors.PRIMARY,
                         border_radius=999),
            ft.Text(a["title"], size=12, weight=ft.FontWeight.W_600,
                    color=Colors.TEXT, expand=True),
            ft.Text(a["created_at"], size=11, color=Colors.TEXT_FAINT),
        ]))
    rows.append(ft.Divider(color=Colors.BORDER_LIGHT, thickness=1, height=1))
    rows.append(ft.Text("Top loaded zones", size=12,
                        weight=ft.FontWeight.W_700, color=Colors.TEXT_MUTED))
    for z in zones:
        pct = z["used"] / z["capacity"] if z["capacity"] else 0
        rows.append(ft.Row(spacing=8, controls=[
            ft.Text(z["name"], size=12, color=Colors.TEXT, expand=True),
            ft.Text(f"{int(pct*100)}%", size=12,
                    weight=ft.FontWeight.W_600,
                    color=Colors.DANGER if pct >= 0.9 else Colors.TEXT),
        ]))
    info_dialog(page, "Live Inventory Feed",
                ft.Column(spacing=8, tight=True, controls=rows))


def _header(page: ft.Page) -> ft.Control:
    title = ft.Column(spacing=4, controls=[
        ft.Text("Inventory Zones", size=28, weight=ft.FontWeight.BOLD,
                color=Colors.TEXT),
        ft.Text("Real-time spatial mapping and capacity management.",
                size=13, color=Colors.TEXT_MUTED),
    ])

    def optimize(_):
        confirm(page, "Run zone optimizer?",
                "This will mark zones over 90% utilization for rebalancing.",
                confirm_label="Optimize",
                on_confirm=lambda: (
                    db.insert_alert("info", "OPTIMIZATION RUN",
                                    "Zone rebalancing pass triggered.",
                                    "Zone Optimizer", "just now"),
                    show_snack(page, "Optimization queued.", kind="success"),
                    _refresh(page),
                ))

    actions = ft.Row(spacing=10, controls=[
        ft.OutlinedButton(
            content=ft.Row(spacing=6, tight=True, controls=[
                ft.Icon(ft.Icons.AUTO_GRAPH, size=16, color=Colors.TEXT),
                ft.Text("Live Feed", size=13,
                        weight=ft.FontWeight.W_600, color=Colors.TEXT),
            ]),
            on_click=lambda _: _open_live_feed(page),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        ),
        ft.ElevatedButton(
            content=ft.Row(spacing=6, tight=True, controls=[
                ft.Icon(ft.Icons.GRID_VIEW, size=16, color="#FFFFFF"),
                ft.Text("Optimize Zones", size=13,
                        weight=ft.FontWeight.W_600, color="#FFFFFF"),
            ]),
            bgcolor=Colors.PRIMARY, color="#FFFFFF",
            on_click=optimize,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                elevation=0,
            ),
        ),
    ])
    return ft.ResponsiveRow(
        run_spacing=14,
        controls=[
            ft.Container(content=title, col={"xs": 12, "lg": 7}),
            ft.Container(
                content=ft.Row(controls=[actions],
                               alignment=ft.MainAxisAlignment.END),
                col={"xs": 12, "lg": 5},
            ),
        ],
    )


def _kpis() -> ft.Control:
    k = db.zone_kpis()
    items = [
        kpi_tile(ft.Icons.SQUARE, f"{k['total_capacity']:,} units",
                 "Total Capacity", "↗ +2.4%", Colors.SUCCESS,
                 icon_bg=Colors.PRIMARY_SOFT, icon_color=Colors.PRIMARY),
        kpi_tile(ft.Icons.INVENTORY_2_OUTLINED, f"{k['active_load']:,} units",
                 "Active Load", "↗ +5.1%", Colors.SUCCESS,
                 icon_bg=Colors.PRIMARY_SOFT, icon_color=Colors.PRIMARY),
        kpi_tile(ft.Icons.BAR_CHART, f"{k['occupancy']}%", "Occupancy Rate",
                 "↘ -1.2%", Colors.DANGER,
                 icon_bg="#F1F5F9", icon_color=Colors.TEXT),
        kpi_tile(ft.Icons.STOP_CIRCLE, f"{k['critical']} Critical",
                 "Alert Zones", "↗ Stable", Colors.SUCCESS,
                 icon_bg=Colors.DANGER_SOFT, icon_color=Colors.DANGER),
    ]
    return ft.ResponsiveRow(
        run_spacing=14,
        controls=[ft.Container(content=i, col={"xs": 12, "sm": 6, "lg": 3})
                  for i in items],
    )


def _floor_tile(page: ft.Page, zone: dict) -> ft.Container:
    pct = zone["used"] / zone["capacity"] if zone["capacity"] else 0
    critical = zone["status"] == "CRITICAL"
    border_c = Colors.DANGER if critical else Colors.BORDER_LIGHT
    bg = Colors.DANGER_SOFT if critical else Colors.SURFACE
    name_color = Colors.DANGER if critical else Colors.TEXT

    def edit(_):
        def submit(values: dict):
            try:
                used = int(values.get("used", "0"))
                cap = int(values.get("capacity", "0"))
            except ValueError:
                show_snack(page, "Used and capacity must be integers.",
                           kind="error")
                return
            if cap <= 0:
                show_snack(page, "Capacity must be > 0.", kind="warning")
                return
            db.update_zone(zone["id"], used=used, capacity=cap)
            show_snack(page, f"{zone['name']} updated.", kind="success")
            _refresh(page)

        form_dialog(page, f"Edit {zone['name']}",
                    fields=[("used", "Used", str(zone["used"])),
                            ("capacity", "Capacity", str(zone["capacity"]))],
                    submit_label="Save",
                    on_submit=submit)

    return ft.Container(
        bgcolor=bg,
        border=ft.Border.all(1, border_c),
        border_radius=10,
        padding=14,
        ink=True, on_click=edit,
        content=ft.Column(spacing=10, controls=[
            ft.Text(zone["category"], size=10, weight=ft.FontWeight.W_700,
                    color=Colors.TEXT_MUTED),
            ft.Text(zone["name"], size=15, weight=ft.FontWeight.BOLD,
                    color=name_color),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.END,
                controls=[
                    ft.Text(f"{int(pct*100)}%", size=24,
                            weight=ft.FontWeight.BOLD, color=name_color),
                    ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=18,
                            color=Colors.DANGER if critical
                            else Colors.TEXT_FAINT),
                ],
            ),
        ]),
    )


def _floor_map(page: ft.Page) -> ft.Control:
    # Pick zones not already in the dashboard's "Zone A/B..." set
    zones = [z for z in db.list_zones() if z["category"] not in
             ("COLD", "BULK", "PICKING", "HAZ", "SORTING", "DISPATCH")][:8]
    grid = ft.ResponsiveRow(
        run_spacing=10,
        controls=[ft.Container(content=_floor_tile(page, z),
                               col={"xs": 12, "sm": 6, "lg": 3})
                  for z in zones],
    )

    legend = ft.Row(spacing=14, controls=[
        ft.Row(spacing=4, controls=[
            ft.Container(width=10, height=10, bgcolor=Colors.PRIMARY,
                         border_radius=999),
            ft.Text("Available", size=11, color=Colors.TEXT_MUTED),
        ]),
        ft.Row(spacing=4, controls=[
            ft.Container(width=10, height=10, bgcolor="#94A3B8",
                         border_radius=999),
            ft.Text("Full", size=11, color=Colors.TEXT_MUTED),
        ]),
        ft.Row(spacing=4, controls=[
            ft.Container(width=10, height=10, bgcolor=Colors.DANGER,
                         border_radius=999),
            ft.Text("Critical", size=11, color=Colors.TEXT_MUTED),
        ]),
    ])

    return panel(
        "Warehouse Floor Map",
        subtitle="Visual heatmap of storage density — click any zone to edit",
        trailing=legend,
        body=grid,
    )


def _optimization_ready_panel() -> ft.Container:
    zones = db.list_zones()
    over = [z for z in zones if z["status"] in ("CRITICAL", "WARNING")]
    if over:
        most = max(over, key=lambda z:
                   (z["used"] / z["capacity"]) if z["capacity"] else 0)
        msg = (f"{len(over)} zone(s) at risk — top candidate "
               f"for rebalancing: {most['name']}.")
    else:
        msg = "All zones within healthy load — no optimization needed."
    return ft.Container(
        bgcolor=Colors.PRIMARY_SOFT,
        border=ft.Border.all(1, Colors.PRIMARY_BORDER),
        border_radius=10,
        padding=12,
        content=ft.Column(spacing=4, controls=[
            ft.Row(spacing=6, controls=[
                ft.Icon(ft.Icons.AUTO_GRAPH, size=14, color=Colors.PRIMARY),
                ft.Text("Optimization Ready", size=13,
                        weight=ft.FontWeight.BOLD, color=Colors.PRIMARY),
            ]),
            ft.Text(msg, size=12, color=Colors.PRIMARY),
        ]),
    )


def _zone_breakdown(page: ft.Page) -> ft.Control:
    rows_data = [z for z in db.list_zones() if z["category"] not in
                 ("COLD", "BULK", "PICKING", "HAZ", "SORTING", "DISPATCH")]
    items: list[ft.Control] = []
    for z in rows_data:
        kind = "critical" if z["status"] == "CRITICAL" \
            else "warning" if z["status"] == "WARNING" \
            else "normal"
        pct = z["used"] / z["capacity"] if z["capacity"] else 0
        items.append(ft.Column(spacing=6, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(z["name"], size=13, weight=ft.FontWeight.W_600,
                            color=Colors.TEXT),
                    status_badge(z["status"], kind),
                ],
            ),
            ft.Row(controls=[
                ft.Text(f"{z['used']} Units / {z['capacity']} Max", size=11,
                        color=Colors.TEXT_MUTED, expand=True),
                ft.Text(f"{int(pct*100)}%", size=11,
                        weight=ft.FontWeight.W_600, color=Colors.TEXT),
            ]),
            progress_bar(pct,
                         color=Colors.DANGER if kind == "critical"
                         else Colors.PRIMARY),
        ]))
    body = ft.Column(spacing=14, controls=[
        *items,
        ft.OutlinedButton(
            content=ft.Text("Export Inventory Report", size=13,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT),
            on_click=lambda _: _export_inventory_csv(page),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        ),
        _optimization_ready_panel(),
    ])
    return panel(
        "Zone Breakdown",
        subtitle="Capacity vs Current Load",
        body=body,
    )


def _traffic_alerts(page: ft.Page) -> ft.Control:
    zones = db.list_zones()
    critical_zones = [z for z in zones if z["status"] == "CRITICAL"]
    warning_zones = [z for z in zones if z["status"] == "WARNING"]

    rows: list[tuple[str, str, bool]] = []
    for z in critical_zones[:3]:
        pct = (z["used"] / z["capacity"] * 100) if z["capacity"] else 0
        rows.append((
            f"{z['name']} at critical capacity ({int(pct)}%).",
            f"ZONE: {z['category']} • {z['used']} / {z['capacity']} units",
            True,
        ))
    for z in warning_zones[:max(0, 3 - len(rows))]:
        pct = (z["used"] / z["capacity"] * 100) if z["capacity"] else 0
        rows.append((
            f"{z['name']} approaching capacity ({int(pct)}%).",
            f"ZONE: {z['category']} • {z['used']} / {z['capacity']} units",
            False,
        ))
    if not rows:
        return panel(
            "Traffic & Congestion Alerts",
            trailing=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=18,
                             color=Colors.SUCCESS),
            body=ft.Text("No congested zones — all clear.", size=13,
                         color=Colors.TEXT_MUTED),
        )

    items: list[ft.Control] = []
    for title, meta, critical in rows:
        items.append(ft.Container(
            bgcolor=Colors.SURFACE,
            border_radius=10,
            border=ft.Border.all(1, Colors.BORDER_LIGHT),
            padding=14,
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=4, height=44,
                        bgcolor=Colors.DANGER if critical else Colors.BORDER,
                        border_radius=999,
                    ),
                    ft.Column(spacing=2, expand=True, controls=[
                        ft.Text(title, size=13, weight=ft.FontWeight.W_600,
                                color=Colors.TEXT),
                        ft.Text(meta, size=11, color=Colors.TEXT_MUTED),
                    ]),
                    ft.TextButton(
                        content=ft.Row(spacing=4, tight=True, controls=[
                            ft.Text("View Details", size=12, color=Colors.TEXT,
                                    weight=ft.FontWeight.W_600),
                            ft.Icon(ft.Icons.ARROW_FORWARD, size=12,
                                    color=Colors.TEXT),
                        ]),
                        on_click=lambda _, _t=title, _m=meta, _c=critical:
                            _open_traffic_alert(page, _t, _m, _c),
                    ),
                ],
            ),
        ))
    return panel(
        "Traffic & Congestion Alerts",
        trailing=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=18,
                         color=Colors.DANGER),
        body=ft.Column(spacing=10, controls=items),
    )


def inventory_view(page: ft.Page) -> ft.Control:
    return ft.Column(
        spacing=20,
        controls=[
            _header(page),
            _kpis(),
            ft.ResponsiveRow(
                run_spacing=20,
                controls=[
                    ft.Container(
                        col={"xs": 12, "lg": 8},
                        content=ft.Column(spacing=20, controls=[
                            _floor_map(page),
                            _traffic_alerts(page),
                        ]),
                    ),
                    ft.Container(
                        col={"xs": 12, "lg": 4},
                        content=_zone_breakdown(page),
                    ),
                ],
            ),
        ],
    )
