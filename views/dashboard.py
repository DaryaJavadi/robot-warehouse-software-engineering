"""Dashboard / Fleet Command screen — DB-backed."""
from __future__ import annotations

import flet as ft

import db
from theme import Colors
from components.cards import kpi_tile, panel, alert_card, status_badge, progress_bar
from components.charts import area_chart
from components.dialogs import show_snack, form_dialog, confirm, info_dialog

# left side:
def _refresh(page: ft.Page) -> None:
    fn = (page.data or {}).get("refresh")
    if callable(fn):
        fn()


def _open_robot(page: ft.Page, robot_id: str) -> None:
    page.data["selected_robot_id"] = robot_id
    show_snack(page, f"Opening {robot_id}.", kind="info")
    page.go("/robots")


def _open_task(page: ft.Page, task_id: str) -> None:
    page.data["selected_task_id"] = task_id
    show_snack(page, f"Opening {task_id}.", kind="info")
    page.go("/tasks")

# DASHBOARD: 
def _header(page: ft.Page) -> ft.Control:
    title = ft.Column(spacing=4, controls=[
        ft.Text("Fleet Command", size=28, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
        ft.Text("Real-time orchestration of Warehouse A assets",
                size=13, color=Colors.TEXT_MUTED),
    ])

    # Task History:
    def open_history(_):
        all_tasks = db.list_tasks() # -> returns a list of all tasks.
        finished = [t for t in all_tasks
                    if t["status"] in ("Completed", "Aborted")]
        finished.sort(key=lambda t: t["id"], reverse=True)
        if not finished:
            body = ft.Text("No completed or aborted tasks yet.",
                           size=13, color=Colors.TEXT_MUTED)
        else:
            rows = []
            for t in finished[:25]:
                rows.append(ft.Row(
                    spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=88,
                            content=ft.Text(t["id"], size=12,
                                            weight=ft.FontWeight.W_600,
                                            color=Colors.PRIMARY)),
                        ft.Container(expand=True,
                            content=ft.Text(t["name"], size=12,
                                            color=Colors.TEXT)),
                        ft.Container(width=90,
                            content=status_badge(
                                t["status"],
                                "active" if t["status"] == "Completed"
                                else "critical")),
                        ft.Container(width=70,
                            content=ft.Text(t["robot_id"] or "—", size=12,
                                            color=Colors.TEXT_MUTED)),
                    ],
                ))
            body = ft.Column(spacing=8, controls=[
                ft.Text(f"{len(finished)} archived task(s) — newest first",
                        size=12, color=Colors.TEXT_MUTED),
                ft.Divider(color=Colors.BORDER_LIGHT, thickness=1, height=1),
                *rows,
            ])
        info_dialog(page, "Task History", body)


    # Assign New Task:
    def open_new_task(_):
        robots = db.list_robots()
        robot_ids = ", ".join(r["id"] for r in robots[:5])

        def submit(values: dict):
            name = values.get("name", "").strip()
            if not name: # Validation:
                show_snack(page, "Task name is required.", kind="warning")
                return
            new_id = db.insert_task(
                name=name,
                kind=values.get("kind", "Pallet Transfer") or "Pallet Transfer",
                priority=values.get("priority", "Normal") or "Normal",
                source=values.get("source", "") or "—",
                destination=values.get("destination", "") or "—",
                robot_id=values.get("robot_id") or None,
                description=values.get("description", "") or "",
            )
            db.insert_alert("info", "TASK CREATED", # inserts an alert into the database.
                            f"{name} queued for dispatch.", new_id, "just now")
            show_snack(page, f"✓ Task {new_id} — '{name}' created successfully!", kind="success")
            _refresh(page)

        form_dialog(page, "Assign New Task",
                    fields=[
                        ("name", "Task name", ""),
                        ("kind", "Kind (Pallet Transfer / Order Picking / ...)",
                         "Pallet Transfer"),
                        ("priority", "Priority (Low / Normal / High / Urgent)",
                         "Normal"),
                        ("source", "Source", "Loading Bay 04"),
                        ("destination", "Destination", "Storage Rack C-12"),
                        ("robot_id", f"Assigned robot (e.g. {robot_ids})", ""),
                        ("description", "Description", ""),
                    ],
                    submit_label="Create Task",
                    on_submit=submit)

    # Logic Part:
    user_role = (page.data.get("user") or {}).get("role", "user")

    # Logic Part:
    action_controls = [
        ft.OutlinedButton(
            content=ft.Row(spacing=6, tight=True, controls=[
                ft.Icon(ft.Icons.HISTORY, size=16, color=Colors.TEXT),
                ft.Text("Task History", size=13, color=Colors.TEXT,
                        weight=ft.FontWeight.W_600),
            ]),
            on_click=open_history,
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        )
    ]

    # Only managers can assign new tasks:
    if user_role == "manager":
        action_controls.append(
            ft.FilledButton(
                content=ft.Row(spacing=6, tight=True, controls=[
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=16, color="#FFFFFF"),
                    ft.Text("Assign New Task", size=13, color="#FFFFFF",
                            weight=ft.FontWeight.W_600),
                ]),
                bgcolor=Colors.PRIMARY,
                on_click=open_new_task,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                ),
            )
        )

    actions = ft.Row(
        spacing=10,
        controls=action_controls,
    )
    return ft.ResponsiveRow(
        run_spacing=14,
        controls=[
            ft.Container(content=title, col={"xs": 12, "md": 7}),
            ft.Container(
                content=ft.Row(controls=[actions],
                               alignment=ft.MainAxisAlignment.END),
                col={"xs": 12, "md": 5},
            ),
        ],
    )


