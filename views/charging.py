"""Charging Management screen — DB-backed."""
from __future__ import annotations

import flet as ft

import db
from theme import Colors
from components.cards import kpi_tile, panel, status_badge, progress_bar
from components.charts import area_chart
from components.dialogs import show_snack, confirm, info_dialog


def _refresh(page: ft.Page) -> None:
    fn = (page.data or {}).get("refresh")
    if callable(fn):
        fn()


def _header(page: ft.Page) -> ft.Control:
    title = ft.Column(spacing=4, controls=[
        ft.Row(spacing=8, controls=[
            ft.Container(
                bgcolor=Colors.PRIMARY_SOFT,
                border_radius=999,
                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                content=ft.Text("Infrastructure", size=11,
                                weight=ft.FontWeight.W_700,
                                color=Colors.PRIMARY),
            ),
            ft.Text("Warehouse A-4", size=12, color=Colors.TEXT_MUTED,
                    weight=ft.FontWeight.W_600),
        ]),
        ft.Text("Charging Management", size=28, weight=ft.FontWeight.BOLD,
                color=Colors.TEXT),
        ft.Text("Real-time dock status and power distribution control.",
                size=13, color=Colors.TEXT_MUTED),
    ])

    def emergency_shutoff(_):
        confirm(page, "Trigger Emergency Shutoff?",
                "All active charging bays will be powered down and marked for "
                "maintenance review.",
                confirm_label="Shut Off", danger=True,
                on_confirm=lambda: (_do_shutoff(page),))

    actions = ft.Row(spacing=10, controls=[
        ft.OutlinedButton(
            content=ft.Row(spacing=6, tight=True, controls=[
                ft.Icon(ft.Icons.HISTORY, size=16, color=Colors.TEXT),
                ft.Text("Usage Logs", size=13,
                        weight=ft.FontWeight.W_600, color=Colors.TEXT),
            ]),
            on_click=lambda _: _open_usage_logs(page),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        ),
        ft.ElevatedButton(
            content=ft.Row(spacing=6, tight=True, controls=[
                ft.Icon(ft.Icons.BOLT, size=16, color="#FFFFFF"),
                ft.Text("Emergency Shutoff", size=13,
                        weight=ft.FontWeight.W_600, color="#FFFFFF"),
            ]),
            bgcolor=Colors.PRIMARY, color="#FFFFFF",
            on_click=emergency_shutoff,
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


def _open_usage_logs(page: ft.Page) -> None:
    bays = db.list_bays()
    rows = [
        ft.Row(controls=[
            ft.Container(width=70, content=ft.Text(b["name"], size=12,
                weight=ft.FontWeight.W_700, color=Colors.TEXT)),
            ft.Container(width=110, content=status_badge(b["status"],
                {"ACTIVE": "active", "AVAILABLE": "available",
                 "MAINTENANCE": "maintenance"}.get(b["status"], "info"))),
            ft.Container(width=80, content=ft.Text(b["robot_id"] or "—",
                size=12, color=Colors.TEXT_MUTED)),
            ft.Container(expand=True, content=ft.Text(
                f"{int((b['charge'] or 0)*100)}% • "
                f"ETC {b['eta_minutes'] or 0}m • "
                f"health {int((b['health'] or 0)*100)}%",
                size=12, color=Colors.TEXT_MUTED)),
        ])
        for b in bays
    ]
    body = ft.Column(spacing=8, controls=[
        ft.Text("Per-bay snapshot", size=12, weight=ft.FontWeight.W_700,
                color=Colors.TEXT_MUTED),
        ft.Divider(color=Colors.BORDER_LIGHT, thickness=1, height=1),
        *rows,
    ])
    info_dialog(page, "Charging Usage Logs", body)


def _open_maintenance_schedule(page: ft.Page) -> None:
    bays = [b for b in db.list_bays() if b["status"] == "MAINTENANCE"]
    if not bays:
        body = ft.Text("No bays currently scheduled for maintenance.",
                       size=13, color=Colors.TEXT_MUTED)
    else:
        rows = [
            ft.Row(controls=[
                ft.Container(width=80,
                    content=ft.Text(b["name"], size=13,
                        weight=ft.FontWeight.W_700, color=Colors.TEXT)),
                ft.Container(expand=True,
                    content=ft.Text("Hardware fault — diagnostic queued",
                        size=12, color=Colors.TEXT_MUTED)),
                ft.Container(width=100,
                    content=ft.Text("Est. 3h window", size=11,
                        color=Colors.WARNING,
                        weight=ft.FontWeight.W_600)),
            ])
            for b in bays
        ]
        body = ft.Column(spacing=10, tight=True, controls=rows)
    info_dialog(page, "Maintenance Schedule", body)


def _do_shutoff(page: ft.Page) -> None:
    for bay in db.list_bays():
        if bay["status"] == "ACTIVE":
            db.update_bay_status(bay["id"], "MAINTENANCE")
    db.insert_alert("critical", "EMERGENCY SHUTOFF",
                    "All active charging bays powered down.",
                    "Charging", "just now")
    show_snack(page, "Charging grid powered down.", kind="error")
    _refresh(page)


def _kpis() -> ft.Control:
    k = db.charging_kpis()
    bays = db.list_bays()
    # Each ACTIVE bay nominal output ~50 kW × charge fraction (toy model)
    energy_kw = round(sum((b["charge"] or 0) * 50
                          for b in bays if b["status"] == "ACTIVE"))
    active_etas = [b["eta_minutes"] for b in bays
                   if b["status"] == "ACTIVE" and b["eta_minutes"]]
    avg_eta = round(sum(active_etas) / len(active_etas)) if active_etas else 0

    items = [
        kpi_tile(ft.Icons.BOLT_OUTLINED, f"{k['active']} / {k['total']}",
                 "ACTIVE CYCLES", None, None,
                 icon_bg=Colors.PRIMARY_SOFT, icon_color=Colors.PRIMARY),
        kpi_tile(ft.Icons.CHECK_CIRCLE_OUTLINE, f"{k['idle']} Units",
                 "IDLE DOCKS", None, None,
                 icon_bg="#F1F5F9", icon_color=Colors.TEXT),
        kpi_tile(ft.Icons.OFFLINE_BOLT_OUTLINED, f"{energy_kw} kW",
                 "ENERGY OUTPUT", None, None,
                 icon_bg=Colors.SUCCESS_SOFT, icon_color=Colors.SUCCESS),
        kpi_tile(ft.Icons.SCHEDULE,
                 f"{avg_eta} min" if avg_eta else "—",
                 "AVG. TURNAROUND", None, None,
                 icon_bg=Colors.WARNING_SOFT, icon_color=Colors.WARNING),
    ]
    return ft.ResponsiveRow(
        run_spacing=14,
        controls=[ft.Container(content=i, col={"xs": 12, "sm": 6, "lg": 3})
                  for i in items],
    )


def _bay_card(page: ft.Page, bay: dict) -> ft.Container:
    name = bay["name"]
    status = bay["status"]
    status_kind = {"ACTIVE": "active", "AVAILABLE": "available",
                   "MAINTENANCE": "maintenance"}.get(status, "info")

    def on_reset(_):
        confirm(page, f"Reset {name}?",
                "Restart the charge cycle for this bay.",
                confirm_label="Reset",
                on_confirm=lambda: (
                    db.reset_bay(bay["id"]),
                    show_snack(page, f"{name} cycle reset.", kind="success"),
                    _refresh(page),
                ))

    def cycle_status(_):
        next_status = {
            "ACTIVE": "MAINTENANCE",
            "MAINTENANCE": "AVAILABLE",
            "AVAILABLE": "ACTIVE",
        }[status]
        confirm(page, f"Change {name} status?",
                f"Move bay from {status} → {next_status}.",
                confirm_label="Change",
                on_confirm=lambda: (
                    db.update_bay_status(bay["id"], next_status),
                    show_snack(page, f"{name} → {next_status}", kind="info"),
                    _refresh(page),
                ))

    if status == "MAINTENANCE":
        body = ft.Column(spacing=10, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(spacing=6, controls=[
                        ft.Icon(ft.Icons.POWER_SETTINGS_NEW, size=14,
                                color=Colors.TEXT_MUTED),
                        ft.Text(name, size=14, weight=ft.FontWeight.BOLD,
                                color=Colors.TEXT),
                    ]),
                    status_badge(status, status_kind),
                ],
            ),
            ft.Text("Hardware fault detected", size=12,
                    color=Colors.TEXT_MUTED),
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=20,
                            color=Colors.DANGER),
                    ft.Text("Offline for Repair", size=12,
                            weight=ft.FontWeight.W_700, color=Colors.DANGER),
                ],
            ),
            ft.OutlinedButton(
                content=ft.Row(spacing=6, tight=True, controls=[
                    ft.Icon(ft.Icons.BUILD, size=14, color=Colors.TEXT),
                    ft.Text("Cycle Status", size=12, color=Colors.TEXT,
                            weight=ft.FontWeight.W_600),
                ]),
                on_click=cycle_status,
                style=ft.ButtonStyle(
                    side=ft.BorderSide(1, Colors.BORDER),
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                ),
            ),
        ])
    elif status == "AVAILABLE":
        body = ft.Column(spacing=10, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(spacing=6, controls=[
                        ft.Icon(ft.Icons.POWER_SETTINGS_NEW, size=14,
                                color=Colors.TEXT_MUTED),
                        ft.Text(name, size=14, weight=ft.FontWeight.BOLD,
                                color=Colors.TEXT),
                    ]),
                    status_badge(status, status_kind),
                ],
            ),
            ft.Text("Ready for connection", size=12, color=Colors.TEXT_MUTED),
            ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
                controls=[
                    ft.Icon(ft.Icons.BOLT_OUTLINED, size=20,
                            color=Colors.TEXT_FAINT),
                    ft.Text("Idle - High Capacity", size=12,
                            weight=ft.FontWeight.W_700,
                            color=Colors.TEXT_MUTED),
                ],
            ),
            ft.OutlinedButton(
                content=ft.Row(spacing=6, tight=True, controls=[
                    ft.Icon(ft.Icons.RESTART_ALT, size=14, color=Colors.TEXT),
                    ft.Text("Reset", size=12, color=Colors.TEXT,
                            weight=ft.FontWeight.W_600),
                ]),
                on_click=cycle_status,
                style=ft.ButtonStyle(
                    side=ft.BorderSide(1, Colors.BORDER),
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                ),
            ),
        ])
    else:  # ACTIVE
        charge_pct = bay["charge"] or 0
        eta = bay["eta_minutes"] or 0
        eta_label = f"{eta // 60}h {eta % 60}m" if eta >= 60 else f"{eta}m"
        health = bay["health"] or 0
        body = ft.Column(spacing=10, controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(spacing=6, controls=[
                        ft.Icon(ft.Icons.POWER_SETTINGS_NEW, size=14,
                                color=Colors.TEXT_MUTED),
                        ft.Text(name, size=14, weight=ft.FontWeight.BOLD,
                                color=Colors.TEXT),
                    ]),
                    status_badge(status, status_kind),
                ],
            ),
            ft.Text("Active Charge Cycle", size=11, color=Colors.TEXT_MUTED),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.END,
                controls=[
                    ft.Column(spacing=2, controls=[
                        ft.Text("Assigned Robot", size=10,
                                weight=ft.FontWeight.W_600,
                                color=Colors.TEXT_MUTED),
                        ft.Text(bay["robot_id"] or "—", size=14,
                                weight=ft.FontWeight.BOLD, color=Colors.PRIMARY),
                    ]),
                    ft.Text(f"{int(charge_pct*100)}%", size=22,
                            weight=ft.FontWeight.BOLD, color=Colors.TEXT),
                ],
            ),
            progress_bar(charge_pct, height=6),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(spacing=4, controls=[
                        ft.Icon(ft.Icons.SCHEDULE, size=12,
                                color=Colors.TEXT_FAINT),
                        ft.Text(f"ETC: {eta_label}", size=11,
                                color=Colors.TEXT_MUTED),
                    ]),
                    ft.Row(spacing=4, controls=[
                        ft.Icon(ft.Icons.MONITOR_HEART_OUTLINED, size=12,
                                color=Colors.TEXT_FAINT),
                        ft.Text(f"Health: {int(health*100)}%", size=11,
                                color=Colors.TEXT_MUTED),
                    ]),
                ],
            ),
            ft.Row(spacing=4, controls=[
                ft.OutlinedButton(
                    expand=True,
                    content=ft.Row(spacing=6, tight=True,
                                   alignment=ft.MainAxisAlignment.CENTER,
                                   controls=[
                                       ft.Icon(ft.Icons.RESTART_ALT, size=14,
                                               color=Colors.TEXT),
                                       ft.Text("Reset", size=12,
                                               weight=ft.FontWeight.W_600,
                                               color=Colors.TEXT),
                                   ]),
                    on_click=on_reset,
                    style=ft.ButtonStyle(
                        side=ft.BorderSide(1, Colors.BORDER),
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    ),
                ),
                ft.IconButton(
                    icon=ft.Icons.MORE_VERT,
                    icon_color=Colors.TEXT_MUTED, icon_size=18,
                    on_click=cycle_status,
                ),
            ]),
        ])
    return ft.Container(
        bgcolor=Colors.SURFACE,
        border=ft.Border.all(1, Colors.BORDER),
        border_radius=12,
        padding=16,
        height=290,
        content=body,
    )


