"""Sign In screen — split layout with stylized warehouse illustration on the left."""
from __future__ import annotations

from pathlib import Path

import flet as ft
import flet.canvas as cv

import db
from theme import Colors
from components.dialogs import show_snack, form_dialog


# left side picture:
ILLUSTRATION_PATH = Path(__file__).parent.parent / "assets" / "warehouse.png"


def _build_illustration() -> ft.Container:
    """Use assets/warehouse.png if present, otherwise fall back to the canvas art."""
    if ILLUSTRATION_PATH.exists():
        return ft.Container(
            expand=True,
            bgcolor="#0B1A4A",
            image=ft.DecorationImage(
                src="warehouse.png",      # relative to assets/
                fit=ft.BoxFit.COVER,      # fill the panel; crop overflow
            ),
        )
    return _canvas_illustration()


def _canvas_illustration() -> ft.Container:
    rack_color = "#5EEAD4"      # mint accents
    rack_dark = "#1E3A8A"
    label_style = ft.TextStyle(size=11, weight=ft.FontWeight.W_500,
                               color="#A5F3FC")

    shapes = []

    # Floor grid (diagonal isometric squares)
    grid_step = 60
    for i in range(-10, 30):
        # Down-right diagonals
        shapes.append(cv.Line(
            x1=i * grid_step, y1=0, x2=i * grid_step + 800, y2=800,
            paint=ft.Paint(color="#1E40AF40", stroke_width=1),
        ))
        # Down-left diagonals
        shapes.append(cv.Line(
            x1=i * grid_step, y1=0, x2=i * grid_step - 800, y2=800,
            paint=ft.Paint(color="#1E40AF40", stroke_width=1),
        ))

    def rack(cx, cy, w=70, h=110):
        # Vertical rack as 3 stacked boxes seen in perspective
        for j in range(3):
            top = cy - h + j * (h / 3)
            shapes.append(cv.Rect(
                x=cx - w / 2, y=top, width=w, height=h / 3 - 4,
                border_radius=2,
                paint=ft.Paint(color=rack_dark),
            ))
            shapes.append(cv.Rect(
                x=cx - w / 2, y=top, width=w, height=h / 3 - 4,
                border_radius=2,
                paint=ft.Paint(
                    color=rack_color,
                    style=ft.PaintingStyle.STROKE,
                    stroke_width=1.2,
                ),
            ))

    # Two clusters of racks, left-top and right-bottom
    for col in range(3):
        for row in range(2):
            rack(80 + col * 90, 200 + row * 130)
    for col in range(3):
        for row in range(2):
            rack(540 + col * 90, 480 + row * 130)

    # Central glowing core
    shapes.append(cv.Circle(
        x=380, y=370, radius=110,
        paint=ft.Paint(
            color="#22D3EE40",
            style=ft.PaintingStyle.FILL,
        ),
    ))
    shapes.append(cv.Rect(
        x=320, y=340, width=130, height=70, border_radius=8,
        paint=ft.Paint(color="#0EA5E9"),
    ))
    shapes.append(cv.Rect(
        x=320, y=340, width=130, height=70, border_radius=8,
        paint=ft.Paint(color="#67E8F9", style=ft.PaintingStyle.STROKE,
                       stroke_width=2),
    ))
    shapes.append(cv.Text(
        x=385, y=375, value="FleetOps", style=ft.TextStyle(
            size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF",
        ),
        alignment=ft.Alignment.CENTER,
    ))
    shapes.append(cv.Text(
        x=385, y=393, value="Core", style=ft.TextStyle(
            size=11, color="#BAE6FD",
        ),
        alignment=ft.Alignment.CENTER,
    ))

    # Light beams from the core to the racks
    for tx, ty in [(180, 250), (180, 380), (600, 530), (600, 660)]:
        shapes.append(cv.Line(
            x1=380, y1=370, x2=tx, y2=ty,
            paint=ft.Paint(color="#22D3EE80", stroke_width=2),
        ))

    # Annotations
    for cx, cy, label in [
        (160, 130, "Active Charging Zones"),
        (640, 140, "Active Charging Zones"),
        (640, 340, "FleetOps Core"),
        (220, 720, "Active Charging Zones"),
    ]:
        shapes.append(cv.Rect(
            x=cx - 80, y=cy - 12, width=160, height=22, border_radius=4,
            paint=ft.Paint(color="#0F172A80"),
        ))
        shapes.append(cv.Text(
            x=cx, y=cy, value=label, style=label_style,
            alignment=ft.Alignment.CENTER,
        ))

    canvas = cv.Canvas(shapes=shapes, expand=True)

    return ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#0B1A4A", "#1E3A8A", "#312E81"],
        ),
        content=ft.Stack(controls=[canvas]),
    )