def _kpis() -> ft.Control:
    k = db.kpis()
    items = [
        kpi_tile(ft.Icons.SMART_TOY_OUTLINED, str(k["active"]), "Active Robots",
                 "+4.5%", Colors.SUCCESS),
        kpi_tile(ft.Icons.CHECK_CIRCLE_OUTLINE, f"{k['completed']:,}",
                 "Completed Tasks", "+12%", Colors.SUCCESS,
                 icon_bg=Colors.SUCCESS_SOFT, icon_color=Colors.SUCCESS),
        kpi_tile(ft.Icons.BOLT_OUTLINED, f"{k['avg_battery']}%", "Avg. Battery",
                 "-2.1%", Colors.DANGER,
                 icon_bg=Colors.WARNING_SOFT, icon_color=Colors.WARNING),
        kpi_tile(ft.Icons.TRENDING_UP, "99.8%", "Uptime Rate",
                 "Optimal", Colors.SUCCESS,
                 icon_bg=Colors.SUCCESS_SOFT, icon_color=Colors.SUCCESS),
    ]
    return ft.ResponsiveRow(
        run_spacing=14,
        controls=[
            ft.Container(content=item, col={"xs": 12, "sm": 6, "lg": 3})
            for item in items
        ],
    )


def _robot_table(page: ft.Page) -> ft.Control:
    # for example: testing robot RBT-904:
    robots = [r for r in db.list_robots() if r["id"] != "RBT-904"][:5]

    header = ft.Row(
        controls=[
            ft.Container(width=80, content=ft.Text("Robot ID", size=11,
                weight=ft.FontWeight.W_600, color=Colors.TEXT_MUTED)),
            ft.Container(width=110, content=ft.Text("Status", size=11,
                weight=ft.FontWeight.W_600, color=Colors.TEXT_MUTED)),
            ft.Container(expand=True, content=ft.Text("Zone", size=11,
                weight=ft.FontWeight.W_600, color=Colors.TEXT_MUTED)),
            ft.Container(width=160, content=ft.Text("Battery", size=11,
                weight=ft.FontWeight.W_600, color=Colors.TEXT_MUTED)),
            ft.Container(width=110, content=ft.Text("Last Maintenance", size=11,
                weight=ft.FontWeight.W_600, color=Colors.TEXT_MUTED)),
        ],
    )

    body_rows: list[ft.Control] = []
    for r in robots:
        rid = r["id"]
        status = r["status"]
        kind = status.lower().replace(" ", "_")
        body_rows.append(ft.Container(
            padding=ft.Padding.symmetric(vertical=12),
            border=ft.Border.only(top=ft.BorderSide(1, Colors.BORDER_LIGHT)),
            ink=True,
            on_click=lambda _, _rid=rid: _open_robot(page, _rid),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=80,
                        content=ft.Text(rid, size=13, weight=ft.FontWeight.W_600,
                                        color=Colors.PRIMARY)),
                    ft.Container(width=110, content=status_badge(status, kind)),
                    ft.Container(expand=True,
                        content=ft.Text(r["zone"], size=13, color=Colors.TEXT)),
                    ft.Container(
                        width=160,
                        content=ft.Row(spacing=8, controls=[
                            ft.Container(expand=True,
                                content=progress_bar(r["battery"])),
                            ft.Text(f"{int(r['battery']*100)}%", size=12,
                                    color=Colors.TEXT_MUTED, width=42),
                        ]),
                    ),
                    ft.Container(width=110,
                        content=ft.Text(r["last_maintenance"], size=12,
                                        color=Colors.TEXT_MUTED)),
                ],
            ),
        ))

    body = ft.Column(spacing=0, controls=[
        ft.Container(padding=ft.Padding.only(bottom=8), content=header),
        *body_rows,
    ])

    # Three dots: -> BULK Menu:
    def recall_idle():
        n = db.recall_idle_robots()
        if n:
            db.insert_alert("info", "BULK RECALL",
                            f"{n} idle robot(s) recalled to Home Dock.",
                            "Bulk", "just now")
            show_snack(page, f"{n} idle robot(s) recalled.", kind="success")
        else:
            show_snack(page, "No idle robots to recall.", kind="info")
        _refresh(page)

    def stop_all_working():
        confirm(page, "Stop all working robots?",
                "Marks every robot currently Working as Maintenance and "
                "raises a critical alert per robot.",
                confirm_label="Stop All", danger=True,
                on_confirm=lambda: (
                    _stop_all_working(page),
                ))

    user_role = (page.data.get("user") or {}).get("role", "user")
    
    menu_items = []
    if user_role == "manager":
        menu_items.extend([
            ft.PopupMenuItem(content="Recall all idle to dock",
                             on_click=lambda _: recall_idle()),
            ft.PopupMenuItem(content="Stop all working robots",
                             on_click=lambda _: stop_all_working()),
        ])
    
    menu_items.append(
        ft.PopupMenuItem(content="Open Robot Detail",
                         on_click=lambda _: page.go("/robots"))
    )

    bulk_menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT, icon_color=Colors.TEXT_MUTED,
        items=menu_items,
    )

    return panel(
        "Robot Status Table",
        subtitle="Real-time telemetry for all fleet assets",
        trailing=bulk_menu,
        body=body,
    )


