"""Task detail screen — DB-backed, defaults to TSK-4421."""
from __future__ import annotations

from datetime import datetime

import flet as ft

import db
from theme import Colors
from components.cards import panel, status_badge, progress_bar
from components.dialogs import show_snack, confirm, form_dialog, info_dialog


DEFAULT_TASK_ID = "TSK-4421"


def _refresh(page: ft.Page) -> None:
    fn = (page.data or {}).get("refresh")
    if callable(fn):
        fn()


def _log(task_id: str, msg: str) -> None:
    db.append_mission_log(task_id, datetime.now().strftime("%H:%M:%S"), msg)


def _header(page: ft.Page, task: dict) -> ft.Control:
    all_tasks = db.list_tasks()

    def switch_to(tid: str):
        page.data["selected_task_id"] = tid
        _refresh(page)

    selector = ft.PopupMenuButton(
        icon=ft.Icons.SWAP_HORIZ, icon_color=Colors.TEXT_MUTED,
        tooltip="Switch task",
        items=[
            ft.PopupMenuItem(content=f"{t['id']} — {t['name']} ({t['status']})",
                             on_click=lambda _, _tid=t["id"]: switch_to(_tid))
            for t in all_tasks
        ],
    )

    title = ft.Column(spacing=4, controls=[
        ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
            ft.Text(task["id"], size=28, weight=ft.FontWeight.BOLD,
                    color=Colors.TEXT),
            status_badge(task["status"],
                         "in_progress" if task["status"] == "In Progress"
                         else "warning"),
            status_badge(task["kind"], "available"),
            selector,
        ]),
        ft.Text(task["description"] or "Mission detail.",
                size=13, color=Colors.TEXT_MUTED),
    ])

    def reset_path(_):
        confirm(page, "Reset path?",
                f"Recompute the navigation plan for {task['id']}.",
                confirm_label="Reset",
                on_confirm=lambda: (
                    _log(task["id"], "Path reset by operator."),
                    show_snack(page, "Path recomputed.", kind="success"),
                    _refresh(page),
                ))

    def force_complete(_):
        confirm(page, "Force-complete task?",
                f"Mark {task['id']} as Completed regardless of progress.",
                confirm_label="Complete",
                on_confirm=lambda: (
                    db.update_task_status(task["id"], "Completed"),
                    _log(task["id"], "Task force-completed by operator."),
                    show_snack(page, f"{task['id']} completed.", kind="success"),
                    _refresh(page),
                ))

    user_role = (page.data.get("user") or {}).get("role", "user")
    
    action_controls = []
    if user_role == "manager":
        action_controls.extend([
            ft.OutlinedButton(
                content=ft.Row(spacing=6, tight=True, controls=[
                    ft.Icon(ft.Icons.RESTART_ALT, size=16, color=Colors.TEXT),
                    ft.Text("Reset Path", size=13,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT),
                ]),
                on_click=reset_path,
                style=ft.ButtonStyle(
                    side=ft.BorderSide(1, Colors.BORDER),
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                ),
            ),
            ft.ElevatedButton(
                content=ft.Row(spacing=6, tight=True, controls=[
                    ft.Icon(ft.Icons.PLAY_ARROW, size=16, color="#FFFFFF"),
                    ft.Text("Force Complete", size=13,
                            weight=ft.FontWeight.W_600, color="#FFFFFF"),
                ]),
                bgcolor=Colors.PRIMARY, color="#FFFFFF",
                on_click=force_complete,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                    elevation=0,
                ),
            ),
        ])

    actions = ft.Row(spacing=10, controls=action_controls)
    return ft.ResponsiveRow(
        run_spacing=14,
        controls=[
            ft.Container(content=title, col={"xs": 12, "lg": 8}),
            ft.Container(
                content=ft.Row(controls=[actions],
                               alignment=ft.MainAxisAlignment.END),
                col={"xs": 12, "lg": 4},
            ),
        ],
    )