_FILTER_CYCLE = ["ALL", "ACTIVE", "AVAILABLE", "MAINTENANCE"]


def _bay_grid(page: ft.Page) -> ft.Control:
    state = page.data.setdefault("charging_view", {})
    sort_by_pct = state.get("sort_by_pct", False)
    flt = state.get("filter", "ALL")

    bays = db.list_bays()
    if flt != "ALL":
        bays = [b for b in bays if b["status"] == flt]
    if sort_by_pct:
        bays.sort(key=lambda b: -(b["charge"] or 0))

    cards = [
        ft.Container(content=_bay_card(page, b),
                     col={"xs": 12, "sm": 6, "lg": 4})
        for b in bays
    ]
    if not cards:
        cards = [ft.Container(
            col={"xs": 12},
            content=ft.Text(f"No bays match filter: {flt}",
                            size=13, color=Colors.TEXT_MUTED))]

    def toggle_sort(_):
        state["sort_by_pct"] = not sort_by_pct
        show_snack(page,
                   "Sorted by charge %." if state["sort_by_pct"]
                   else "Sort cleared.",
                   kind="info")
        _refresh(page)

    def cycle_filter(_):
        idx = _FILTER_CYCLE.index(flt)
        state["filter"] = _FILTER_CYCLE[(idx + 1) % len(_FILTER_CYCLE)]
        show_snack(page, f"Filter → {state['filter']}", kind="info")
        _refresh(page)

    return panel(
        "Bay Monitoring Grid",
        trailing=ft.Row(spacing=12, controls=[
            ft.Row(spacing=6, controls=[
                ft.Container(width=8, height=8, bgcolor=Colors.SUCCESS,
                             border_radius=999),
                ft.Text("Live View", size=11, weight=ft.FontWeight.W_700,
                        color=Colors.SUCCESS),
            ]),
            ft.TextButton(
                content=ft.Text(
                    "Sort by % ✓" if sort_by_pct else "Sort by %",
                    size=11,
                    color=Colors.PRIMARY if sort_by_pct
                    else Colors.TEXT_MUTED,
                    weight=ft.FontWeight.W_700 if sort_by_pct
                    else ft.FontWeight.W_500,
                ),
                on_click=toggle_sort,
                style=ft.ButtonStyle(padding=ft.Padding.symmetric(
                    horizontal=4, vertical=2)),
            ),
            ft.TextButton(
                content=ft.Text(f"Filter: {flt}", size=11,
                                color=Colors.PRIMARY if flt != "ALL"
                                else Colors.TEXT_MUTED,
                                weight=ft.FontWeight.W_700 if flt != "ALL"
                                else ft.FontWeight.W_500),
                on_click=cycle_filter,
                style=ft.ButtonStyle(padding=ft.Padding.symmetric(
                    horizontal=4, vertical=2)),
            ),
        ]),
        body=ft.ResponsiveRow(run_spacing=14, controls=cards),
    )


