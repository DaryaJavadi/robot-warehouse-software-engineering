"""Add Robot view — form that POSTs to the FastAPI server.

Navigation:
  Tab 0 → live robots table  (GET /robots)
  Tab 1 → registration form  (POST /robots)

Features:
  - Auto-load on entry
  - Edit and Delete functionality
  - Visual loading states
  - Terminal logging
"""
from __future__ import annotations

import threading
import time
import requests
import flet as ft

from theme import Colors
from components.dialogs import show_snack, confirm

API_URL = "http://127.0.0.1:8000"

# ── valid dropdown choices (must match api.py validators) ─────────────────────
STATUS_OPTIONS  = ["Working", "Ready", "Idle", "Maintenance", "Active"]
SIGNAL_OPTIONS  = ["Excellent", "Good", "Fair", "Poor", "Offline"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _field(label: str, hint: str = "") -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=hint,
        border_color=Colors.BORDER,
        focused_border_color=Colors.PRIMARY,
        border_radius=10,
        text_size=14,
        label_style=ft.TextStyle(color=Colors.TEXT_MUTED, size=13),
    )


def _dropdown(label: str, options: list[str]) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        options=[ft.dropdown.Option(o) for o in options],
        border_color=Colors.BORDER,
        focused_border_color=Colors.PRIMARY,
        border_radius=10,
        text_size=14,
        label_style=ft.TextStyle(color=Colors.TEXT_MUTED, size=13),
    )


def _section_header(title: str, subtitle: str) -> ft.Control:
    return ft.Column(
        spacing=4,
        controls=[
            ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color=Colors.TEXT),
            ft.Text(subtitle, size=13, color=Colors.TEXT_MUTED),
        ],
    )


# ── main view builder ─────────────────────────────────────────────────────────