def _meta_tile(icon, label: str, value: str, icon_bg: str, icon_color: str,
               trailing: ft.Control | None = None) -> ft.Container:
    inner = [
        ft.Container(width=40, height=40, bgcolor=icon_bg, border_radius=10,
                     alignment=ft.Alignment.CENTER,
                     content=ft.Icon(icon, color=icon_color, size=20)),
        ft.Column(spacing=2, expand=True, controls=[
            ft.Text(label, size=10, weight=ft.FontWeight.W_700,
                    color=Colors.TEXT_MUTED),
            ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
        ]),
    ]
    if trailing:
        inner.append(trailing)
    return ft.Container(
        bgcolor=Colors.SURFACE,
        border=ft.Border.all(1, Colors.BORDER),
        border_radius=12,
        padding=14,
        content=ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                       controls=inner),
    )


def _meta_row(page: ft.Page, task: dict) -> ft.Control:
    elapsed = task["elapsed_secs"] or 0
    mins, secs = divmod(elapsed, 60)
    elapsed_label = f"{mins:02d}m {secs:02d}s"

    progress_card = ft.Container(
        bgcolor=Colors.SURFACE,
        border=ft.Border.all(1, Colors.BORDER),
        border_radius=12,
        padding=14,
        content=ft.Column(spacing=8, controls=[
            ft.Row(controls=[
                ft.Text("TASK PROGRESS", size=10,
                        weight=ft.FontWeight.W_700, color=Colors.TEXT_MUTED,
                        expand=True),
                ft.Text(f"{int(task['progress']*100)}%", size=14,
                        weight=ft.FontWeight.BOLD, color=Colors.TEXT),
            ]),
            progress_bar(task["progress"], height=8),
        ]),
    )

    items = [
        _meta_tile(ft.Icons.SCHEDULE, "ELAPSED TIME", elapsed_label,
                   "#F1F5F9", Colors.TEXT),
        _meta_tile(ft.Icons.BOLT, "PRIORITY LEVEL", task["priority"],
                   Colors.PRIMARY_SOFT, Colors.PRIMARY),
        _meta_tile(ft.Icons.SMART_TOY_OUTLINED, "ASSIGNED ROBOT",
                   task["robot_id"] or "Unassigned",
                   Colors.PRIMARY_SOFT, Colors.PRIMARY,
                   trailing=ft.Icon(ft.Icons.NORTH_EAST, size=14,
                                    color=Colors.TEXT_FAINT)),
    ]
    return ft.ResponsiveRow(
        run_spacing=14,
        controls=[
            *[ft.Container(content=i, col={"xs": 12, "sm": 6, "lg": 3})
              for i in items],
            ft.Container(content=progress_card, col={"xs": 12, "sm": 6, "lg": 3}),
        ],
    )


