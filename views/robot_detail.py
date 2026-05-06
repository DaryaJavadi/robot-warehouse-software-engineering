"""Robot detail screen — DB-backed, defaults to RBT-904."""
from __future__ import annotations

import flet as ft

import db
from theme import Colors
from components.cards import panel, status_badge, progress_bar
from components.charts import area_chart
from components.dialogs import show_snack, confirm, info_dialog


DEFAULT_ROBOT_ID = "RBT-904"


def _refresh(page: ft.Page) -> None:
    fn = (page.data or {}).get("refresh")
    if callable(fn):
        fn()


def _header(page: ft.Page, robot: dict) -> ft.Control:
    all_robots = db.list_robots()

    def switch_to(rid: str):
        page.data["selected_robot_id"] = rid
        _refresh(page)

    selector = ft.PopupMenuButton(
        icon=ft.Icons.SWAP_HORIZ, icon_color=Colors.TEXT_MUTED,
        tooltip="Switch robot",
        items=[
            ft.PopupMenuItem(content=f"{r['id']} — {r['model']} ({r['status']})",
                             on_click=lambda _, _rid=r["id"]: switch_to(_rid))
            for r in all_robots
        ],
    )

    title = ft.Column(spacing=4, controls=[
        ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Text(robot["id"], size=28, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
            status_badge(robot["status"], robot["status"].lower()),
            selector,
        ]),
        ft.Text(f"Model: {robot['model']} • Serial: {robot['serial']}",
                size=13, color=Colors.TEXT_MUTED),
    ])

    def return_to_base(_):
        confirm(page, "Return to base?",
                f"Recall {robot['id']} to its home dock.",
                confirm_label="Return",
                on_confirm=lambda: (
                    db.update_robot_status(robot["id"], "Ready", zone="Home Dock"),
                    show_snack(page, f"{robot['id']} returning to base.",
                               kind="success"),
                    _refresh(page),
                ))

    def identify(_):
        show_snack(page, f"{robot['id']} flashing strobe + chirping for 5s.",
                   kind="info")

    def emergency_stop(_):
        confirm(page, "Trigger Emergency Stop?",
                f"This will halt {robot['id']} immediately and mark it for "
                "maintenance review.",
                confirm_label="Stop", danger=True,
                on_confirm=lambda: (
                    db.update_robot_status(robot["id"], "Maintenance"),
                    db.insert_alert("critical", "EMERGENCY STOP",
                                    f"{robot['id']} halted by operator.",
                                    robot["id"], "just now"),
                    show_snack(page, f"{robot['id']} stopped.", kind="error"),
                    _refresh(page),
                ))

    user_role = (page.data.get("user") or {}).get("role", "user")
    
    action_controls = [
        ft.OutlinedButton(
            content=ft.Row(spacing=6, tight=True, controls=[
                ft.Icon(ft.Icons.LIGHTBULB_OUTLINE, size=16, color=Colors.TEXT),
                ft.Text("Identify", size=13,
                        weight=ft.FontWeight.W_600, color=Colors.TEXT),
            ]),
            on_click=identify,
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        )
    ]

    if user_role == "manager":
        action_controls.insert(0, 
            ft.OutlinedButton(
                content=ft.Row(spacing=6, tight=True, controls=[
                    ft.Icon(ft.Icons.RESTART_ALT, size=16, color=Colors.TEXT),
                    ft.Text("Return to Base", size=13,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT),
                ]),
                on_click=return_to_base,
                style=ft.ButtonStyle(
                    side=ft.BorderSide(1, Colors.BORDER),
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                ),
            )
        )
        action_controls.append(
            ft.FilledButton(
                content=ft.Row(spacing=6, tight=True, controls=[
                    ft.Icon(ft.Icons.STOP_CIRCLE_OUTLINED, size=16, color="#FFFFFF"),
                    ft.Text("Emergency Stop", size=13,
                            weight=ft.FontWeight.W_600, color="#FFFFFF"),
                ]),
                bgcolor=Colors.DANGER,
                on_click=emergency_stop,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                ),
            )
        )

    actions = ft.Row(spacing=10, controls=action_controls)
    return ft.ResponsiveRow(
        run_spacing=14,
        controls=[
            ft.Container(content=title, col={"xs": 12, "lg": 7}),
            ft.Container(
                content=ft.Row(controls=[actions],
                               alignment=ft.MainAxisAlignment.END,
                               wrap=True),
                col={"xs": 12, "lg": 5},
            ),
        ],
    )


