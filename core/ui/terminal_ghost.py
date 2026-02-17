import re
from PyQt6.QtWidgets import QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QFont, QTextCursor, QCursor, QTextCharFormat
from core.drivers.window_manager import apply_ghost_mode, set_always_on_top, set_click_through
from core.utils.logger import logger
from core.utils.events import bus, AppEvent
from core.ui.highlighter import MarkdownHighlighter

class TerminalGhostWindow(QMainWindow):
    """
    Transparent terminal window that displays stdout/stderr with premium syntax highlighting.
    
    ARCHITECTURE (Sidecar 3.2):
    Uses a native QSyntaxHighlighter (MarkdownHighlighter). This solves the 
    'split color' and 'newline drift' bugs by analyzing text in atomic blocks 
    rather than streaming chunks.
    """
    
    def __init__(self, bg_low: float, bg_high: float, text_low: float, text_high: float, 
                 font_size: int = 10, font_family: str = "Consolas",
                 width: int = 800, height: int = 600):
        super().__init__()
        
        self.bg_low = bg_low
        self.bg_high = bg_high
        self.text_low = text_low
        self.text_high = text_high
        self.max_lines = 1000
        self._is_currently_click_through = True # Default to ghosted
        self._focus_mode = False # Toggle state for Clarity/Blur mode
        
        # Connect to Global Event Bus
        bus.dispatch.connect(self._on_event)
        
        # 1. Window Configuration
        # Frameless, Always-on-Top, and hidden from Taskbar (Tool window)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Ghost Protocol 2.0: Stealth Boot
        # Start at 0% opacity to prevent the 'Capture Flash' before 
        # Win32 affinity flags are anchored.
        self.setWindowOpacity(0.0)
        
        # 2. Central Widget (The visual container)
        self.central_widget = QWidget()
        bg_alpha = int(self.bg_low * 255)
        self.central_widget.setStyleSheet(f"""
            QWidget {{
                background: rgba(0, 0, 0, {bg_alpha});
                border: 1px solid rgba(200, 200, 200, 0.5);
                border-radius: 6px;
            }}
        """)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setCentralWidget(self.central_widget)
        
        # 3. Terminal Display Component
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        self.terminal.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.terminal.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.terminal.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 4. Highlighter Integration (THE ROBUST SOLUTION)
        self.highlighter = MarkdownHighlighter(self.terminal.document(), 
                                               opacity_callback=lambda: self.get_current_text_opacity())
        
        # 5. Monospaced Font Setup
        font = QFont(font_family, font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.terminal.setFont(font)
        
        # 6. Global Terminal Styling (Pure UI, NO Scrollbar visibility)
        self.terminal.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                border: none;
                padding: 10px 0px 10px 10px;
            }}
        """)
        self.layout.addWidget(self.terminal)

        # 7. Forcefully Wipe Scrollbar History / Interaction
        self.terminal.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.terminal.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.terminal.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        
        # 8. Status Dot (Indicator for hidden text)
        self.status_dot = QWidget(self.central_widget)
        self.status_dot.setFixedSize(5, 5)
        self.status_dot.setStyleSheet("background-color: rgba(0, 255, 255, 0.5); border-radius: 2px;")
        self.status_dot.hide()
        
        # 9. Default Window Geometry
        self.resize(width, height)
        self._reposition_status_dot()
        
        # 10. Apply Win32 Ghost Mode (Immediate HWND mapping)
        # We call this synchronously to ensure flags are set BEFORE the first draw.
        self._apply_ghost_mode()
        
    def _apply_ghost_mode(self):
        """Apply Win32 transparency protocols."""
        try:
            # Force mapping of the window handle
            hwnd = int(self.winId())
            
            # Apply capture exclusion immediately
            if apply_ghost_mode(hwnd):
                logger.success("Ghost Protocol applied to terminal window.")
            
            set_always_on_top(hwnd, True)
            set_click_through(hwnd, True)
            self._is_currently_click_through = True
            
            # Stealth Boot Release: Now that the window is hidden from capture,
            # we can safely show it to the local user.
            QTimer.singleShot(100, lambda: self.setWindowOpacity(1.0))
            
        except Exception as e:
            logger.error(f"Critical error applying ghost mode: {e}")
            self.setWindowOpacity(1.0) # Fallback to visibility if ghosting fails

    def _reposition_status_dot(self):
        """Keep the status dot in the top-right corner."""
        self.status_dot.move(self.central_widget.width() - 10, 5)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_status_dot()

    def get_current_text_opacity(self) -> float:
        """Helper to get the current target text alpha based on mode."""
        return self.text_high if self._focus_mode else self.text_low

    def toggle_focus_mode(self):
        """
        Premium Clarity Toggle: 
        Switches between minimalist 'Ghost' and high-contrast 'Focus' (Solid) mode.
        """
        self._focus_mode = not self._focus_mode
        
        if self._focus_mode:
            # FOCUS MODE: High contrast, solid background for readability
            bg_alpha = int(self.bg_high * 255)
            text_alpha_val = self.text_high
            self.status_dot.show()
            logger.debug("Ghost Mode: FOCUS / HIGH-CONTRAST Active")
        else:
            # NORMAL MODE: Minimalist Ghost
            bg_alpha = int(self.bg_low * 255)
            text_alpha_val = self.text_low
            self.status_dot.hide()
            logger.debug("Ghost Mode: GHOST / TRANSPARENT Active")

        # 1. Update Container Style (Background Opacity)
        self.central_widget.setStyleSheet(f"""
            QWidget {{
                background: rgba(0, 0, 0, {bg_alpha});
                border: 1px solid rgba(200, 200, 200, 0.3);
                border-radius: 6px;
            }}
        """)

        # 2. Update Terminal Style (Base Text Padding)
        self.terminal.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                border: none;
                padding: 10px 0px 10px 10px;
            }}
        """)
        
        # 3. Force re-render with the explicit rehighlight() protocol.
        # This is the mission-critical structural fix for the 'Alpha Lock'.
        self.highlighter.rehighlight()

    def _on_event(self, event, payload):
        """Dispatches bus events to local UI methods."""
        if event == AppEvent.UI_FOCUS_TOGGLE:
            self.toggle_focus_mode()
        elif event == AppEvent.UI_FONT_SCALE:
            if payload > 0: self.increase_font_size()
            else: self.decrease_font_size()
        elif event == AppEvent.UI_MOVE:
            dx, dy = payload
            self.move(self.x() + dx, self.y() + dy)
        elif event == AppEvent.UI_SCROLL:
            if payload > 0: self.scroll_down()
            else: self.scroll_up()
        elif event == AppEvent.AGENT_CHUNK_UPDATE:
            chunk, vector = payload
            self.append_markdown(chunk)
        elif event == AppEvent.AGENT_STATUS_UPDATE:
            self.show_hud_notification(payload)
        elif event == AppEvent.AGENT_HEARTBEAT:
            self.force_repaint()

    def force_repaint(self):
        """Force a full alpha-buffer refresh to prevent DWM hibernation."""
        self.update() # Qt native repaint request

    def show_hud_notification(self, message: str):
        """Displays a concise HUD message, scrubbing ANSI escapes."""
        # Scrub ANSI codes (colors, etc) so they don't break markdown rendering
        clean_msg = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('', message)
        self.append_markdown(f"\n[INFO] {clean_msg}\n")

    def add_turn_divider(self):
        """Adds a subtle visual divider between AI turns."""
        divider_width = 40
        # Using Gray color (90m) for the divider
        divider_msg = f"\n{'-' * divider_width}\n"
        self.append_markdown(divider_msg)

    def append_markdown(self, text: str):
        """Append raw markdown text. The highlighter handles everything else."""
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()
        self._trim_history()


    def _trim_history(self):
        """Maintain performance by limiting the terminal buffer length."""
        doc = self.terminal.document()
        blocks_to_remove = doc.blockCount() - self.max_lines

        if blocks_to_remove > 0:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            # Efficiently select the entire top chunk in one move
            # Move cursor N blocks while keeping the anchor at the start
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor, blocks_to_remove)
            cursor.removeSelectedText()
                
    def increase_font_size(self):
        """Dynamic font scaling via hotkeys."""
        current_font = self.terminal.font()
        new_size = min(current_font.pointSize() + 1, 24)
        current_font.setPointSize(new_size)
        self.terminal.setFont(current_font)
        logger.debug(f"Terminal font scaled to {new_size}pt")
        
    def decrease_font_size(self):
        """Dynamic font scaling via hotkeys."""
        current_font = self.terminal.font()
        new_size = max(current_font.pointSize() - 1, 8)
        current_font.setPointSize(new_size)
        self.terminal.setFont(current_font)
        logger.debug(f"Terminal font scaled to {new_size}pt")
        
    def move_up(self, pixels: int = 50):
        self.move(self.x(), self.y() - pixels)
        
    def move_down(self, pixels: int = 50):
        self.move(self.x(), self.y() + pixels)
        
    def move_left(self, pixels: int = 50):
        self.move(self.x() - pixels, self.y())
        
    def move_right(self, pixels: int = 50):
        self.move(self.x() + pixels, self.y())
        
    def scroll_up(self):
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() - scrollbar.singleStep() * 5) 
        
    def scroll_down(self):
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + scrollbar.singleStep() * 5)