def _pathing_visual(page: ft.Page, task: dict) -> ft.Control:
    pct = max(0.05, min(task["progress"], 0.95))
    chip_left_pct = int(pct * 100)
    src = ft.Column(
        spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(width=56, height=56, bgcolor=Colors.PRIMARY_SOFT,
                         border_radius=999, alignment=ft.Alignment.CENTER,
                         content=ft.Icon(ft.Icons.PLACE, size=28,
                                         color=Colors.PRIMARY)),
            ft.Text("SOURCE", size=10, weight=ft.FontWeight.W_700,
                    color=Colors.TEXT_MUTED),
            ft.Text(task["source"], size=14, weight=ft.FontWeight.BOLD,
                    color=Colors.TEXT),
            ft.Text("Sector North-A", size=11, color=Colors.TEXT_MUTED),
        ],
    )
    dst = ft.Column(
        spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(width=56, height=56, bgcolor=Colors.PRIMARY_SOFT,
                         border_radius=999, alignment=ft.Alignment.CENTER,
                         content=ft.Icon(ft.Icons.INVENTORY_2, size=26,
                                         color=Colors.PRIMARY)),
            ft.Text("DESTINATION", size=10, weight=ft.FontWeight.W_700,
                    color=Colors.TEXT_MUTED),
            ft.Text(task["destination"], size=14, weight=ft.FontWeight.BOLD,
                    color=Colors.TEXT),
            ft.Text("Zone High-Density", size=11, color=Colors.TEXT_MUTED),
        ],
    )
    middle = ft.Column(
        expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14,
        controls=[
            ft.Stack(
                width=240, height=44,
                controls=[
                    ft.Container(top=18, width=240,
                                 content=ft.Row(controls=[
                                     ft.Container(expand=chip_left_pct, height=2,
                                                  bgcolor=Colors.PRIMARY),
                                     ft.Container(expand=100 - chip_left_pct,
                                                  height=2,
                                                  bgcolor=Colors.PRIMARY_SOFT),
                                 ])),
                    ft.Container(
                        left=int(2.4 * chip_left_pct) - 30, top=4,
                        bgcolor=Colors.PRIMARY,
                        border_radius=6,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                        content=ft.Row(spacing=4, tight=True, controls=[
                            ft.Icon(ft.Icons.SMART_TOY, color="#FFFFFF", size=12),
                            ft.Text(task["robot_id"] or "—", size=10,
                                    weight=ft.FontWeight.W_700, color="#FFFFFF"),
                        ]),
                    ),
                ],
            ),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[
                    ft.Column(spacing=2,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                              controls=[
                                  ft.Text("EST. DISTANCE:", size=10,
                                          weight=ft.FontWeight.W_700,
                                          color=Colors.TEXT_MUTED),
                                  ft.Text("124M", size=12,
                                          weight=ft.FontWeight.BOLD,
                                          color=Colors.TEXT),
                              ]),
                    ft.Column(spacing=2,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                              controls=[
                                  ft.Text("AVG. SPEED:", size=10,
                                          weight=ft.FontWeight.W_700,
                                          color=Colors.TEXT_MUTED),
                                  ft.Text("1.2M/S", size=12,
                                          weight=ft.FontWeight.BOLD,
                                          color=Colors.TEXT),
                              ]),
                ],
            ),
        ],
    )
    visualization = ft.Container(
        bgcolor=Colors.BG,
        border=ft.Border.all(1, Colors.BORDER_LIGHT),
        border_radius=10,
        padding=20,
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[src, middle, dst],
        ),
    )

    specs = ft.ResponsiveRow(
        run_spacing=10,
        controls=[
            ft.Container(
                col={"xs": 12, "md": 6},
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=6, controls=[
                        ft.Icon(ft.Icons.PLACE_OUTLINED, size=14,
                                color=Colors.PRIMARY),
                        ft.Text("ZONE SPECIFICATIONS", size=10,
                                weight=ft.FontWeight.W_700,
                                color=Colors.TEXT_MUTED),
                    ]),
                    *[
                        ft.Row(controls=[
                            ft.Text(k, size=12, color=Colors.TEXT_MUTED, expand=True),
                            ft.Text(v, size=12, weight=ft.FontWeight.W_600,
                                    color=Colors.TEXT),
                        ])
                        for k, v in [
                            ("Source Sector", "North Loading Dock (L-04)"),
                            ("Destination Sector", "Cold Storage Wing (S-12)"),
                            ("Required Clearance", "Level 2 / Hazardous"),
                        ]
                    ],
                ]),
            ),
            ft.Container(
                col={"xs": 12, "md": 6},
                content=ft.Column(spacing=8, controls=[
                    ft.Row(spacing=6, controls=[
                        ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=14,
                                color=Colors.PRIMARY),
                        ft.Text("PAYLOAD DETAILS", size=10,
                                weight=ft.FontWeight.W_700,
                                color=Colors.TEXT_MUTED),
                    ]),
                    *[
                        ft.Row(controls=[
                            ft.Text(k, size=12, color=Colors.TEXT_MUTED, expand=True),
                            ft.Text(v, size=12, weight=ft.FontWeight.W_600,
                                    color=Colors.TEXT),
                        ])
                        for k, v in [
                            ("Content Type", "Standard Euro Pallet (Mixed)"),
                            ("Total Weight", "420.5 kg"),
                            ("Fragility Index", "Medium-Low"),
                        ]
                    ],
                ]),
            ),
        ],
    )

    def recompute_path():
        _log(task["id"], "Path recomputed via overlay menu.")
        show_snack(page, "Path recomputed.", kind="success")
        _refresh(page)

    def reroute_avoid_traffic():
        _log(task["id"], "Re-routed to avoid high-traffic Sector B.")
        show_snack(page, "Alternate path selected (avoiding Sector B).",
                   kind="success")
        _refresh(page)

    path_menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT, icon_color=Colors.TEXT_MUTED,
        items=[
            ft.PopupMenuItem(content="Recompute path",
                             on_click=lambda _: recompute_path()),
            ft.PopupMenuItem(content="Avoid high-traffic zones",
                             on_click=lambda _: reroute_avoid_traffic()),
        ],
    )

    return panel(
        "Pathing Visualization",
        subtitle=f"Real-time spatial tracking of {task['id']}",
        trailing=path_menu,
        body=ft.Column(spacing=18, controls=[visualization, specs]),
    )


