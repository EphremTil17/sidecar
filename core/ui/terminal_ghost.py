import re

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget

from core.drivers.window_manager import (
    apply_ghost_mode,
    set_always_on_top,
    set_click_through,
)
from core.ui.highlighter import MarkdownHighlighter
from core.ui.mixins.terminal_actions import TerminalActionMixin
from core.utils.events import AppEvent, bus
from core.utils.logger import logger


class TerminalGhostWindow(QMainWindow, TerminalActionMixin):
    """
    Transparent terminal window that displays stdout/stderr with premium syntax highlighting.
    Inherits standardized actions from TerminalActionMixin.
    """

    def __init__(
        self,
        bg_low: float,
        bg_high: float,
        text_low: float,
        text_high: float,
        font_size: int = 10,
        font_family: str = "Consolas",
        width: int = 800,
        height: int = 600,
    ):
        super().__init__()

        self.bg_low, self.bg_high = bg_low, bg_high
        self.text_low, self.text_high = text_low, text_high
        self.max_lines = 1000
        self._focus_mode = False
        self._last_completion_msg = None

        # UI Setup
        self._setup_window_flags()
        self._setup_layout(width, height)
        self._setup_terminal(font_family, font_size)
        self._setup_highlighter()
        self._setup_indicators()

        # Win32 & Event Integration
        self._apply_init_ghost_mode()
        bus.dispatch.connect(self._on_event)

    def _setup_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.0)  # Stealth Boot

    def _setup_layout(self, width, height):
        self.central_widget = QWidget()
        self._update_container_style()
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setCentralWidget(self.central_widget)
        self.resize(width, height)

    def _setup_terminal(self, font_family, font_size):
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        self.terminal.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.terminal.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.terminal.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.terminal.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.terminal.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        font = QFont(font_family, font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.terminal.setFont(font)
        self.terminal.setStyleSheet(
            "background: transparent; border: none; padding: 10px 0px 10px 10px;"
        )
        self.layout.addWidget(self.terminal)

    def _setup_highlighter(self):
        self.highlighter = MarkdownHighlighter(
            self.terminal.document(),
            opacity_callback=lambda: self.text_high if self._focus_mode else self.text_low,
        )

    def _setup_indicators(self):
        self.status_dot = QWidget(self.central_widget)
        self.status_dot.setFixedSize(5, 5)
        self.status_dot.setStyleSheet(
            "background-color: rgba(0, 255, 255, 0.5); border-radius: 2px;"
        )
        self.status_dot.hide()
        self._reposition_status_dot()

    def _apply_init_ghost_mode(self):
        try:
            hwnd = int(self.winId())
            if apply_ghost_mode(hwnd):
                logger.success("Ghost Protocol applied to terminal window.")
            set_always_on_top(hwnd, True)
            set_click_through(hwnd, True)
            QTimer.singleShot(100, lambda: self.setWindowOpacity(1.0))
        except Exception as e:
            logger.error(f"Ghost Mode Error: {e}")
            self.setWindowOpacity(1.0)

    def _reposition_status_dot(self):
        self.status_dot.move(self.central_widget.width() - 10, 5)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_status_dot()

    def toggle_focus_mode(self):
        self._focus_mode = not self._focus_mode
        self._update_container_style()
        if self._focus_mode:
            self.status_dot.show()
        else:
            self.status_dot.hide()
        self.highlighter.rehighlight()

    def _update_container_style(self):
        bg_alpha = int((self.bg_high if self._focus_mode else self.bg_low) * 255)
        self.central_widget.setStyleSheet(f"""
            QWidget {{
                background: rgba(0, 0, 0, {bg_alpha});
                border: 1px solid rgba(200, 200, 200, 0.3);
                border-radius: 6px;
            }}
        """)

    def _on_event(self, event, payload):
        if event == AppEvent.UI_FOCUS_TOGGLE:
            self.toggle_focus_mode()
        elif event == AppEvent.UI_FONT_SCALE:
            self.increase_font_size() if payload > 0 else self.decrease_font_size()
        elif event == AppEvent.UI_MOVE:
            self.move_relative(*payload)
        elif event == AppEvent.UI_SCROLL:
            self.scroll_down() if payload > 0 else self.scroll_up()
        elif event == AppEvent.AGENT_CHUNK_UPDATE:
            self.append_markdown(payload[0])
        elif event == AppEvent.AGENT_STATUS_UPDATE:
            self.show_hud_notification(payload)
        elif event == AppEvent.AGENT_HEARTBEAT:
            self.update()

    def show_hud_notification(self, message: str):
        # ANSI removal for clean HUD printing (Ghost Mode doesn't support full ANSI escapes)
        clean_msg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])").sub("", message)

        divider = "—" * 65

        # Structuralist Isolation Logic: Frame model output and system state transitions
        if "Response Streaming" in clean_msg:
            # Web-Parity 3.8: Neutralize any stuck code block state (unclosed ```)
            self.highlighter.reset_state()
            # Top of model output isolation
            self.append_markdown(f"[INFO]    {clean_msg}\n{divider}\n")
        elif "READY" in clean_msg:
            # Web-Parity 3.8: Neutralize state for the next interaction turn
            self.highlighter.reset_state()
            # Systems Ready isolation (framed like CLI cockpit)
            # Group with buffered completion message if available
            if self._last_completion_msg:
                self.append_markdown(
                    f"\n{divider}\n[SUCCESS] {self._last_completion_msg}\n[SYSTEM]  {clean_msg}\n{divider}\n"
                )
                self._last_completion_msg = None
            else:
                self.append_markdown(f"\n{divider}\n[SYSTEM]  {clean_msg}\n{divider}\n")
        elif "Complete" in clean_msg or "SUCCESS" in clean_msg:
            # Completion Log (e.g., Pixel Analysis Complete)
            # Buffer for unified Ready box
            self._last_completion_msg = clean_msg
        else:
            # General status log
            self.append_markdown(f"[INFO]    {clean_msg}\n")

    def append_markdown(self, text: str):
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()
        self._trim_history(self.max_lines)