def _stop_all_working(page: ft.Page) -> None:
    halted = []
    for r in db.list_robots():
        if r["status"] == "Working":
            db.update_robot_status(r["id"], "Maintenance")
            db.insert_alert("critical", "BULK STOP",
                            f"{r['id']} halted via bulk action.",
                            r["id"], "just now")
            halted.append(r["id"])
    show_snack(page,
               f"Stopped {len(halted)} robot(s)." if halted
               else "No working robots to stop.",
               kind="error" if halted else "info")
    _refresh(page)


def _open_all_alerts(page: ft.Page) -> None:
    alerts = db.list_alerts(limit=99)
    if not alerts:
        info_dialog(page, "All Alerts",
                    ft.Text("No active alerts.", size=13,
                            color=Colors.TEXT_MUTED))
        return
    rows = []
    for a in alerts:
        rows.append(ft.Container(
            border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER_LIGHT)),
            padding=ft.Padding.symmetric(vertical=8),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=70,
                        content=status_badge(a["kind"].upper(),
                                             "critical" if a["kind"] == "critical"
                                             else "warning")),
                    ft.Column(spacing=2, expand=True, controls=[
                        ft.Text(a["title"], size=13,
                                weight=ft.FontWeight.W_600,
                                color=Colors.TEXT),
                        ft.Text(f"{a['body']}  •  {a['meta']}  •  "
                                f"{a['created_at']}",
                                size=11, color=Colors.TEXT_MUTED),
                    ]),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_color=Colors.TEXT_MUTED, icon_size=16,
                        tooltip="Dismiss",
                        on_click=lambda _, _id=a["id"]: (
                            show_snack(page, "Access Denied: Administrative privileges required.", kind="error")
                            if (page.data.get("user") or {}).get("role") != "manager" else
                            (db.dismiss_alert(_id),
                             show_snack(page, "Alert dismissed.", kind="success"),
                             _refresh(page))
                        ),
                    ),
                ],
            ),
        ))
    info_dialog(page, f"All Alerts ({len(alerts)})",
                ft.Column(spacing=0, tight=True, controls=rows))


