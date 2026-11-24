
import math
import random
import tkinter as tk
from tkinter import ttk


FIELD_WIDTH = 840
FIELD_HEIGHT = 360
FIELD_TOP = 68
PADDLE_WIDTH = 12
PADDLE_HEIGHT = 76
PADDLE_MARGIN = 22
PADDLE_SPEED = 7
BALL_RADIUS = 8
WINNING_SCORE = 5
FRAME_MS = 16

START_SPEEDS = {"Лёгкая": 5.0, "Средняя": 6.3, "Сложная": 7.6}
MAX_BALL_SPEED = 11.0
SPEED_GAIN = 0.5
MAX_BOUNCE_ANGLE = math.radians(60)
RUSSIAN_KEYS = {
    "cyrillic_tse": "w", "cyrillic_yeru": "s", "cyrillic_ka": "r",
    "ц": "w", "ы": "s", "к": "r",
}
WINDOWS_LETTER_KEYS = {0x57: "w", 0x53: "s", 0x52: "r"}

BACKGROUND = "#101621"
FIELD_COLOR = "#171f2d"
BORDER = "#344358"
TEXT = "#f1f5ff"
MUTED = "#aab9ce"
LEFT_COLOR = "#66e0cd"
RIGHT_COLOR = "#ffae91"


class GameModel:
    """Храните состояние матча и рассчитывайте движение объектов."""

    def __init__(self):
        """Подготовьте матч со средней сложностью."""
        self.reset(START_SPEEDS["Средняя"])

    def reset(self, start_speed):
        """Обнулите счёт и верните объекты в исходное положение."""
        self.start_speed = start_speed
        self.scores = [0, 0]
        self.winner = None
        self.paddle_y = [(FIELD_HEIGHT - PADDLE_HEIGHT) / 2] * 2
        self._serve(random.choice((-1, 1)))

    def _serve(self, direction):
        self.ball_x = FIELD_WIDTH / 2
        self.ball_y = FIELD_HEIGHT / 2
        self.ball_speed = self.start_speed
        angle = math.radians(random.choice((-18, 18)))
        self.ball_dx = direction * self.ball_speed * math.cos(angle)
        self.ball_dy = self.ball_speed * math.sin(angle)

    def step(self, left_direction, right_direction):
        """Продвиньте матч на один кадр с учётом движения обеих ракеток."""
        if self.winner is not None:
            return

        for player, direction in enumerate((left_direction, right_direction)):
            new_y = self.paddle_y[player] + direction * PADDLE_SPEED
            self.paddle_y[player] = min(
                FIELD_HEIGHT - PADDLE_HEIGHT, max(0, new_y)
            )

        old_x = self.ball_x
        old_y = self.ball_y
        incoming_dy = self.ball_dy
        self.ball_x += self.ball_dx
        next_y = old_y + incoming_dy
        self.ball_y = self._reflect_wall(next_y)

        if next_y <= BALL_RADIUS:
            self.ball_dy = abs(self.ball_dy)
        elif next_y >= FIELD_HEIGHT - BALL_RADIUS:
            self.ball_dy = -abs(self.ball_dy)
       
        target = 0 if self.ball_dx < 0 else 1
        self._check_paddle(target, old_x, old_y, incoming_dy)

        if self.ball_x + BALL_RADIUS <= 0:
            self._score(1, -1)
        elif self.ball_x - BALL_RADIUS >= FIELD_WIDTH:
            self._score(0, 1)

    @staticmethod
    def _reflect_wall(y):
        if y < BALL_RADIUS:
            return 2 * BALL_RADIUS - y
        lower_wall = FIELD_HEIGHT - BALL_RADIUS
        if y > lower_wall:
            return 2 * lower_wall - y
        return y

    def _check_paddle(self, player, old_x, old_y, incoming_dy):
        left_contact = PADDLE_MARGIN + PADDLE_WIDTH + BALL_RADIUS
        if player == 0:
            contact_x = left_contact
            crossed = self.ball_x <= contact_x < old_x
        else:
            contact_x = FIELD_WIDTH - left_contact
            crossed = old_x < contact_x <= self.ball_x
        if not crossed:
            return

        fraction = (contact_x - old_x) / self.ball_dx
        contact_y = self._reflect_wall(old_y + fraction * incoming_dy)
        top = self.paddle_y[player]
        if not (
            top - BALL_RADIUS <= contact_y <= top + PADDLE_HEIGHT + BALL_RADIUS
        ):
            return

        self.ball_x = contact_x
        self.ball_y = contact_y
        self._bounce(player, contact_y - (top + PADDLE_HEIGHT / 2))

    def _bounce(self, player, offset):
        # Попадание в центр даёт прямой отскок, попадание в край — до 60°.
        relative_offset = max(-1, min(1, offset / (PADDLE_HEIGHT / 2)))
        angle = relative_offset * MAX_BOUNCE_ANGLE
        self.ball_speed = min(MAX_BALL_SPEED, self.ball_speed + SPEED_GAIN)
        direction = 1 if player == 0 else -1
        self.ball_dx = direction * self.ball_speed * math.cos(angle)
        self.ball_dy = self.ball_speed * math.sin(angle)

    def _score(self, player, serve_direction):
        self.scores[player] += 1
        if self.scores[player] == WINNING_SCORE:
            self.winner = player + 1
        self._serve(serve_direction)