# login card (right side):
def _portal_card() -> ft.Container:
    return ft.Container(
        bgcolor=Colors.PRIMARY_SOFT,
        border=ft.Border.all(1, Colors.PRIMARY_BORDER),
        border_radius=10,
        padding=16,
        content=ft.Column(spacing=10, controls=[
            ft.Text("ACTIVE PORTAL", size=11, weight=ft.FontWeight.W_700,
                    color=Colors.PRIMARY),
            ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=40, height=40,
                        bgcolor=Colors.PRIMARY,
                        border_radius=999,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.SHIELD, color="#FFFFFF", size=20),
                    ),
                    ft.Column(spacing=2, controls=[
                        ft.Text("Fleet Manager", size=15, weight=ft.FontWeight.BOLD,
                                color=Colors.TEXT),
                        ft.Text("Full warehouse administrative access",
                                size=12, italic=True, color=Colors.TEXT_MUTED),
                    ]),
                ],
            ),
        ]),
    )


def _input_field(value: str, icon, password: bool = False) -> ft.TextField:
    return ft.TextField(
        value=value,
        prefix_icon=icon, # icon at the start of the input field.
        password=password,
        can_reveal_password=password, # show/hide password toggle.
        bgcolor=Colors.SURFACE,
        border_color=Colors.BORDER,
        focused_border_color=Colors.PRIMARY,
        border_radius=10,
        height=48,
        text_size=14,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
    )


def labeled(label: str, field: ft.Control,
            trailing: ft.Control | None = None) -> ft.Column:
    return ft.Column(spacing=8, controls=[
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text(label, size=13, weight=ft.FontWeight.W_600,
                        color=Colors.TEXT),
                *([trailing] if trailing else []),
            ],
        ),
        field,
    ])