def _critical_alerts(page: ft.Page) -> ft.Control:
    alerts = db.list_alerts()
    new_count = sum(1 for a in alerts if a["kind"] == "critical")

    def make_row(alert: dict) -> ft.Control:
        card = alert_card(alert["kind"], alert["title"], alert["body"],
                          alert["meta"], alert["created_at"])
        # Wrap so click→dismiss
        return ft.Container(
            content=card,
            ink=True,
            on_click=lambda _, _a=alert: confirm(
                page, "Dismiss alert?", f"{_a['title']} — {_a['body']}",
                confirm_label="Dismiss", danger=True,
                on_confirm=lambda _id=_a["id"]: (
                    show_snack(page, "Access Denied: Administrative privileges required.", kind="error")
                    if (page.data.get("user") or {}).get("role") != "manager" else
                    (db.dismiss_alert(_id),
                     show_snack(page, "Alert dismissed.", kind="success"),
                     _refresh(page))
                ),
            ),
        )

    body = ft.Column(spacing=10, controls=[
        ft.Text("Action items requiring immediate attention",
                size=12, color=Colors.TEXT_MUTED),
        *(make_row(a) for a in alerts[:4]),
        ft.TextButton(
            "View All Alerts",
            style=ft.ButtonStyle(color=Colors.PRIMARY),
            on_click=lambda _: _open_all_alerts(page),
        ),
    ])
    return panel(
        "Critical Alerts",
        trailing=ft.Container(
            bgcolor=Colors.DANGER_SOFT, border_radius=999,
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            content=ft.Text(f"{new_count} New", size=11,
                            weight=ft.FontWeight.W_700, color=Colors.DANGER),
        ),
        body=body,
    )


def _active_tasks(page: ft.Page) -> ft.Control:
    tasks = [t for t in db.list_tasks() if t["status"] == "In Progress"][:3]
    cards = []
    for t in tasks:
        priority = t["priority"]
        kind = "high" if priority in ("High", "Urgent") else "normal"
        cards.append(ft.Container(
            bgcolor=Colors.BG,
            border=ft.Border.all(1, Colors.BORDER_LIGHT),
            border_radius=10,
            padding=14,
            ink=True,
            on_click=lambda _, _t=t: _open_task(page, _t["id"]),
            content=ft.Column(spacing=10, controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(f"#{t['id']}", size=11, color=Colors.TEXT_MUTED,
                                weight=ft.FontWeight.W_600),
                        status_badge(priority, kind),
                    ],
                ),
                ft.Text(t["name"], size=15, weight=ft.FontWeight.BOLD,
                        color=Colors.TEXT),
                ft.Row(spacing=6, controls=[
                    ft.Icon(ft.Icons.PLACE_OUTLINED, size=14, color=Colors.PRIMARY),
                    ft.Text(t["source"], size=12, color=Colors.TEXT_MUTED),
                ]),
                ft.Row(spacing=6, controls=[
                    ft.Icon(ft.Icons.PLACE_OUTLINED, size=14, color=Colors.PRIMARY),
                    ft.Text(t["destination"], size=12, color=Colors.TEXT_MUTED),
                ]),
                ft.Divider(color=Colors.BORDER_LIGHT, thickness=1, height=1),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(spacing=4, controls=[
                            ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=14,
                                    color=Colors.TEXT_FAINT),
                            ft.Text(t["robot_id"] or "Unassigned", size=12,
                                    weight=ft.FontWeight.W_600,
                                    color=Colors.TEXT),
                        ]),
                        ft.Text(t["status"], size=12, color=Colors.PRIMARY,
                                weight=ft.FontWeight.W_600),
                    ],
                ),
            ]),
        ))
    if not cards:
        cards.append(ft.Text("No active tasks.", size=13, color=Colors.TEXT_MUTED))

    return panel(
        "Active Tasks",
        trailing=ft.TextButton(
            "Manage",
            on_click=lambda _: page.go("/tasks"),
            style=ft.ButtonStyle(color=Colors.PRIMARY),
        ),
        body=ft.Column(spacing=12, controls=cards),
    )


def _zone_tile(zone: dict) -> ft.Container:
    pct = zone["used"] / zone["capacity"] if zone["capacity"] else 0
    critical = zone["status"] == "CRITICAL"
    border_c = Colors.DANGER if critical else Colors.BORDER_LIGHT
    bg = Colors.DANGER_SOFT if critical else Colors.SURFACE
    return ft.Container(
        bgcolor=bg,
        border=ft.Border.all(1, border_c),
        border_radius=10,
        padding=12,
        content=ft.Column(spacing=8, controls=[
            ft.Row(controls=[
                ft.Text(zone["name"].upper(), size=10,
                        weight=ft.FontWeight.W_700, color=Colors.TEXT_MUTED),
                *([ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=12,
                          color=Colors.DANGER)] if critical else []),
            ]),
            ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.END, spacing=4,
                controls=[
                    ft.Text(str(zone["used"]), size=20,
                            weight=ft.FontWeight.BOLD, color=Colors.TEXT),
                    ft.Text(f"/ {zone['capacity']} units", size=11,
                            color=Colors.TEXT_MUTED),
                ],
            ),
            progress_bar(pct,
                         color=Colors.DANGER if critical else Colors.PRIMARY),
        ]),
    )


