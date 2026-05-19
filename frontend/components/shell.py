"""App shell — responsive sidebar + topbar wrapper used by every view except Sign In."""
from __future__ import annotations

import flet as ft

import db
from theme import Colors
from components.dialogs import show_snack, confirm, info_dialog


def _do_search(page: ft.Page, query: str) -> None:
    if not query:
        show_snack(page, "Enter a search term.", kind="warning")
        return
    q = query.lower()
    robots = [r for r in db.list_robots()
              if q in r["id"].lower() or q in r["model"].lower()
              or q in r["zone"].lower() or q in r["status"].lower()]
    tasks = [t for t in db.list_tasks()
             if q in t["id"].lower() or q in t["name"].lower()
             or q in t["status"].lower() or q in t["priority"].lower()]
    zones = [z for z in db.list_zones()
             if q in z["name"].lower() or q in z["category"].lower()
             or q in z["status"].lower()]

    total = len(robots) + len(tasks) + len(zones)
    if total == 0:
        show_snack(page, f"No matches for '{query}'.", kind="info")
        return

    sections: list[ft.Control] = []

    def header(text: str, count: int) -> ft.Control:
        return ft.Text(f"{text}  ({count})", size=11,
                       weight=ft.FontWeight.W_700, color=Colors.TEXT_MUTED)

    def select_robot(rid: str):
        page.data["selected_robot_id"] = rid
        try:
            page.pop_dialog()
        except Exception:
            pass
        page.go("/robots")

    def select_task(tid: str):
        page.data["selected_task_id"] = tid
        try:
            page.pop_dialog()
        except Exception:
            pass
        page.go("/tasks")

    def select_zone(_zid: int):
        try:
            page.pop_dialog()
        except Exception:
            pass
        page.go("/inventory")

    if robots:
        sections.append(header("ROBOTS", len(robots)))
        for r in robots[:8]:
            sections.append(ft.Container(
                ink=True,
                padding=ft.Padding.symmetric(horizontal=8, vertical=8),
                border_radius=6,
                on_click=lambda _, _rid=r["id"]: select_robot(_rid),
                content=ft.Row(controls=[
                    ft.Text(r["id"], size=12, weight=ft.FontWeight.W_700,
                            color=Colors.PRIMARY, width=80),
                    ft.Text(f"{r['model']} • {r['zone']}", size=12,
                            color=Colors.TEXT, expand=True),
                    ft.Text(r["status"], size=11,
                            color=Colors.TEXT_MUTED),
                ]),
            ))
    if tasks:
        sections.append(ft.Container(height=4))
        sections.append(header("TASKS", len(tasks)))
        for t in tasks[:8]:
            sections.append(ft.Container(
                ink=True,
                padding=ft.Padding.symmetric(horizontal=8, vertical=8),
                border_radius=6,
                on_click=lambda _, _tid=t["id"]: select_task(_tid),
                content=ft.Row(controls=[
                    ft.Text(t["id"], size=12, weight=ft.FontWeight.W_700,
                            color=Colors.PRIMARY, width=80),
                    ft.Text(f"{t['name']} • {t['priority']}", size=12,
                            color=Colors.TEXT, expand=True),
                    ft.Text(t["status"], size=11,
                            color=Colors.TEXT_MUTED),
                ]),
            ))
    if zones:
        sections.append(ft.Container(height=4))
        sections.append(header("ZONES", len(zones)))
        for z in zones[:8]:
            pct = (z["used"] / z["capacity"] * 100) if z["capacity"] else 0
            sections.append(ft.Container(
                ink=True,
                padding=ft.Padding.symmetric(horizontal=8, vertical=8),
                border_radius=6,
                on_click=lambda _, _zid=z["id"]: select_zone(_zid),
                content=ft.Row(controls=[
                    ft.Text(z["name"], size=12, weight=ft.FontWeight.W_600,
                            color=Colors.TEXT, expand=True),
                    ft.Text(f"{int(pct)}%  •  {z['status']}", size=11,
                            color=Colors.DANGER if z["status"] == "CRITICAL"
                            else Colors.TEXT_MUTED),
                ]),
            ))

    info_dialog(page, f"Search: '{query}' ({total} match{'es' if total != 1 else ''})",
                ft.Column(spacing=4, tight=True, controls=sections))


NAV_ITEMS = [
    ("dashboard", "Dashboard",       ft.Icons.GRID_VIEW_OUTLINED,    "/dashboard"),
    ("robots",    "Robots",          ft.Icons.SMART_TOY_OUTLINED,    "/robots"),
    ("tasks",     "Tasks",           ft.Icons.ASSIGNMENT_OUTLINED,   "/tasks"),
    ("inventory", "Inventory Zones", ft.Icons.INVENTORY_2_OUTLINED,  "/inventory"),
    ("charging",  "Charging",        ft.Icons.BOLT_OUTLINED,         "/charging"),
    ("add_robot", "Add Robot",       ft.Icons.ADD_BOX_OUTLINED,      "/add_robot"),
]