def add_robot_view(page: ft.Page) -> ft.Control:
    """Robot Management View with Table and Form."""

    # ── State ─────────────────────────────────────────────────────────────────
    editing_id = [None]  # Using a list for mutable closure access

    # ── Form Controls ─────────────────────────────────────────────────────────
    f_id    = _field("Robot ID *",   "e.g. RX-900")
    f_model = _field("Model *",      "e.g. Titan-X Cargo Lifter")
    f_serial= _field("Serial No. *", "e.g. TX-9000-AA")
    f_zone  = _field("Warehouse Zone *", "e.g. Loading A-1")
    f_maint = _field("Last Maintenance *", "e.g. 1d ago")
    f_temp  = _field("Temperature (°C)", "Default: 32")

    dd_status = _dropdown("Status *", STATUS_OPTIONS)
    dd_signal = _dropdown("Signal Strength *", SIGNAL_OPTIONS)

    battery_label  = ft.Text("Battery: 80%", size=13, color=Colors.TEXT_MUTED)
    battery_slider = ft.Slider(
        min=0, max=100, value=80, divisions=20,
        active_color=Colors.PRIMARY,
        on_change=lambda e: (setattr(battery_label, "value", f"Battery: {int(e.control.value)}%"), page.update()),
    )

    submit_btn_text = ft.Text("Register Robot", size=14, weight=ft.FontWeight.W_600, color="#FFFFFF")
    
    # ── Table Controls ────────────────────────────────────────────────────────
    table = ft.DataTable(
        column_spacing=24,
        heading_row_color=Colors.PRIMARY_SOFT,
        columns=[
            ft.DataColumn(ft.Text("ID",     size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Model",  size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Status", size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Battery",size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Actions",size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
        ],
        rows=[],
    )
    status_text = ft.Text("Initializing...", size=12, color=Colors.TEXT_MUTED)

    # ── Navigation logic ──────────────────────────────────────────────────────
    nav = ft.NavigationBar(
        selected_index=0,
        bgcolor=Colors.SURFACE,
        indicator_color=Colors.PRIMARY_SOFT,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.LIST_ALT_OUTLINED, selected_icon=ft.Icons.LIST_ALT, label="Records"),
            ft.NavigationBarDestination(icon=ft.Icons.ADD_BOX_OUTLINED, selected_icon=ft.Icons.ADD_BOX, label="Add/Edit"),
        ],
    )

    def switch_to_tab(idx: int):
        nav.selected_index = idx
        records_panel.visible = (idx == 0)
        form_panel.visible    = (idx == 1)
        page.update()

    # ── API Operations ────────────────────────────────────────────────────────

    def load_robots():
        print(">>> Flet: Requesting GET /robots")
        refresh_btn.disabled = True
        refresh_btn.content.controls[0].visible = True # Show ProgressRing
        status_text.value = "Fetching data..."
        page.update()

        try:
            resp = requests.get(f"{API_URL}/robots", timeout=5)
            resp.raise_for_status()
            robots = resp.json()
            print(f"--- Flet: Received {len(robots)} robots")
            
            table.rows.clear()
            for r in robots:
                rid = r["id"]
                batt_pct = f"{int(r['battery'] * 100)}%"
                table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(rid, weight=ft.FontWeight.BOLD, color=Colors.PRIMARY)),
                        ft.DataCell(ft.Text(r["model"])),
                        ft.DataCell(ft.Text(r["status"])),
                        ft.DataCell(ft.Text(batt_pct)),
                        ft.DataCell(
                            ft.Row([
                                ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=18, 
                                              icon_color=Colors.PRIMARY, tooltip="Edit",
                                              on_click=lambda _, _r=r: start_edit(_r)),
                                ft.IconButton(ft.Icons.DELETE_OUTLINED, icon_size=18, 
                                              icon_color=Colors.DANGER, tooltip="Delete",
                                              on_click=lambda _, _id=rid: delete_robot(_id)),
                            ], spacing=0)
                        ),
                    ])
                )
            status_text.value = f"Success: {len(robots)} robot(s) loaded"
            status_text.color = Colors.SUCCESS
        except Exception as e:
            print(f"!!! Flet: GET /robots failed - {e}")
            status_text.value = f"Error: {e}"
            status_text.color = Colors.DANGER
        finally:
            refresh_btn.disabled = False
            refresh_btn.content.controls[0].visible = False
            page.update()

    def delete_robot(robot_id: str):
        def on_confirmed():
            print(f">>> Flet: Requesting DELETE /robots/{robot_id}")
            try:
                resp = requests.delete(f"{API_URL}/robots/{robot_id}", timeout=5)
                if resp.status_code == 200:
                    show_snack(page, f"Robot {robot_id} deleted.", kind="success")
                    load_robots()
                else:
                    show_snack(page, f"Delete failed: {resp.text}", kind="error")
            except Exception as e:
                show_snack(page, f"Connection error: {e}", kind="error")

        confirm(page, "Delete Robot?", f"Are you sure you want to remove {robot_id}?", 
                on_confirm=on_confirmed, confirm_label="Delete")

    def start_edit(robot: dict):
        editing_id[0] = robot["id"]
        f_id.value = robot["id"]
        f_id.disabled = True # Cannot change ID during edit
        f_model.value = robot["model"]
        f_serial.value = robot["serial"]
        f_zone.value = robot["zone"]
        f_maint.value = robot["last_maintenance"]
        f_temp.value = str(robot.get("temperature", 32.0))
        dd_status.value = robot["status"]
        dd_signal.value = robot.get("signal", "Excellent")
        battery_slider.value = robot["battery"] * 100
        battery_label.value = f"Battery: {int(battery_slider.value)}%"
        
        submit_btn_text.value = "Update Robot"
        switch_to_tab(1)

    def clear_form():
        editing_id[0] = None
        f_id.value = ""
        f_id.disabled = False
        f_model.value = ""
        f_serial.value = ""
        f_zone.value = ""
        f_maint.value = ""
        f_temp.value = ""
        dd_status.value = None
        dd_signal.value = None
        battery_slider.value = 80
        battery_label.value = "Battery: 80%"
        submit_btn_text.value = "Register Robot"

    def submit_form(_):
        payload = {
            "id": f_id.value.strip(),
            "model": f_model.value.strip(),
            "serial": f_serial.value.strip(),
            "status": dd_status.value,
            "zone": f_zone.value.strip(),
            "battery": round(battery_slider.value / 100, 2),
            "last_maintenance": f_maint.value.strip(),
            "temperature": float(f_temp.value.strip()) if f_temp.value.strip() else 32.0,
            "signal": dd_signal.value or "Excellent",
        }
        
        if not all([payload["id"], payload["model"], payload["status"]]):
            show_snack(page, "Please fill required fields.", kind="warning")
            return

        try:
            if editing_id[0]:
                print(f">>> Flet: Requesting PUT /robots/{editing_id[0]}")
                resp = requests.put(f"{API_URL}/robots/{editing_id[0]}", json=payload, timeout=5)
            else:
                print(">>> Flet: Requesting POST /robots")
                resp = requests.post(f"{API_URL}/robots", json=payload, timeout=5)
            
            if resp.status_code in (200, 201):
                show_snack(page, "Success!", kind="success")
                clear_form()
                switch_to_tab(0)
                load_robots()
            else:
                show_snack(page, f"Error: {resp.json().get('detail', resp.text)}", kind="error")
        except Exception as e:
            show_snack(page, f"Request failed: {e}", kind="error")

    # ── UI Layout ─────────────────────────────────────────────────────────────

    refresh_btn = ft.FilledButton(
        content=ft.Row([
            ft.ProgressRing(width=14, height=14, stroke_width=2, color="#FFFFFF", visible=False),
            ft.Icon(ft.Icons.REFRESH, size=18),
            ft.Text("Refresh"),
        ], spacing=8, tight=True),
        on_click=lambda _: load_robots(),
    )

    records_panel = ft.Column(
        visible=True, expand=True, spacing=16,
        controls=[
            ft.Row([_section_header("Robot Fleet", "Manage warehouse robots via API"), refresh_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            status_text,
            ft.Container(
                bgcolor=Colors.SURFACE, border_radius=12, border=ft.Border.all(1, Colors.BORDER),
                content=ft.Column([ft.Row([table], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO),
            )
        ]
    )

    form_panel = ft.Column(
        visible=False, expand=True, spacing=16,
        controls=[
            _section_header("Robot Details", "Add or modify robot information"),
            ft.Container(
                bgcolor=Colors.SURFACE, border_radius=14, border=ft.Border.all(1, Colors.BORDER), padding=24,
                content=ft.Column([
                    ft.ResponsiveRow([ft.Container(f_id, col=6), ft.Container(f_model, col=6)]),
                    ft.ResponsiveRow([ft.Container(f_serial, col=6), ft.Container(f_zone, col=6)]),
                    ft.ResponsiveRow([ft.Container(dd_status, col=6), ft.Container(dd_signal, col=6)]),
                    ft.ResponsiveRow([ft.Container(f_maint, col=6), ft.Container(f_temp, col=6)]),
                    ft.Column([battery_label, battery_slider]),
                    ft.Row([
                        ft.FilledButton(content=submit_btn_text, on_click=submit_form),
                        ft.TextButton("Cancel / Clear", on_click=lambda _: clear_form()),
                    ]),
                ], spacing=16)
            )
        ]
    )

    nav.on_change = lambda e: switch_to_tab(e.control.selected_index)

    # ── Initial Load ──────────────────────────────────────────────────────────
    def initial_load():
        time.sleep(0.3)
        load_robots()
    
    threading.Thread(target=initial_load, daemon=True).start()

    return ft.Column(
        expand=True, spacing=0,
        controls=[
            ft.Container(
                bgcolor=Colors.SURFACE, padding=20, border=ft.Border.all(1, Colors.BORDER), border_radius=12,
                content=ft.Row([
                    ft.Icon(ft.Icons.SMART_TOY, color=Colors.PRIMARY, size=30),
                    ft.Text("Robot Management System", size=20, weight="bold"),
                ])
            ),
            nav,
            ft.Container(height=20),
            ft.Stack([records_panel, form_panel], expand=True),
        ]
    )
