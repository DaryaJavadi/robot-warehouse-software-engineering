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

# Valid dropdown choices:
STATUS_OPTIONS  = ["Working", "Ready", "Idle", "Maintenance", "Active"]
SIGNAL_OPTIONS  = ["Excellent", "Good", "Fair", "Poor", "Offline"]


# Helpers:

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


# main view builder:

def add_robot_view(page: ft.Page) -> ft.Control:
    """Robot Management View with Table and Form."""

    # State:
    editing_id = [None]  # Using a list for mutable closure access
    current_page = [1]
    total_pages = [1]
    PAGE_SIZE = 10

    # Form Controls:
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
    
    # Table Controls:
    table = ft.DataTable(
        column_spacing=16,
        heading_row_color=Colors.PRIMARY_SOFT,
        columns=[
            ft.DataColumn(ft.Text("ID",     size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Model",  size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Serial", size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Status", size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Zone",   size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Battery",size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Maint",  size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Temp",   size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Signal", size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
            ft.DataColumn(ft.Text("Actions",size=12, weight=ft.FontWeight.W_700, color=Colors.PRIMARY)),
        ],
        rows=[],
    )
    status_text = ft.Text("Initializing...", size=12, color=Colors.TEXT_MUTED)

    # Search Field & Sorting & Paging:
    search_field = ft.TextField(
        label="Search by ID, Model, Zone, Status...",
        width=280,
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda e: go_to_page(1), # Reset to page 1 on new search
    )

    sort_dropdown = ft.Dropdown(
        label="Sort by",
        width=160,
        value="id",
        border_color=Colors.BORDER,
        focused_border_color=Colors.PRIMARY,
        border_radius=10,
        text_size=14,
        label_style=ft.TextStyle(color=Colors.TEXT_MUTED, size=13),
        options=[
            ft.dropdown.Option("id", "ID"),
            ft.dropdown.Option("model", "Model"),
            ft.dropdown.Option("status", "Status"),
            ft.dropdown.Option("battery", "Battery"),
            ft.dropdown.Option("zone", "Zone"),
            ft.dropdown.Option("temperature", "Temperature"),
            ft.dropdown.Option("signal", "Signal"),
        ],
    )
    sort_dropdown.on_change = lambda e: load_robots()

    order_dropdown = ft.Dropdown(
        label="Order",
        width=170,
        value="asc",
        border_color=Colors.BORDER,
        focused_border_color=Colors.PRIMARY,
        border_radius=10,
        text_size=14,
        label_style=ft.TextStyle(color=Colors.TEXT_MUTED, size=13),
        options=[
            ft.dropdown.Option("asc", "↑ Ascending"),
            ft.dropdown.Option("desc", "↓ Descending"),
        ],
    )
    order_dropdown.on_change = lambda e: load_robots()

    counter_text = ft.Text("", size=13, color=Colors.TEXT_MUTED)

    pager_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER)

    def go_to_page(n: int):
        current_page[0] = n
        load_robots()

    def _page_btn(p: int, current: int):
        """Return a styled button for page p; highlighted if p == current."""
        return ft.ElevatedButton(
            str(p),
            bgcolor=Colors.PRIMARY if p == current else Colors.SURFACE,
            color=Colors.SURFACE if p == current else Colors.TEXT,
            width=40,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.all(0),
            ),
            on_click=lambda e, pg=p: go_to_page(pg),
        )

    def rebuild_pager():
        pager_row.controls.clear()
        tp = total_pages[0]
        cp = current_page[0]
        # ─ Previous button
        pager_row.controls.append(
            ft.IconButton(
                ft.Icons.CHEVRON_LEFT,
                tooltip="Previous",
                disabled=(cp == 1),
                on_click=lambda e: go_to_page(cp - 1),
            )
        )
        # ─ Page number buttons (show at most 7 pages)
        start_p = max(1, cp - 3)
        end_p = min(tp, start_p + 6)
        if start_p > 1:
            pager_row.controls.append(_page_btn(1, cp))
            if start_p > 2:
                pager_row.controls.append(ft.Text("…", size=16, color=Colors.TEXT_MUTED))
        for p in range(start_p, end_p + 1):
            pager_row.controls.append(_page_btn(p, cp))
        if end_p < tp:
            if end_p < tp - 1:
                pager_row.controls.append(ft.Text("…", size=16, color=Colors.TEXT_MUTED))
            pager_row.controls.append(_page_btn(tp, cp))
        # ─ Next button
        pager_row.controls.append(
            ft.IconButton(
                ft.Icons.CHEVRON_RIGHT,
                tooltip="Next",
                disabled=(cp == tp),
                on_click=lambda e: go_to_page(cp + 1),
            )
        )

    # Edit Dialog Fields:
    dlg_id      = ft.TextField(label="Robot ID", read_only=True)
    dlg_model   = _field("Model")
    dlg_serial  = _field("Serial No.")
    dlg_zone    = _field("Zone")
    dlg_maint   = _field("Last Maintenance")
    dlg_temp    = _field("Temperature (°C)")
    dlg_status  = _dropdown("Status", STATUS_OPTIONS)
    dlg_signal  = _dropdown("Signal", SIGNAL_OPTIONS)
    
    dlg_battery_label = ft.Text("Battery: 80%", size=13, color=Colors.TEXT_MUTED)
    dlg_battery_slider = ft.Slider(
        min=0, max=100, value=80, divisions=20,
        active_color=Colors.PRIMARY,
        on_change=lambda e: (setattr(dlg_battery_label, "value", f"Battery: {int(e.control.value)}%"), page.update()),
    )

    def close_dialog(_):
        edit_dialog.open = False
        page.update()

    def save_edit(_):
        # Validate temperature field:
        temp_val = 32.0
        temp_raw = (dlg_temp.value or "").strip()
        if temp_raw:
            try:
                temp_val = float(temp_raw)
            except ValueError:
                show_snack(page, f"Invalid temperature value: '{temp_raw}'. Please enter a valid number.", kind="error")
                return

        payload = {
            "id": dlg_id.value,
            "model": dlg_model.value.strip(),
            "serial": dlg_serial.value.strip(),
            "status": dlg_status.value,
            "zone": dlg_zone.value.strip(),
            "battery": round(dlg_battery_slider.value / 100, 2),
            "last_maintenance": dlg_maint.value.strip(),
            "temperature": temp_val,
            "signal": dlg_signal.value or "Excellent",
        }
        
        try:
            print(f">>> Flet: Requesting PUT /robots/{dlg_id.value}")
            resp = requests.put(f"{API_URL}/robots/{dlg_id.value}", json=payload, timeout=5)
            if resp.status_code == 200:
                show_snack(page, f"✓ Robot {dlg_id.value} updated successfully!", kind="success")
                edit_dialog.open = False
                load_robots()
            else:
                show_snack(page, f"Update failed: {resp.text}", kind="error")
        except Exception as ex:
            show_snack(page, f"Error: {ex}", kind="error")
        page.update()

    edit_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Robot Record"),
        content=ft.Container(
            width=400,
            content=ft.Column([
                dlg_id, dlg_model, dlg_serial, dlg_zone,
                ft.Row([dlg_status, dlg_signal]),
                dlg_maint, dlg_temp,
                ft.Column([dlg_battery_label, dlg_battery_slider]),
            ], tight=True, scroll=ft.ScrollMode.AUTO)
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.ElevatedButton("Save Changes", bgcolor=Colors.PRIMARY, color="#FFFFFF", on_click=save_edit),
        ],
    )
    page.overlay.append(edit_dialog)

    def open_edit_dialog(robot: dict):
        dlg_id.value = robot["id"]
        dlg_model.value = robot["model"]
        dlg_serial.value = robot["serial"]
        dlg_zone.value = robot["zone"]
        dlg_maint.value = robot["last_maintenance"]
        dlg_temp.value = str(robot.get("temperature", 32.0))
        dlg_status.value = robot["status"]
        dlg_signal.value = robot.get("signal", "Excellent")
        dlg_battery_slider.value = robot["battery"] * 100
        dlg_battery_label.value = f"Battery: {int(dlg_battery_slider.value)}%"
        
        edit_dialog.open = True
        page.update()

    # Navigation logic:
    user_role = (page.data.get("user") or {}).get("role", "user")
    
    tabs = [
        ft.NavigationBarDestination(icon=ft.Icons.LIST_ALT_OUTLINED, selected_icon=ft.Icons.LIST_ALT, label="Records"),
    ]
    if user_role == "manager":
        tabs.append(
            ft.NavigationBarDestination(icon=ft.Icons.ADD_BOX_OUTLINED, selected_icon=ft.Icons.ADD_BOX, label="Add/Edit")
        )

    nav = ft.NavigationBar(
        selected_index=0,
        bgcolor=Colors.SURFACE,
        indicator_color=Colors.PRIMARY_SOFT,
        destinations=tabs,
    )

    def switch_to_tab(idx: int):
        if user_role != "manager" and idx != 0:
            nav.selected_index = 0
            page.update()
            return
        nav.selected_index = idx
        records_panel.visible = (idx == 0)
        form_panel.visible    = (idx == 1)
        page.update()

    # API Operations:

    def load_robots():
        search_text = search_field.value or ""
        offset = (current_page[0] - 1) * PAGE_SIZE
        sort_by = sort_dropdown.value or "id"
        order = order_dropdown.value or "asc"
        
        print(f">>> Flet: Requesting GET /robots (offset={offset}, limit={PAGE_SIZE}, search='{search_text}', sort_by='{sort_by}', order='{order}')")
        refresh_btn.disabled = True
        refresh_btn.content.controls[0].visible = True # Show ProgressRing
        status_text.value = "Fetching data..."
        status_text.color = Colors.TEXT_MUTED
        page.update()

        max_retries = 3
        retry_delay = 1.5 # seconds
        
        for attempt in range(max_retries):
            try:
                params = {
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "search": search_text,
                    "sort_by": sort_by,
                    "order": order
                }
                resp = requests.get(f"{API_URL}/robots", params=params, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                
                total = data["total"]
                robots = data["items"]
                print(f"--- Flet: Received {len(robots)} of {total} robots")
                
                import math
                total_pages[0] = max(1, math.ceil(total / PAGE_SIZE))
                
                # clamp current page
                if current_page[0] > total_pages[0]:
                    current_page[0] = total_pages[0]
                
                # counter label
                start = offset + 1 if total > 0 else 0
                end = min(offset + PAGE_SIZE, total)
                counter_text.value = f"Showing {start}–{end} of {total} records"
                
                # Role-based restriction:
                user_role = (page.data.get("user") or {}).get("role", "user")
                
                table.rows.clear()
                for r in robots:
                    rid = r["id"]
                    batt_pct = f"{int(r['battery'] * 100)}%"
                    
                    # Only show actions for managers:
                    action_row = ft.Row(spacing=0)
                    if user_role == "manager":
                        action_row.controls.extend([
                            ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=18, 
                                          icon_color=Colors.PRIMARY, tooltip="Edit",
                                          on_click=lambda _, _r=r: open_edit_dialog(_r)),
                            ft.IconButton(ft.Icons.DELETE_OUTLINED, icon_size=18, 
                                          icon_color=Colors.DANGER, tooltip="Delete",
                                          on_click=lambda _, _id=rid: delete_robot(_id)),
                        ])
                    else:
                        action_row.controls.append(
                            ft.Text("View Only", size=11, color=Colors.TEXT_MUTED, italic=True)
                        )

                    table.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(rid, weight=ft.FontWeight.BOLD, color=Colors.PRIMARY)),
                            ft.DataCell(ft.Text(r["model"])),
                            ft.DataCell(ft.Text(r["serial"])),
                            ft.DataCell(ft.Text(r["status"])),
                            ft.DataCell(ft.Text(r["zone"])),
                            ft.DataCell(ft.Text(batt_pct)),
                            ft.DataCell(ft.Text(r["last_maintenance"])),
                            ft.DataCell(ft.Text(f"{r['temperature']}°C")),
                            ft.DataCell(ft.Text(r["signal"])),
                            ft.DataCell(action_row),
                        ])
                    )
                status_text.value = f"Success: {total} robot(s) total"
                status_text.color = Colors.SUCCESS
                rebuild_pager()
                break # Exit retry loop on success
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    print(f"--- Flet: API connection attempt {attempt + 1} failed, retrying...")
                    status_text.value = f"API starting up... (Attempt {attempt + 1}/{max_retries})"
                    page.update()
                    time.sleep(retry_delay)
                else:
                    print(f"!!! Flet: GET /robots failed after {max_retries} attempts - {e}")
                    status_text.value = "Error: API server not responding."
                    status_text.color = Colors.DANGER
            except Exception as e:
                print(f"!!! Flet: Unexpected error - {e}")
                status_text.value = f"Error: {e}"
                status_text.color = Colors.DANGER
                break
        
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
        # Validate temperature field:
        temp_val = 32.0
        temp_raw = (f_temp.value or "").strip()
        if temp_raw:
            try:
                temp_val = float(temp_raw)
            except ValueError:
                show_snack(page, f"Invalid temperature value: '{temp_raw}'. Please enter a valid number.", kind="error")
                return

        payload = {
            "id": f_id.value.strip(),
            "model": f_model.value.strip(),
            "serial": f_serial.value.strip(),
            "status": dd_status.value,
            "zone": f_zone.value.strip(),
            "battery": round(battery_slider.value / 100, 2),
            "last_maintenance": f_maint.value.strip(),
            "temperature": temp_val,
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
                action = "updated" if editing_id[0] else "registered"
                show_snack(page, f"✓ Robot {payload['id']} {action} successfully!", kind="success")
                clear_form()
                switch_to_tab(0)
                load_robots()
            else:
                show_snack(page, f"Error: {resp.json().get('detail', resp.text)}", kind="error")
        except Exception as e:
            show_snack(page, f"Request failed: {e}", kind="error")

    # UI Layout:

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
            ft.Row([search_field, sort_dropdown, order_dropdown], wrap=True, alignment=ft.MainAxisAlignment.START, spacing=10),
            ft.Row([counter_text, status_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                bgcolor=Colors.SURFACE, border_radius=12, border=ft.Border.all(1, Colors.BORDER),
                content=ft.Column([ft.Row([table], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO),
            ),
            ft.Container(height=10),
            pager_row,
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

    # Initial Load:
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
