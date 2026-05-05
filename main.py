"""FleetOps — Robot Warehouse Management dashboard built with Flet."""
from __future__ import annotations

import flet as ft

import db
from theme import Colors
from components.shell import shell # The shell wraps all pages except sign-in.
from views.signin import signin_view
from views.dashboard import dashboard_view
from views.robot_detail import robot_detail_view
from views.task_detail import task_detail_view
from views.inventory import inventory_view
from views.charging import charging_view
from views.add_robot import add_robot_view


ROUTES = {
    "/dashboard":  ("dashboard",  dashboard_view),
    "/robots":     ("robots",     robot_detail_view),
    "/tasks":      ("tasks",      task_detail_view),
    "/inventory":  ("inventory",  inventory_view),
    "/charging":   ("charging",   charging_view),
    "/add_robot":  ("add_robot",  add_robot_view),
}


def main(page: ft.Page) -> None:
    db.init() # creates tables, checks schema, prepares DB.

    page.title = "FleetOps — Warehouse Robot Control"
    page.bgcolor = Colors.BG
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.LIGHT # light mode.
    
    # UI part:
    page.theme = ft.Theme(
        color_scheme_seed=Colors.PRIMARY,
        font_family="Inter",
        use_material3=True,
    )
    page.window.min_width = 360
    page.window.min_height = 600
    page.window.width = 1280
    page.window.height = 880

    #  signed-in user info, auth session, refresh callback. Init as dict before use.
    page.data = {"user": None} # currently no user is logged in.

    def render() -> None: # removing old UI before drawing new UI.
        page.controls.clear()
        page.overlay.clear()
        try:
            while page.pop_dialog() is not None:
                pass
        except Exception:
            pass

        # gets current url/page:
        route = page.route or "/"
        signed_in = bool((page.data or {}).get("user")) # checks whether user is logged in.

        if route in ("/", "") or not signed_in:
            page.controls.append(signin_view(page)) # stays in sign-in page.
        else:
            entry = ROUTES.get(route)
            if entry is None:
                page.route = "/dashboard"
                entry = ROUTES["/dashboard"]
            active, builder = entry # active = "dashboard"
                                    # builder = dashboard_view
            page.controls.append(shell(page, active, builder(page))) # builds UI. 
        page.update() # refreshes/redraws UI.


    page.data["refresh"] = render # so any page can refresh the whole app.

    # call render when route or size changes. like responsive. if window resized, it calls render.
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
    ft.app(target=main, assets_dir="assets")