def _live_telemetry(page: ft.Page, robot: dict | None) -> ft.Control:
    if robot:
        items = [
            ("BATTERY", f"{int(robot['battery']*100)}%"),
            ("TEMP", f"{int(robot['temperature'])}°C"),
            ("CONNECTIVITY", "98ms"),
            ("TORQUE", "12 Nm"),
        ]
    else:
        items = [("BATTERY", "—"), ("TEMP", "—"),
                 ("CONNECTIVITY", "—"), ("TORQUE", "—")]
    cells = [
        ft.Container(
            col={"xs": 6, "md": 3},
            padding=14, bgcolor=Colors.BG, border_radius=10,
            content=ft.Column(spacing=4, controls=[
                ft.Text(label, size=10, weight=ft.FontWeight.W_700,
                        color=Colors.TEXT_MUTED),
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD,
                        color=Colors.TEXT),
            ]),
        )
        for label, value in items
    ]
    body = ft.ResponsiveRow(run_spacing=10, controls=cells)
    def open_telemetry(_):
        if robot:
            extra = ft.Column(spacing=10, controls=[
                ft.Text(f"Robot: {robot['id']} — {robot['model']}",
                        size=13, weight=ft.FontWeight.W_600,
                        color=Colors.TEXT),
                ft.Text(f"Serial: {robot['serial']}",
                        size=12, color=Colors.TEXT_MUTED),
                ft.Divider(color=Colors.BORDER_LIGHT, thickness=1, height=1),
                *[ft.Row(controls=[
                    ft.Text(k, size=12, color=Colors.TEXT_MUTED, expand=True),
                    ft.Text(v, size=12, weight=ft.FontWeight.W_600,
                            color=Colors.TEXT),
                  ])
                  for k, v in [
                      ("Status", robot["status"]),
                      ("Zone", robot["zone"]),
                      ("Battery",
                       f"{int(robot['battery']*100)}%"),
                      ("Temperature",
                       f"{int(robot['temperature'])}°C"),
                      ("Signal", robot["signal"]),
                      ("Last maintenance", robot["last_maintenance"]),
                  ]],
            ])
        else:
            extra = ft.Text("No robot assigned to this task.",
                            size=13, color=Colors.TEXT_MUTED)
        info_dialog(page, "Live Robot Telemetry", extra)

    return panel(
        "Live Robot Telemetry",
        trailing=ft.IconButton(
            icon=ft.Icons.EXPAND_MORE, icon_color=Colors.TEXT_MUTED,
            tooltip="Expanded telemetry",
            on_click=open_telemetry,
        ),
        body=body,
    )