def _stat_tile(icon, label: str, value: str,
               icon_bg: str, icon_color: str) -> ft.Container:
    return ft.Container(
        bgcolor=Colors.SURFACE,
        border=ft.Border.all(1, Colors.BORDER),
        border_radius=12,
        padding=18,
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=44, height=44, bgcolor=icon_bg, border_radius=10,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=icon_color, size=22),
                ),
                ft.Column(spacing=2, controls=[
                    ft.Text(label, size=12, color=Colors.TEXT_MUTED),
                    ft.Text(value, size=18, weight=ft.FontWeight.BOLD,
                            color=Colors.TEXT),
                ]),
            ],
        ),
    )


def _stats(robot: dict) -> ft.Control:
    items = [
        _stat_tile(ft.Icons.BOLT, "Battery Status",
                   f"{int(robot['battery']*100)}%",
                   Colors.PRIMARY_SOFT, Colors.PRIMARY),
        _stat_tile(ft.Icons.THERMOSTAT, "Core Temperature",
                   f"{int(robot['temperature'])}°C",
                   "#F1F5F9", Colors.TEXT),
        _stat_tile(ft.Icons.WIFI, "Signal Strength", robot["signal"],
                   "#F1F5F9", Colors.TEXT),
        _stat_tile(ft.Icons.PLACE, "Current Zone", robot["zone"],
                   Colors.DANGER_SOFT, Colors.DANGER),
    ]
    return ft.ResponsiveRow(
        run_spacing=14,
        controls=[ft.Container(content=i, col={"xs": 12, "sm": 6, "lg": 3})
                  for i in items],
    )


def _telemetry() -> ft.Control:
    data = [0.85, 0.82, 0.78, 0.75, 0.7, 0.68, 0.65, 0.6, 0.55, 0.52]
    chart = area_chart(
        values=data, height=210,
        x_labels=["09:15", "09:30", "09:45", "10:00"],
        legend=[("Battery Level (%)", Colors.CHART_BLUE)],
    )
    return panel(
        "Robot Telemetry",
        subtitle="Real-time battery discharge and motor temperature history (Last 2 hours)",
        body=chart,
    )