class GameRenderer:
    """Рисуйте поле, счёт и состояние матча на Canvas."""

    def __init__(self, canvas):
        """Создайте постоянные элементы поля и подвижные объекты."""
        self.canvas = canvas
        center_x = FIELD_WIDTH / 2
        bottom = FIELD_TOP + FIELD_HEIGHT

        canvas.create_rectangle(
            0, FIELD_TOP, FIELD_WIDTH, bottom, fill=FIELD_COLOR, outline=""
        )
        canvas.create_line(
            center_x, FIELD_TOP + 1, center_x, bottom - 1,
            fill=BORDER, width=2, dash=(5, 8),
        )
        canvas.create_rectangle(
            1, FIELD_TOP, FIELD_WIDTH - 1, bottom - 1, outline=BORDER
        )

        self.score_items = []
        for x, number, color in (
            (center_x - 78, 1, LEFT_COLOR),
            (center_x + 78, 2, RIGHT_COLOR),
        ):
            canvas.create_text(
                x, 10, text=f"ИГРОК {number}", fill=color,
                font=("Segoe UI", 9, "bold"),
            )
            item = canvas.create_text(
                x, 39, fill=TEXT, font=("Segoe UI", 31, "bold")
            )
            self.score_items.append(item)

        self.paddles = [
            canvas.create_rectangle(0, 0, 0, 0, fill=color, outline="")
            for color in (LEFT_COLOR, RIGHT_COLOR)
        ]
        self.ball = canvas.create_oval(0, 0, 0, 0, fill=TEXT, outline="")
        center_y = FIELD_TOP + FIELD_HEIGHT / 2
        canvas.create_rectangle(
            center_x - 190, center_y - 48, center_x + 190, center_y + 48,
            fill=BACKGROUND, outline=BORDER, tags="overlay",
        )
        self.message = canvas.create_text(
            center_x, center_y - 13, fill=TEXT, tags="overlay",
            font=("Segoe UI", 21, "bold"),
        )
        self.hint = canvas.create_text(
            center_x, center_y + 20, fill=MUTED, tags="overlay",
            font=("Segoe UI", 10),
        )

    def draw(self, model, state):
        """Обновите координаты, счёт и сообщение на игровом поле."""
        left_x = PADDLE_MARGIN
        right_x = FIELD_WIDTH - PADDLE_MARGIN - PADDLE_WIDTH
        for player, x in enumerate((left_x, right_x)):
            y = FIELD_TOP + model.paddle_y[player]
            self.canvas.coords(
                self.paddles[player], x, y, x + PADDLE_WIDTH, y + PADDLE_HEIGHT
            )
            self.canvas.itemconfigure(
                self.score_items[player], text=str(model.scores[player])
            )

        x, y = model.ball_x, FIELD_TOP + model.ball_y
        self.canvas.coords(
            self.ball, x - BALL_RADIUS, y - BALL_RADIUS,
            x + BALL_RADIUS, y + BALL_RADIUS,
        )
        if state == "playing":
            self.canvas.itemconfigure("overlay", state="hidden")
            return

        titles = {
            "ready": ("До пяти очков", "Выберите сложность и начните игру"),
            "paused": ("Пауза", "Нажмите пробел, чтобы продолжить"),
            "finished": (
                f"Победил игрок {model.winner}",
                "Нажмите «Начать игру» для нового матча",
            ),
        }
        title, hint = titles[state]
        self.canvas.itemconfigure(self.message, text=title)
        self.canvas.itemconfigure(self.hint, text=hint)
        self.canvas.itemconfigure("overlay", state="normal")


