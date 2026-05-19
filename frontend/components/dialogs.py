"""Reusable dialogs + snackbar helpers (Flet 0.84 API).

Flet 0.84 splits dialogs and overlay snackbars into two trackers:
- `page.show_dialog(d)` / `page.pop_dialog()` — managed dialog stack
- `page.overlay.append(s)` — for SnackBars
"""
from __future__ import annotations

from typing import Callable

import flet as ft

from theme import Colors


def _open_dialog(page: ft.Page, dlg: ft.AlertDialog) -> None:
    page.show_dialog(dlg)


def _close_dialog(page: ft.Page) -> None:
    """Pop the top of the dialog stack."""
    try:
        page.pop_dialog()
    except Exception:
        pass


def show_snack(page: ft.Page, message: str, *, kind: str = "info") -> None:
    color = {
        "info": Colors.PRIMARY,
        "success": Colors.SUCCESS,
        "warning": Colors.WARNING,
        "error": Colors.DANGER,
    }.get(kind, Colors.PRIMARY)
    snack = ft.SnackBar(
        content=ft.Text(message, color="#FFFFFF", size=13,
                        weight=ft.FontWeight.W_500),
        bgcolor=color,
        behavior=ft.SnackBarBehavior.FLOATING,
        show_close_icon=True,
    )
    page.overlay.append(snack)
    snack.open = True
    page.update()


def confirm(page: ft.Page, title: str, body: str,
            on_confirm: Callable[[], None],
            confirm_label: str = "Confirm",
            danger: bool = False) -> None:
    dlg = ft.AlertDialog(modal=True)

    def close(_):
        _close_dialog(page)

    def go(_):
        _close_dialog(page)
        on_confirm()

    dlg.title = ft.Text(title, weight=ft.FontWeight.BOLD)
    dlg.content = ft.Text(body, size=13, color=Colors.TEXT_MUTED)
    dlg.actions = [
        ft.TextButton(content=ft.Text("Cancel", color=Colors.TEXT_MUTED),
                      on_click=close),
        ft.ElevatedButton(
            content=ft.Text(confirm_label, color="#FFFFFF",
                            weight=ft.FontWeight.W_600),
            bgcolor=Colors.DANGER if danger else Colors.PRIMARY,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                elevation=0,
            ),
            on_click=go,
        ),
    ]
    _open_dialog(page, dlg)


def info_dialog(page: ft.Page, title: str, body: ft.Control,
                width: int = 520,
                close_label: str = "Close") -> None:
    """Generic read-only dialog: title + arbitrary body control + Close."""
    dlg = ft.AlertDialog(modal=True)

    def close(_):
        _close_dialog(page)

    dlg.title = ft.Text(title, weight=ft.FontWeight.BOLD)
    dlg.content = ft.Container(
        width=width,
        content=ft.Column(spacing=10, tight=True,
                          scroll=ft.ScrollMode.AUTO, controls=[body]),
    )
    dlg.actions = [
        ft.ElevatedButton(
            content=ft.Text(close_label, color="#FFFFFF",
                            weight=ft.FontWeight.W_600),
            bgcolor=Colors.PRIMARY,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                elevation=0,
            ),
            on_click=close,
        ),
    ]
    _open_dialog(page, dlg)


def form_dialog(page: ft.Page, title: str, fields: list[tuple[str, str, str]],
                on_submit: Callable[[dict], None],
                submit_label: str = "Save") -> None:
    """fields: list of (key, label, default_value)."""
    inputs: dict[str, ft.TextField] = {}
    field_controls: list[ft.Control] = []
    for key, label, default in fields:
        tf = ft.TextField(
            label=label,
            value=default,
            border_color=Colors.BORDER,
            focused_border_color=Colors.PRIMARY,
            border_radius=8,
            text_size=14,
            content_padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        )
        inputs[key] = tf
        field_controls.append(tf)

    dlg = ft.AlertDialog(modal=True)

    def close(_):
        _close_dialog(page)

    def submit(_):
        values = {k: tf.value or "" for k, tf in inputs.items()}
        _close_dialog(page)
        on_submit(values)

    dlg.title = ft.Text(title, weight=ft.FontWeight.BOLD)
    dlg.content = ft.Container(
        width=420,
        content=ft.Column(spacing=12, tight=True, controls=field_controls),
    )
    dlg.actions = [
        ft.TextButton(content=ft.Text("Cancel", color=Colors.TEXT_MUTED),
                      on_click=close),
        ft.ElevatedButton(
            content=ft.Text(submit_label, color="#FFFFFF",
                            weight=ft.FontWeight.W_600),
            bgcolor=Colors.PRIMARY, color="#FFFFFF",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                elevation=0,
            ),
            on_click=submit,
        ),
    ]
    _open_dialog(page, dlg)