def _power_chart(page: ft.Page) -> ft.Control:
    data = [0.45, 0.5, 0.42, 0.55, 0.6, 0.65, 0.7, 0.75]
    chart = area_chart(
        values=data, height=180,
        x_labels=["10:00", "12:00", "14:00", "16:00", "18:00"],
    )
    return panel(
        "Power Distribution Health",
        subtitle="Grid load forecast for Warehouse A infrastructure",
        trailing=ft.Container(
            bgcolor=Colors.BG, border_radius=999,
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            content=ft.Text("Predictive Analysis", size=11,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT_MUTED),
        ),
        body=chart,
    )


def _queue(page: ft.Page) -> ft.Control:
    queue = db.list_queue()
    rows: list[ft.Control] = []
    for q in queue:
        kind = "low" if q["battery"] < 0.20 else "mid"
        bg = Colors.DANGER_SOFT if kind == "low" else Colors.PRIMARY_SOFT
        fg = Colors.DANGER if kind == "low" else Colors.PRIMARY

        def on_click(_, _q=q):
            confirm(page, "Remove from queue?",
                    f"Drop {_q['robot_id']} from the charging queue.",
                    confirm_label="Remove", danger=True,
                    on_confirm=lambda _id=_q["id"]: (
                        db.remove_queue_entry(_id),
                        show_snack(page, f"{_q['robot_id']} removed.",
                                   kind="success"),
                        _refresh(page),
                    ))

        rows.append(ft.Container(
            border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER_LIGHT)),
            padding=ft.Padding.symmetric(vertical=12),
            ink=True, on_click=on_click,
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=32, height=32, bgcolor=bg,
                                 border_radius=8,
                                 alignment=ft.Alignment.CENTER,
                                 content=ft.Icon(ft.Icons.SMART_TOY, size=18,
                                                 color=fg)),
                    ft.Column(spacing=2, expand=True, controls=[
                        ft.Text(q["robot_id"], size=13,
                                weight=ft.FontWeight.W_700, color=Colors.TEXT),
                        ft.Text(f"{q['reason']} • {q['eta']}", size=11,
                                color=Colors.TEXT_MUTED),
                    ]),
                    ft.Column(
                        spacing=0,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        controls=[
                            ft.Text(f"{int(q['battery']*100)}%", size=13,
                                    weight=ft.FontWeight.BOLD, color=fg),
                            ft.Text("BATTERY", size=9,
                                    weight=ft.FontWeight.W_700,
                                    color=Colors.TEXT_FAINT),
                        ],
                    ),
                ],
            ),
        ))

    if not rows:
        rows.append(ft.Text("Queue empty.", size=13, color=Colors.TEXT_MUTED))

    body = ft.Column(spacing=0, controls=[
        ft.Text("Robots awaiting bay availability — click any row to remove.",
                size=12, color=Colors.TEXT_MUTED),
        ft.Container(height=8),
        *rows,
        ft.Container(height=8),
        ft.OutlinedButton(
            content=ft.Text("Optimize Queue Order", size=13,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT),
            on_click=lambda _: (
                db.reorder_queue(),
                show_snack(page,
                           "Queue reordered by battery (lowest first).",
                           kind="success"),
                _refresh(page),
            ),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        ),
        ft.Container(height=8),
        ft.Container(
            bgcolor=Colors.WARNING_SOFT,
            border=ft.Border.all(1, "#FCD34D"),
            border_radius=10,
            padding=12,
            content=ft.Column(spacing=6, controls=[
                ft.Row(spacing=6, controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=14,
                            color=Colors.WARNING),
                    ft.Text("System Maintenance", size=13,
                            weight=ft.FontWeight.BOLD, color=Colors.TEXT),
                ]),
                ft.Text(
                    "Next scheduled infrastructure diagnostic is in 3 hours. "
                    "Ensure all high-priority robots are charged before then.",
                    size=12, color=Colors.TEXT_MUTED,
                ),
                ft.TextButton(
                    "View Maintenance Schedule →",
                    on_click=lambda _: _open_maintenance_schedule(page),
                    style=ft.ButtonStyle(color=Colors.WARNING,
                                         padding=ft.Padding.all(0)),
                ),
            ]),
        ),
    ])
    return panel(
        "Charging Queue",
        trailing=ft.Container(
            bgcolor=Colors.PRIMARY_SOFT, border_radius=999,
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            content=ft.Text(f"{len(queue)} Pending", size=11,
                            weight=ft.FontWeight.W_700, color=Colors.PRIMARY),
        ),
        body=body,
    )


def charging_view(page: ft.Page) -> ft.Control:
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
                            _bay_grid(page),
                            _power_chart(page),
                        ]),
                    ),
                    ft.Container(
                        col={"xs": 12, "lg": 4},
                        content=_queue(page),
                    ),
                ],
            ),
        ],
    )