def _nav_button(label: str, icon, route: str, active: bool, page: ft.Page,
                on_select=None) -> ft.Container:
    bg = Colors.PRIMARY_SOFT if active else "#00000000"
    fg = Colors.PRIMARY if active else Colors.TEXT_MUTED
    fw = ft.FontWeight.W_600 if active else ft.FontWeight.W_500

    def _click(_):
        if on_select:
            on_select()
        page.go(route)

    return ft.Container(
        bgcolor=bg,
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=14, vertical=11),
        on_click=_click,
        ink=True,
        content=ft.Row(
            spacing=12,
            controls=[
                ft.Icon(icon, color=fg, size=20),
                ft.Text(label, size=14, weight=fw, color=fg),
            ],
        ),
    )


def _logo() -> ft.Row:
    return ft.Row(
        spacing=8,
        controls=[
            ft.Container(
                width=28, height=28,
                bgcolor=Colors.PRIMARY_SOFT,
                border_radius=8,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.AUTO_GRAPH, color=Colors.PRIMARY, size=18),
            ),
            ft.Text("FleetOps", size=18, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
        ],
    )


def _action_button(label: str, icon, page: ft.Page,
                   on_click, on_select=None) -> ft.Container:
    def _click(e):
        if on_select:
            on_select()
        on_click(e)
    return ft.Container(
        bgcolor="#00000000",
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=14, vertical=11),
        on_click=_click, ink=True,
        content=ft.Row(spacing=12, controls=[
            ft.Icon(icon, color=Colors.TEXT_MUTED, size=20),
            ft.Text(label, size=14, weight=ft.FontWeight.W_500,
                    color=Colors.TEXT_MUTED),
        ]),
    )


def _sidebar_content(active: str, page: ft.Page,
                     on_select=None) -> ft.Column:
    user_role = (page.data.get("user") or {}).get("role", "user")

    # Filter navigation items based on role:
    visible_nav = []
    for key, label, icon, route in NAV_ITEMS:
        # Restriction: Only 'manager' can see 'Add Robot' (key: add_robot)
        if key == "add_robot" and user_role != "manager":
            continue
        visible_nav.append(
            _nav_button(label, icon, route, key == active, page, on_select)
        )

    def open_settings(_):
        if user_role != "manager":
            show_snack(page, "Access Denied: Administrative privileges required.", kind="error")
            return
        
        confirm(page, "Reset demo data?",
                "This wipes the local database and re-seeds the sample data.",
                confirm_label="Reset",
                on_confirm=lambda: (
                    db.reset(),
                    show_snack(page, "Demo data reset.", kind="success"),
                    (page.data or {}).get("refresh")
                    and (page.data or {}).get("refresh")(),
                ))

    def logout(_):
        page.data["user"] = None
        show_snack(page, "Signed out.", kind="info")
        page.go("/")

    return ft.Column(
        expand=True,
        controls=[
            ft.Container(padding=ft.Padding.symmetric(horizontal=20, vertical=22),
                         content=_logo()),
            ft.Container(
                expand=True,
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                content=ft.Column(spacing=4, controls=visible_nav),
            ),
            ft.Divider(color=Colors.BORDER_LIGHT, thickness=1, height=1),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=12, vertical=12),
                content=ft.Column(spacing=4, controls=[
                    _action_button("Settings", ft.Icons.SETTINGS_OUTLINED,
                                   page, open_settings, on_select),
                    _action_button("Logout", ft.Icons.LOGOUT,
                                   page, logout, on_select),
                ]),
            ),
        ],
    )