def _mission_controls(page: ft.Page, task: dict) -> ft.Control:
    def pause(_):
        new_status = "Paused" if task["status"] != "Paused" else "In Progress"
        db.update_task_status(task["id"], new_status)
        _log(task["id"], f"Task {new_status.lower()} by operator.")
        show_snack(page, f"{task['id']} → {new_status}", kind="success")
        _refresh(page)

    def abort(_):
        confirm(page, "Abort task?",
                f"This cancels {task['id']} and frees the robot.",
                confirm_label="Abort", danger=True,
                on_confirm=lambda: (
                    db.update_task_status(task["id"], "Aborted"),
                    _log(task["id"], "Task aborted by operator."),
                    show_snack(page, f"{task['id']} aborted.", kind="error"),
                    _refresh(page),
                ))

    def set_priority(level: str):
        db.update_task_priority(task["id"], level)
        show_snack(page, f"Priority → {level}", kind="info")
        _refresh(page)

    def reassign(robot_id: str):
        def submit(_): pass
        # We use a one-line dialog
        form_dialog(page, "Reassign Robot",
                    fields=[("robot_id", "Robot ID", robot_id or "")],
                    submit_label="Reassign",
                    on_submit=lambda v: (
                        _do_reassign(page, task, v.get("robot_id", "").strip()),
                    ))

    other_robots = [r for r in db.list_robots() if r["id"] != task["robot_id"]][:2]

    def priority_pill(level: str) -> ft.Control:
        active = (task["priority"] == level)
        bg = Colors.PRIMARY if (active and level not in ("Urgent",)) \
            else Colors.DANGER if (active and level == "Urgent") \
            else Colors.BG
        fg = "#FFFFFF" if active else Colors.TEXT_MUTED
        weight = ft.FontWeight.W_600 if active else ft.FontWeight.W_500
        return ft.Container(
            bgcolor=bg,
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            ink=True,
            on_click=lambda _, _l=level: set_priority(_l),
            content=ft.Text(level, size=12, color=fg, weight=weight),
        )

    body = ft.Column(spacing=14, controls=[
        ft.Text(f"Manual overrides for {task['id']}",
                size=12, color=Colors.TEXT_MUTED),
        ft.Row(spacing=10, controls=[
            ft.OutlinedButton(
                content=ft.Row(spacing=6, tight=True, controls=[
                    ft.Icon(ft.Icons.PAUSE if task["status"] != "Paused"
                            else ft.Icons.PLAY_ARROW,
                            size=14, color=Colors.TEXT),
                    ft.Text("Pause" if task["status"] != "Paused" else "Resume",
                            size=13, color=Colors.TEXT,
                            weight=ft.FontWeight.W_600),
                ]),
                expand=True, on_click=pause,
                style=ft.ButtonStyle(
                    side=ft.BorderSide(1, Colors.BORDER),
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                ),
            ),
            ft.OutlinedButton(
                content=ft.Row(spacing=6, tight=True, controls=[
                    ft.Icon(ft.Icons.STOP_CIRCLE_OUTLINED, size=14,
                            color=Colors.DANGER),
                    ft.Text("Abort", size=13, color=Colors.DANGER,
                            weight=ft.FontWeight.W_600),
                ]),
                expand=True, on_click=abort,
                style=ft.ButtonStyle(
                    side=ft.BorderSide(1, Colors.DANGER_BORDER),
                    bgcolor=Colors.DANGER_SOFT,
                    shape=ft.RoundedRectangleBorder(radius=10),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                ),
            ),
        ]),
        ft.Text("ASSIGN NEW ROBOT", size=10, weight=ft.FontWeight.W_700,
                color=Colors.TEXT_MUTED),
        *[
            ft.Container(
                bgcolor=Colors.BG,
                border=ft.Border.all(1, Colors.BORDER_LIGHT),
                border_radius=10,
                padding=10,
                ink=True,
                on_click=lambda _, _rid=r["id"]: confirm(
                    page, "Reassign robot?",
                    f"Hand off {task['id']} from {task['robot_id'] or 'unassigned'} "
                    f"to {_rid}.",
                    confirm_label="Reassign",
                    on_confirm=lambda _r=_rid: _do_reassign(page, task, _r),
                ),
                content=ft.Row(spacing=10, controls=[
                    ft.Container(width=28, height=28,
                                 bgcolor=Colors.PRIMARY_SOFT,
                                 border_radius=999,
                                 alignment=ft.Alignment.CENTER,
                                 content=ft.Icon(ft.Icons.SMART_TOY, size=16,
                                                 color=Colors.PRIMARY)),
                    ft.Column(spacing=0, expand=True, controls=[
                        ft.Text(r["id"], size=13, weight=ft.FontWeight.W_600,
                                color=Colors.TEXT),
                        ft.Text(f"{r['model']}", size=11,
                                color=Colors.TEXT_MUTED),
                    ]),
                    ft.Container(width=70,
                                 content=progress_bar(r["battery"], height=5)),
                    ft.Text(f"{int(r['battery']*100)}%", size=12,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT),
                ]),
            )
            for r in other_robots
        ],
        ft.OutlinedButton(
            content=ft.Text("View All Robots", size=13,
                            weight=ft.FontWeight.W_600, color=Colors.TEXT),
            on_click=lambda _: page.go("/robots"),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, Colors.BORDER),
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            ),
        ),
        ft.Text("PRIORITY LEVEL", size=10, weight=ft.FontWeight.W_700,
                color=Colors.TEXT_MUTED),
        ft.Row(spacing=8, controls=[priority_pill(p)
                                    for p in ("Low", "Medium", "High", "Urgent")]),
    ])
    return panel("Mission Controls", body=body)