def _inventory_zones(page: ft.Page) -> ft.Control:
    zones = db.list_zones(categories=("COLD", "BULK", "PICKING", "HAZ",
                                      "SORTING", "DISPATCH"))[:6]
    grid = ft.ResponsiveRow(
        run_spacing=10,
        controls=[ft.Container(content=_zone_tile(z), col={"xs": 12, "sm": 6})
                  for z in zones],
    )
    return panel(
        "Inventory Zones",
        trailing=ft.Row(spacing=4, controls=[
            ft.Container(width=8, height=8, bgcolor=Colors.DANGER, border_radius=999),
            ft.Text("HEAVY LOAD", size=10, weight=ft.FontWeight.W_700,
                    color=Colors.DANGER),
        ]),
        body=grid,
    )


def _battery_trends(page: ft.Page) -> ft.Control:
    data = [0.55, 0.62, 0.5, 0.7, 0.55, 0.6, 0.72, 0.65, 0.5, 0.58]
    data2 = [0.4, 0.45, 0.38, 0.55, 0.48, 0.5, 0.62, 0.55, 0.42, 0.48]
    chart = area_chart(
        values=data,
        second_values=data2,
        height=180,
        x_labels=["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"],
        legend=[("Average Fleet Charge", Colors.CHART_BLUE),
                ("Peak Demand Charge", "#93C5FD")],
    )
    low = sorted([r for r in db.list_robots()
                  if r["status"] != "Maintenance" and r["battery"] < 0.30],
                 key=lambda r: r["battery"])
    if low:
        ids = ", ".join(r["id"] for r in low[:5])
        alert_body = (f"{len(low)} unit(s) below 30% charge "
                      f"({ids}) — recommend recall before next mission window.")
        alert_kind = "warning"
    else:
        alert_body = ("All robots above 30% charge. Predictive window clear "
                      "for the next 45 minutes.")
        alert_kind = "info"

    alert = ft.Container(
        bgcolor=Colors.WARNING_SOFT if alert_kind == "warning"
        else Colors.PRIMARY_SOFT,
        border=ft.Border.all(1, "#FCD34D" if alert_kind == "warning"
                             else Colors.PRIMARY_BORDER),
        border_radius=10,
        padding=14,
        content=ft.Column(spacing=8, controls=[
            ft.Row(spacing=6, controls=[
                ft.Icon(ft.Icons.BATTERY_ALERT, size=14,
                        color=Colors.WARNING if alert_kind == "warning"
                        else Colors.PRIMARY),
                ft.Text("Predictive Power Alert", size=13,
                        weight=ft.FontWeight.W_700,
                        color=Colors.WARNING if alert_kind == "warning"
                        else Colors.PRIMARY),
            ]),
            ft.Text(alert_body, size=12, color=Colors.TEXT_MUTED),
            ft.TextButton(
                "Open Charging Optimization →",
                style=ft.ButtonStyle(color=Colors.PRIMARY,
                                     padding=ft.Padding.all(0)),
                on_click=lambda _: page.go("/charging"),
            ),
        ]),
    )
    return panel(
        "Battery Trends",
        trailing=ft.OutlinedButton(
            content=ft.Text("View Charging Hub", size=12,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT),
            on_click=lambda _: page.go("/charging"),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            ),
        ),
        body=ft.Column(spacing=14, controls=[chart, alert]),
    )


def dashboard_view(page: ft.Page) -> ft.Control:
    return ft.Column(
        spacing=20,
        controls=[
            _header(page),
            _kpis(),
            ft.ResponsiveRow(
                run_spacing=20,
                controls=[
                    ft.Container(content=_robot_table(page),
                                 col={"xs": 12, "lg": 8}),
                    ft.Container(content=_critical_alerts(page),
                                 col={"xs": 12, "lg": 4}),
                ],
            ),
            ft.ResponsiveRow(
                run_spacing=20,
                controls=[
                    ft.Container(content=_active_tasks(page),
                                 col={"xs": 12, "md": 6, "lg": 4}),
                    ft.Container(content=_inventory_zones(page),
                                 col={"xs": 12, "md": 6, "lg": 4}),
                    ft.Container(content=_battery_trends(page),
                                 col={"xs": 12, "lg": 4}),
                ],
            ),
        ],
    )