def _current_mission(page: ft.Page, robot: dict) -> ft.Control:
    # Find any task currently assigned to this robot
    tasks = [t for t in db.list_tasks() if t["robot_id"] == robot["id"]]
    task = tasks[0] if tasks else None

    if not task:
        return panel(
            "Current Mission",
            body=ft.Column(spacing=10, controls=[
                ft.Text("No active mission.", size=13, color=Colors.TEXT_MUTED),
                ft.OutlinedButton(
                    content=ft.Text("Browse Tasks", color=Colors.TEXT,
                                    weight=ft.FontWeight.W_600),
                    on_click=lambda _: page.go("/tasks"),
                    style=ft.ButtonStyle(
                        side=ft.BorderSide(1, Colors.BORDER),
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                    ),
                ),
            ]),
        )

    body = ft.Column(spacing=14, controls=[
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(spacing=2, controls=[
                    ft.Text("Task ID", size=11, color=Colors.TEXT_MUTED,
                            weight=ft.FontWeight.W_600),
                    ft.Text(task["id"], size=18, weight=ft.FontWeight.BOLD,
                            color=Colors.PRIMARY),
                ]),
                status_badge(f"{task['priority']} Priority", "warning"),
            ],
        ),
        ft.Row(controls=[
            ft.Text("Mission Progress", size=12, color=Colors.TEXT_MUTED, expand=True),
            ft.Text(f"{int(task['progress']*100)}%", size=12,
                    weight=ft.FontWeight.W_600, color=Colors.TEXT),
        ]),
        progress_bar(task["progress"]),
        ft.Container(height=4),
        ft.Row(spacing=12, controls=[
            ft.Container(
                width=32, height=32, bgcolor=Colors.PRIMARY_SOFT,
                border_radius=999, alignment=ft.Alignment.CENTER,
                content=ft.Text("A", size=12, weight=ft.FontWeight.BOLD,
                                color=Colors.PRIMARY),
            ),
            ft.Column(spacing=0, controls=[
                ft.Text("SOURCE", size=10, weight=ft.FontWeight.W_700,
                        color=Colors.TEXT_MUTED),
                ft.Text(task["source"], size=14, weight=ft.FontWeight.W_600,
                        color=Colors.TEXT),
            ]),
        ]),
        ft.Container(margin=ft.Margin.only(left=15),
                     content=ft.Text("⋮", size=16, color=Colors.TEXT_FAINT)),
        ft.Row(spacing=12, controls=[
            ft.Container(
                width=32, height=32, bgcolor=Colors.PRIMARY,
                border_radius=999, alignment=ft.Alignment.CENTER,
                content=ft.Text("B", size=12, weight=ft.FontWeight.BOLD,
                                color="#FFFFFF"),
            ),
            ft.Column(spacing=0, controls=[
                ft.Text("DESTINATION", size=10, weight=ft.FontWeight.W_700,
                        color=Colors.TEXT_MUTED),
                ft.Text(task["destination"], size=14,
                        weight=ft.FontWeight.W_600, color=Colors.TEXT),
            ]),
        ]),
        ft.OutlinedButton(
            content=ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=6, controls=[
                ft.Text("View Full Task Details", size=13,
                        weight=ft.FontWeight.W_600, color=Colors.TEXT),
                ft.Icon(ft.Icons.ARROW_FORWARD, size=14, color=Colors.TEXT),
            ]),
            on_click=lambda _: page.go("/tasks"),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        ),
    ])
    return panel(
        "Current Mission",
        body=body,
        trailing=ft.Icon(ft.Icons.SCHEDULE, size=18, color=Colors.PRIMARY),
    )


def _spatial_grid(page: ft.Page, robot: dict) -> ft.Control:
    rows: list[ft.Control] = []
    target = (3, 2)
    for r in range(6):
        cells = []
        for c in range(6):
            label = f"{chr(65 + r)}{c + 1}"
            highlight = c in (1, 3, 5)
            bg = "#E2E8F0" if highlight else Colors.BG
            border_c = Colors.BORDER_LIGHT
            content: ft.Control = ft.Text(label, size=10, color=Colors.TEXT_FAINT)
            if (r, c) == target:
                content = ft.Container(
                    width=28, height=28,
                    bgcolor=Colors.PRIMARY,
                    border_radius=999,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.PLACE, color="#FFFFFF", size=18),
                )
                bg = Colors.SURFACE
            cells.append(ft.Container(
                expand=True, height=44, bgcolor=bg,
                alignment=ft.Alignment.CENTER,
                border=ft.Border.all(1, border_c),
                content=content,
            ))
        rows.append(ft.Row(spacing=4, controls=cells))

    grid = ft.Column(spacing=4, controls=rows)
    body = ft.Column(spacing=12, controls=[
        ft.Container(bgcolor=Colors.BG, border_radius=10, padding=12, content=grid),
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(spacing=4, controls=[
                    ft.Text("Zone B-4 Utilization:", size=12, color=Colors.TEXT_MUTED),
                    ft.Text("78%", size=12, weight=ft.FontWeight.W_600,
                            color=Colors.PRIMARY),
                ]),
                ft.TextButton(
                    "Manage Zone",
                    on_click=lambda _: page.go("/inventory"),
                    style=ft.ButtonStyle(color=Colors.PRIMARY,
                                         padding=ft.Padding.all(0)),
                ),
            ],
        ),
    ])
    return panel(
        "Spatial Location",
        subtitle="Precise position in Sector B - Aisle 12",
        trailing=ft.Icon(ft.Icons.PLACE, size=18, color=Colors.DANGER),
        body=body,
    )