def _do_reassign(page: ft.Page, task: dict, new_robot_id: str) -> None:
    if not new_robot_id:
        show_snack(page, "Robot ID is required.", kind="warning")
        return
    if not db.get_robot(new_robot_id):
        show_snack(page, f"Unknown robot {new_robot_id}.", kind="error")
        return
    with db.cursor() as cur:
        cur.execute("UPDATE tasks SET robot_id=? WHERE id=?",
                    (new_robot_id, task["id"]))
    _log(task["id"], f"Robot reassigned to {new_robot_id}.")
    show_snack(page, f"{task['id']} reassigned to {new_robot_id}.",
               kind="success")
    _refresh(page)


def _mission_log(page: ft.Page, task: dict) -> ft.Control:
    items = db.list_mission_log(task["id"])
    rows = [
        ft.Column(spacing=2, controls=[
            ft.Text(it["ts"], size=11, color=Colors.TEXT_MUTED,
                    weight=ft.FontWeight.W_600),
            ft.Text(it["msg"], size=12, color=Colors.TEXT),
        ])
        for it in items
    ] or [ft.Text("No log entries yet.", size=13, color=Colors.TEXT_MUTED)]

    body = ft.Column(spacing=14, controls=[
        *rows,
        ft.Container(
            bgcolor=Colors.PRIMARY_SOFT,
            border=ft.Border.all(1, Colors.PRIMARY_BORDER),
            border_radius=10,
            padding=12,
            content=ft.Column(spacing=4, controls=[
                ft.Row(spacing=6, controls=[
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=Colors.PRIMARY),
                    ft.Text("MANUAL INTERVENTION TIP", size=10,
                            weight=ft.FontWeight.W_700, color=Colors.PRIMARY),
                ]),
                ft.Text(
                    "If the robot remains stationary for more than 2 minutes in a "
                    "high-traffic zone, consider manual remote override or "
                    "re-assignment.",
                    size=12, color=Colors.PRIMARY,
                ),
            ]),
        ),
    ])
    def open_raw(_):
        if not items:
            content = ft.Text("No log entries yet.", size=13,
                              color=Colors.TEXT_MUTED)
        else:
            raw = "\n".join(f"[{it['ts']}] {it['msg']}" for it in items)
            content = ft.Container(
                bgcolor=Colors.BG,
                border=ft.Border.all(1, Colors.BORDER_LIGHT),
                border_radius=8,
                padding=12,
                content=ft.Text(raw, size=12, color=Colors.TEXT,
                                font_family="monospace",
                                selectable=True),
            )
        info_dialog(page, f"Raw Mission Log — {task['id']}", content)

    return panel(
        "Mission Log",
        trailing=ft.TextButton(
            "View Raw",
            on_click=open_raw,
            style=ft.ButtonStyle(color=Colors.TEXT_MUTED),
        ),
        body=body,
    )


def task_detail_view(page: ft.Page) -> ft.Control:
    user_role = (page.data.get("user") or {}).get("role", "user")
    tid = (page.data or {}).get("selected_task_id") or DEFAULT_TASK_ID
    task = db.get_task(tid)
    if not task:
        page.data["selected_task_id"] = DEFAULT_TASK_ID
        task = db.get_task(DEFAULT_TASK_ID)
    if not task:
        return ft.Text("Task not found.", size=16, color=Colors.DANGER)
    robot = db.get_robot(task["robot_id"]) if task["robot_id"] else None
    return ft.Column(
        spacing=20,
        controls=[
            _header(page, task),
            _meta_row(page, task),
            ft.ResponsiveRow(
                run_spacing=20,
                controls=[
                    ft.Container(
                        col={"xs": 12, "lg": 8},
                        content=ft.Column(spacing=20, controls=[
                            _pathing_visual(page, task),
                            _live_telemetry(page, robot),
                        ]),
                    ),
                    ft.Container(
                        col={"xs": 12, "lg": 4},
                        content=ft.Column(spacing=20, controls=[
                            _mission_controls(page, task) if user_role == "manager" else 
                            panel("Mission Controls", body=ft.Text("Management controls restricted to System Administrators.", 
                                                                  size=13, color=Colors.TEXT_MUTED, italic=True)),
                            _mission_log(page, task),
                        ]),
                    ),
                ],
            ),
        ],
    )
