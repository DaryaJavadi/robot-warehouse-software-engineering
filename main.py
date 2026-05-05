"""FleetOps — Robot Warehouse Management dashboard built with Flet."""
from __future__ import annotations

import flet as ft

import db
from theme import Colors
from components.shell import shell
from views.signin import signin_view
from views.dashboard import dashboard_view
from views.robot_detail import robot_detail_view
from views.task_detail import task_detail_view
from views.inventory import inventory_view
from views.charging import charging_view


# Routes that map to (active sidebar key, builder).
ROUTES = {
    "/dashboard": ("dashboard", dashboard_view),
    "/robots":    ("robots",    robot_detail_view),
    "/tasks":     ("tasks",     task_detail_view),
    "/inventory": ("inventory", inventory_view),
    "/charging":  ("charging",  charging_view),
}


def main(page: ft.Page) -> None:
    db.init()

    page.title = "FleetOps — Warehouse Robot Control"
    page.bgcolor = Colors.BG
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=Colors.PRIMARY,
        font_family="Inter",
        use_material3=True,
    )
    page.window.min_width = 360
    page.window.min_height = 600
    page.window.width = 1280
    page.window.height = 880

    # Page-level state bag (auth, refresh callback). Init as dict before use.
    page.data = {"user": None}

    def render() -> None:
        page.controls.clear()
        page.overlay.clear()
        # Drain any lingering dialogs from the stack
        try:
            while page.pop_dialog() is not None:
                pass
        except Exception:
            pass
        route = page.route or "/"
        signed_in = bool((page.data or {}).get("user"))
        # Auth gate: render sign-in for "/" OR any route while not signed in.
        # Don't mutate page.route here — that would re-trigger render.
        if route in ("/", "") or not signed_in:
            page.controls.append(signin_view(page))
        else:
            entry = ROUTES.get(route)
            if entry is None:
                page.route = "/dashboard"
                entry = ROUTES["/dashboard"]
            active, builder = entry
            page.controls.append(shell(page, active, builder(page)))
        page.update()

    # Expose a global refresh handler the views can use to rebuild after DB writes
    page.data["refresh"] = render

    def on_route_change(_: ft.RouteChangeEvent) -> None:
        render()

    def on_resize(_: ft.PageResizeEvent) -> None:
        render()

    page.on_route_change = on_route_change
    page.on_resized = on_resize

    if not page.route or page.route == "/":
        page.route = "/"
    render()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