def _open_full_history(page: ft.Page, robot: dict,
                       items: list[dict]) -> None:
    if not items:
        body = ft.Text("No log entries.", size=13, color=Colors.TEXT_MUTED)
    else:
        rows = []
        for it in items:
            kind = it["kind"]
            color = (Colors.DANGER if kind == "Error"
                     else Colors.PRIMARY if kind == "Maintenance"
                     else Colors.TEXT_MUTED)
            rows.append(ft.Container(
                border=ft.Border.only(
                    bottom=ft.BorderSide(1, Colors.BORDER_LIGHT)),
                padding=ft.Padding.symmetric(vertical=8),
                content=ft.Column(spacing=2, controls=[
                    ft.Row(controls=[
                        ft.Text(it["date"], size=11,
                                weight=ft.FontWeight.W_700,
                                color=Colors.TEXT_MUTED, expand=True),
                        ft.Text(kind, size=11, weight=ft.FontWeight.W_700,
                                color=color),
                    ]),
                    ft.Text(it["body"], size=12, color=Colors.TEXT),
                ]),
            ))
        body = ft.Column(spacing=0, tight=True, controls=rows)
    info_dialog(page, f"{robot['id']} — Operational Log ({len(items)})",
                body)


def _operational_history(page: ft.Page, robot: dict) -> ft.Control:
    items = db.list_op_history(robot["id"])
    rows: list[ft.Control] = []
    for it in items:
        kind = it["kind"]
        is_error = kind == "Error"
        rows.append(ft.Row(
            spacing=10, vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    width=20, height=20, margin=ft.Margin.only(top=2),
                    bgcolor=Colors.BG, border_radius=999,
                    border=ft.Border.all(1, Colors.BORDER),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(
                        ft.Icons.WARNING_AMBER if is_error else ft.Icons.CHECK,
                        size=12,
                        color=Colors.DANGER if is_error else Colors.TEXT_MUTED,
                    ),
                ),
                ft.Column(spacing=2, expand=True, controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(it["date"], size=11,
                                    weight=ft.FontWeight.W_700,
                                    color=Colors.TEXT_MUTED),
                            status_badge(kind,
                                         "critical" if is_error
                                         else "maintenance" if kind == "Maintenance"
                                         else "warning"),
                        ],
                    ),
                    ft.Text(it["body"], size=13, color=Colors.TEXT),
                ]),
            ],
        ))
    if not rows:
        rows.append(ft.Text("No history entries.", size=13,
                            color=Colors.TEXT_MUTED))

    body = ft.Column(spacing=14, controls=[
        *rows,
        ft.OutlinedButton(
            content=ft.Text("View All Logs", size=13,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT),
            on_click=lambda _: _open_full_history(page, robot, items),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        ),
    ])
    return panel(
        "Operational History",
        trailing=ft.Icon(ft.Icons.HISTORY, size=18, color=Colors.PRIMARY),
        body=body,
    )


def robot_detail_view(page: ft.Page) -> ft.Control:
    rid = (page.data or {}).get("selected_robot_id") or DEFAULT_ROBOT_ID
    robot = db.get_robot(rid)
    if not robot:
        page.data["selected_robot_id"] = DEFAULT_ROBOT_ID
        robot = db.get_robot(DEFAULT_ROBOT_ID)
    if not robot:
        return ft.Text("Robot not found.", size=16, color=Colors.DANGER)
    return ft.Column(
        spacing=20,
        controls=[
            _header(page, robot),
            _stats(robot),
            ft.ResponsiveRow(
                run_spacing=20,
                controls=[
                    ft.Container(
                        col={"xs": 12, "lg": 8},
                        content=ft.Column(spacing=20, controls=[
                            _telemetry(),
                            _spatial_grid(page, robot),
                        ]),
                    ),
                    ft.Container(
                        col={"xs": 12, "lg": 4},
                        content=ft.Column(spacing=20, controls=[
                            _current_mission(page, robot),
                            _operational_history(page, robot),
                        ]),
                    ),
                ],
            ),
        ],
    )