def _topbar(page: ft.Page, on_menu=None, show_menu: bool = False) -> ft.Container:
    search_field = ft.TextField(
        hint_text="Search robots, tasks, or zones...",
        border_color=Colors.BG,
        focused_border_color=Colors.PRIMARY,
        bgcolor=Colors.BG,
        border_radius=10,
        text_size=13,
        height=44,
        prefix_icon=ft.Icons.SEARCH,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        on_submit=lambda e: _do_search(page, (e.control.value or "").strip()),
    )
    search = ft.Container(expand=True, content=search_field)

    user_data = page.data.get("user") or {"name": "Guest User", "role": "user"}
    user_display_name = user_data.get("name", "Unknown")
    user_display_role = "System Administrator" if user_data.get("role") == "manager" else "Basic Operator"

    user = ft.Row(
        spacing=10,
        controls=[
            ft.Stack(
                width=40, height=40,
                controls=[
                    ft.CircleAvatar(
                        bgcolor=Colors.PRIMARY_SOFT,
                        radius=18,
                        content=ft.Icon(ft.Icons.PERSON, color=Colors.PRIMARY, size=20),
                    ),
                    ft.Container(
                        right=2, bottom=2,
                        width=10, height=10,
                        bgcolor=Colors.SUCCESS,
                        border_radius=999,
                        border=ft.Border.all(2, Colors.SURFACE),
                    ),
                ],
            ),
            ft.Column(
                spacing=0,
                horizontal_alignment=ft.CrossAxisAlignment.END,
                controls=[
                    ft.Text(user_display_name, size=13, weight=ft.FontWeight.W_600,
                            color=Colors.TEXT),
                    ft.Text(user_display_role, size=11, color=Colors.TEXT_MUTED),
                ],
            ),
        ],
    )

    alert_count = len(db.list_alerts(limit=99))

    def open_alerts(_):
        # Reuse dashboard's All Alerts dialog (lazy import to avoid cycle)
        from views.dashboard import _open_all_alerts
        _open_all_alerts(page)

    bell = ft.Stack(
        width=36, height=36,
        controls=[
            ft.IconButton(icon=ft.Icons.NOTIFICATIONS_OUTLINED,
                          icon_color=Colors.TEXT_MUTED, icon_size=22,
                          on_click=open_alerts),
            *([
                ft.Container(right=8, top=8, width=8, height=8,
                             bgcolor=Colors.DANGER, border_radius=999,
                             border=ft.Border.all(2, Colors.SURFACE))
            ] if alert_count else []),
        ],
    )

    leading: list[ft.Control] = []
    if show_menu:
        leading.append(
            ft.IconButton(
                icon=ft.Icons.MENU,
                icon_color=Colors.TEXT,
                on_click=lambda _: on_menu and on_menu(),
            )
        )

    return ft.Container(
        bgcolor=Colors.SURFACE,
        height=72,
        padding=ft.Padding.symmetric(horizontal=24, vertical=14),
        border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER_LIGHT)),
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[*leading, search, bell, user],
        ),
    )


def _footer() -> ft.Container:
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=24, vertical=16),
        border=ft.Border.only(top=ft.BorderSide(1, Colors.BORDER_LIGHT)),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("© 2026 FleetOps Logistics Solutions. All rights reserved.",
                        size=12, color=Colors.TEXT_MUTED),
                ft.Row(spacing=10, controls=[
                    ft.Text("System Status:", size=12, color=Colors.TEXT_MUTED),
                    ft.Text("Optimal", size=12, weight=ft.FontWeight.W_600,
                            color=Colors.SUCCESS),
                    ft.Text("Version 2.4.0-release", size=12, color=Colors.TEXT_MUTED),
                ]),
            ],
        ),
    )


def shell(page: ft.Page, active: str, body: ft.Control) -> ft.Control:
    """Wrap a page body with sidebar + topbar. Sidebar collapses below 900px."""
    width = page.width or 1280
    is_narrow = width < 900

    def close_drawer():
        drawer.open = False
        page.update()

    # Reuse or create drawer
    if not isinstance(page.drawer, ft.NavigationDrawer):
        drawer = ft.NavigationDrawer(
            bgcolor=Colors.SIDEBAR,
            controls=[ft.Container(width=260, expand=True,
                                   content=_sidebar_content(active, page,
                                                            on_select=close_drawer))],
        )
        page.drawer = drawer
    else:
        # Update existing drawer content to reflect active state
        drawer = page.drawer
        drawer.controls[0].content = _sidebar_content(active, page, on_select=close_drawer)

    def open_drawer():
        drawer.open = True
        page.update()

    sidebar = ft.Container(
        width=240,
        bgcolor=Colors.SIDEBAR,
        border=ft.Border.only(right=ft.BorderSide(1, Colors.BORDER_LIGHT)),
        content=_sidebar_content(active, page),
    )

    main_col = ft.Column(
        expand=True,
        spacing=0,
        controls=[
            _topbar(page, on_menu=open_drawer, show_menu=is_narrow),
            ft.Container(
                expand=True,
                bgcolor=Colors.BG,
                content=ft.Column(
                    expand=True,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=0,
                    controls=[
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=24, vertical=22),
                            content=body,
                        ),
                        _footer(),
                    ],
                ),
            ),
        ],
    )

    if is_narrow:
        return main_col

    return ft.Row(
        expand=True,
        spacing=0,
        controls=[sidebar, main_col],
    )