def signin_view(page: ft.Page) -> ft.Control:
    width = page.width or 1280
    is_narrow = width < 900
    is_register = [False] # use list for mutable closure

    name_field = _input_field("", ft.Icons.PERSON_OUTLINE)
    email_field = _input_field("admin@fleetops.logistics", ft.Icons.MAIL_OUTLINE)
    password_field = _input_field("fleetops", ft.Icons.LOCK_OUTLINE, password=True)
    remember_box = ft.Checkbox(value=False, fill_color=Colors.PRIMARY)

    title_text = ft.Text("Sign In", size=30, weight=ft.FontWeight.BOLD, color=Colors.TEXT)
    subtitle_text = ft.Text("Enter your credentials to access the fleet control system.", size=13, color=Colors.TEXT_MUTED)
    submit_btn_text = ft.Text("Access Dashboard", size=14, weight=ft.FontWeight.W_600, color="#FFFFFF")
    
    toggle_text = ft.Text("Don't have an account?", size=13, color=Colors.TEXT_MUTED)
    toggle_link = ft.TextButton("Sign Up", style=ft.ButtonStyle(color=Colors.PRIMARY), on_click=lambda _: switch_mode())

    name_container = ft.Column(visible=False, controls=[labeled("Full Name", name_field)])

    def switch_mode():
        is_register[0] = not is_register[0]
        if is_register[0]:
            title_text.value = "Create Account"
            subtitle_text.value = "Join the FleetOps network to monitor warehouse operations."
            submit_btn_text.value = "Register Account"
            toggle_text.value = "Already have an account?"
            toggle_link.text = "Sign In"
            name_container.visible = True
            email_field.value = ""
            password_field.value = ""
        else:
            title_text.value = "Sign In"
            subtitle_text.value = "Enter your credentials to access the fleet control system."
            submit_btn_text.value = "Access Dashboard"
            toggle_text.value = "Don't have an account?"
            toggle_link.text = "Sign Up"
            name_container.visible = False
            email_field.value = "admin@fleetops.logistics"
            password_field.value = "fleetops"
        page.update()

    def handle_submit(_):
        if is_register[0]:
            attempt_register()
        else:
            attempt_login()

    def attempt_register():
        name = (name_field.value or "").strip()
        email = (email_field.value or "").strip()
        pw = password_field.value or ""
        if not name or not email or not pw:
            show_snack(page, "All fields are required.", kind="warning")
            return
        
        success = db.register_user(email, pw, name, role="user") # New users are 'user' role
        if success:
            show_snack(page, "Registration successful! Please sign in.", kind="success")
            switch_mode()
        else:
            show_snack(page, "Email already registered.", kind="error")

    def attempt_login():
        email = (email_field.value or "").strip()
        pw = password_field.value or ""
        if not email or not pw:
            show_snack(page, "Email and password are required.", kind="warning")
            return
        user = db.authenticate(email, pw)
        if not user:
            show_snack(page, "Invalid credentials.", kind="error")
            return
        page.data["user"] = user
        show_snack(page, f"Welcome back, {user['name']}.", kind="success")
        target = page.route if page.route and page.route != "/" else "/dashboard"
        if target != page.route:
            page.go(target)
        else:
            refresh = (page.data or {}).get("refresh")
            if callable(refresh):
                refresh()

    def open_forgot(_):
        def submit(values: dict):
            email = (values.get("email") or "").strip()
            if not email or "@" not in email:
                show_snack(page, "Enter a valid work email.", kind="warning")
                return
            # Minimal check for demo:
            if email == "admin@fleetops.logistics":
                 show_snack(page, "Reset link queued for admin@fleetops.logistics.", kind="success")
            else:
                 show_snack(page, f"No account found for {email}.", kind="error")
        form_dialog(page, "Reset Password",
                    fields=[("email", "Work email", email_field.value or "")],
                    submit_label="Send Reset Link",
                    on_submit=submit)

    forgot = ft.TextButton(
        "Forgot Password?",
        style=ft.ButtonStyle(color=Colors.PRIMARY, padding=ft.Padding.all(0)),
        on_click=open_forgot,
    )

    form = ft.Container(
        width=420 if not is_narrow else None,
        padding=ft.Padding.symmetric(horizontal=32, vertical=40),
        content=ft.Column(
            spacing=22,
            controls=[
                ft.Column(spacing=6, controls=[title_text, subtitle_text]),
                _portal_card(),
                name_container,
                labeled("Work Email", email_field),
                labeled("Security Password", password_field, trailing=forgot),
                ft.Row(spacing=8, controls=[
                    remember_box,
                    ft.Text("Remember this workstation for 30 days",
                            size=13, color=Colors.TEXT_MUTED),
                ]),
                ft.ElevatedButton(
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            submit_btn_text,
                            ft.Icon(ft.Icons.ARROW_FORWARD, color="#FFFFFF", size=18),
                        ],
                    ),
                    height=50, width=10000, bgcolor=Colors.PRIMARY, color="#FFFFFF",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10), elevation=0),
                    on_click=handle_submit,
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[toggle_text, toggle_link]
                ),
                ft.Divider(color=Colors.BORDER_LIGHT, thickness=1, height=1),
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(spacing=6, controls=[
                            ft.Icon(ft.Icons.PUBLIC, size=14, color=Colors.TEXT_MUTED),
                            ft.Text("System: ", size=12, color=Colors.TEXT_MUTED),
                            ft.Text("US-EAST-1 (Active)", size=12,
                                    weight=ft.FontWeight.W_600, color=Colors.TEXT),
                        ]),
                        ft.Row(spacing=10, controls=[
                            ft.Row(spacing=4, controls=[
                                ft.Icon(ft.Icons.HELP_OUTLINE, size=14,
                                        color=Colors.TEXT_MUTED),
                                ft.Text("Support", size=12, color=Colors.TEXT_MUTED),
                            ]),
                            ft.Container(width=2, height=2, bgcolor=Colors.TEXT_FAINT,
                                         border_radius=999),
                            ft.Text("Privacy", size=12, color=Colors.TEXT_MUTED),
                        ]),
                    ],
                ),
            ],
        ),
    )

    if is_narrow:
        return ft.Container(
            expand=True,
            bgcolor=Colors.SURFACE,
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Container(height=180, content=_build_illustration()),
                    form,
                ],
            ),
        )

    return ft.Row(
        expand=True,
        spacing=0,
        controls=[
            ft.Container(expand=1, content=_build_illustration()),
            ft.Container(
                expand=1,
                bgcolor=Colors.SURFACE,
                alignment=ft.Alignment.CENTER,
                content=form,
            ),
        ],
    )
