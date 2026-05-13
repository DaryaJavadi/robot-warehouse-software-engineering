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
        # Preserve open snackbars so success messages stay visible after refresh
        active_snacks = [c for c in page.overlay if isinstance(c, ft.SnackBar) and c.open]
        page.overlay.clear()
        page.overlay.extend(active_snacks)
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


def start_api() -> None:
    """Starts the FastAPI server in a background process if not already running."""
    import socket
    import subprocess
    import os
    from pathlib import Path

    # Check if port 8000 is already in use
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        in_use = s.connect_ex(("127.0.0.1", 8000)) == 0

    if in_use:
        print("--- System: API already running on port 8000.")
        return

    print("--- System: Starting FastAPI server...")
    
    # Path to venv python/uvicorn
    root = Path(__file__).parent
    uvicorn_path = root / "venv" / "Scripts" / "uvicorn.exe"
    
    if not uvicorn_path.exists():
        # Fallback to system uvicorn if venv is missing
        uvicorn_path = "uvicorn"

    try:
        subprocess.Popen(
            [str(uvicorn_path), "api:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        print("--- System: API server launched in background.")
    except Exception as e:
        print(f"!!! System: Failed to start API: {e}")


if __name__ == "__main__":
    start_api()
    ft.app(target=main, assets_dir="assets")