class App:
    """Создайте окно и свяжите управление с игровым циклом."""

    def __init__(self, root):
        """Настройте интерфейс, привязки клавиш и обновление кадров."""
        self.root = root
        self.root.title("Пинг-понг • Игра для двоих")
        self.root.geometry("900x600")
        self.root.resizable(False, False)
        self.root.configure(bg=BACKGROUND)

        self.model = GameModel()
        self.state = "ready"
        self.pressed_keys = set()
        self.window_system = self.root.tk.call("tk", "windowingsystem")
        self.difficulty = tk.StringVar(value="Средняя")
        self._build_interface()
        self.root.bind("<KeyPress>", self._key_pressed)
        self.root.bind("<KeyRelease>", self._key_released)
        self.root.bind("<FocusOut>", self._focus_lost)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._refresh()
        self._tick()

    def _build_interface(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "TButton", font=("Segoe UI", 10, "bold"), padding=(13, 7),
            background="#243248", foreground=TEXT, bordercolor=BORDER,
            focuscolor=BORDER,
        )
        style.map(
            "TButton", background=[("active", "#314460")],
            foreground=[("disabled", "#8291a7")],
        )
        style.configure(
            "Start.TButton", background=LEFT_COLOR, foreground="#102322"
        )
        style.map(
            "Start.TButton",
            background=[("disabled", "#243248"), ("active", "#9af0e4")],
        )
        style.configure(
            "TCombobox", foreground=TEXT, fieldbackground="#243248",
            background="#243248", arrowcolor=TEXT, padding=4,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#243248"), ("disabled", "#1b2535")],
            foreground=[("disabled", "#8291a7")],
            selectbackground=[("readonly", "#243248")],
            selectforeground=[("readonly", TEXT)],
        )

        header = tk.Frame(self.root, bg=BACKGROUND)
        header.pack(fill="x", padx=30, pady=(14, 6))
        tk.Label(
            header, text="Пинг-понг", bg=BACKGROUND, fg=TEXT,
            font=("Segoe UI", 24, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="Двое игроков · до 5 очков", bg=BACKGROUND,
            fg=MUTED, font=("Segoe UI", 10),
        ).pack(side="right")

        toolbar = tk.Frame(self.root, bg=BACKGROUND)
        toolbar.pack(fill="x", padx=30, pady=(0, 5))
        self.start_button = ttk.Button(
            toolbar, text="Начать игру", command=self._start,
            style="Start.TButton",
        )
        self.start_button.pack(side="left")
        self.pause_button = ttk.Button(
            toolbar, text="Пауза", command=self._toggle_pause
        )
        self.pause_button.pack(side="left", padx=8)
        ttk.Button(
            toolbar, text="Заново", command=self._reset
        ).pack(side="left")
        self.difficulty_box = ttk.Combobox(
            toolbar, textvariable=self.difficulty, values=tuple(START_SPEEDS),
            state="readonly", width=10, font=("Segoe UI", 10),
        )
        self.difficulty_box.pack(side="right")
        tk.Label(
            toolbar, text="Сложность", bg=BACKGROUND, fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(side="right", padx=10)

        self.canvas = tk.Canvas(
            self.root, width=FIELD_WIDTH, height=FIELD_TOP + FIELD_HEIGHT,
            bg=BACKGROUND, highlightthickness=0,
        )
        self.canvas.pack()
        self.renderer = GameRenderer(self.canvas)

        footer = tk.Frame(self.root, bg=BACKGROUND)
        footer.pack(fill="x", padx=30, pady=(13, 0))
        for label, color, side in (
            ("Игрок 1   W / S", LEFT_COLOR, "left"),
            ("Игрок 2   ↑ / ↓", RIGHT_COLOR, "left"),
            ("Пробел — пауза    R — заново", MUTED, "right"),
        ):
            tk.Label(
                footer, text=label, bg=BACKGROUND, fg=color,
                font=("Segoe UI", 10),
            ).pack(side=side, padx=(0, 24) if side == "left" else 0)

    def _start(self):
        self.model.reset(START_SPEEDS[self.difficulty.get()])
        self.pressed_keys.clear()
        self.canvas.focus_set()
        self.state = "playing"
        self._refresh()

    def _reset(self):
        self.model.reset(START_SPEEDS[self.difficulty.get()])
        self.pressed_keys.clear()
        self.canvas.focus_set()
        self.state = "ready"
        self._refresh()

    def _toggle_pause(self):
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"
        else:
            return
        self.canvas.focus_set()
        self._refresh()

    def _refresh(self):
        match_active = self.state in ("playing", "paused")
        self.start_button.configure(
            state="disabled" if match_active else "normal"
        )
        self.difficulty_box.configure(
            state="disabled" if match_active else "readonly"
        )
        self.pause_button.configure(
            text="Продолжить" if self.state == "paused" else "Пауза",
            state="normal" if match_active else "disabled",
        )
        self.renderer.draw(self.model, self.state)

    def _game_key(self, event):
        key = event.keysym.lower()
        if self.window_system == "win32":
            key = WINDOWS_LETTER_KEYS.get(event.keycode, key)
        return RUSSIAN_KEYS.get(key, key)

    def _key_pressed(self, event):
        key = self._game_key(event)
        if key in self.pressed_keys:
            return
        if key == "r":
            self._reset()
        self.pressed_keys.add(key)
        if key == "space":
            self._toggle_pause()

    def _key_released(self, event):
        self.pressed_keys.discard(self._game_key(event))

    def _focus_lost(self, event):
        self.pressed_keys.clear()

    def _tick(self):
        if self.state == "playing":
            left = (
                int("s" in self.pressed_keys) - int("w" in self.pressed_keys)
            )
            right = (
                int("down" in self.pressed_keys)
                - int("up" in self.pressed_keys)
            )
            self.model.step(left, right)
            if self.model.winner is None:
                self.renderer.draw(self.model, self.state)
            else:
                self.state = "finished"
                self._refresh()

        self.frame_id = self.root.after(FRAME_MS, self._tick)

    def _close(self):
        self.root.after_cancel(self.frame_id)
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    app = App(window)
    window.mainloop()
