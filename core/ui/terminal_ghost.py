from PyQt6.QtWidgets import QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QFont, QTextCursor, QCursor
from core.ui.ansi_parser import ANSIParser
from core.drivers.window_manager import apply_ghost_mode, set_always_on_top, set_click_through
from core.utils.logger import logger

class TerminalGhostWindow(QMainWindow):
    """
    Transparent terminal window that displays stdout/stderr with ANSI color support.
    
    ARCHITECTURE NOTE:
    We use a 'Dynamic Interactivity Polling' architecture instead of overriding 'nativeEvent'.
    Overriding 'nativeEvent' for WM_NCHITTEST is highly unstable during window initialization
    and caused persistent silent crashes. 
    
    Instead, we poll the mouse position (20Hz) and toggle the Win32 'WS_EX_TRANSPARENT' 
    style dynamically. This allows the scrollbar to be interactive while the rest of 
    the window remains click-through 'Ghost' content.
    """
    
    def __init__(self, opacity: float = 0.78, font_size: int = 10, font_family: str = "Consolas"):
        super().__init__()
        
        self.opacity = opacity
        self.max_lines = 1000
        self._is_currently_click_through = False
        
        # 1. Window Configuration
        # Frameless, Always-on-Top, and hidden from Taskbar (Tool window)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 2. Central Widget (The visual container)
        self.central_widget = QWidget()
        alpha = int(opacity * 255)
        self.central_widget.setStyleSheet(f"""
            QWidget {{
                background: rgba(0, 0, 0, {int(alpha * 0.5)});
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
        
        # 4. Monospaced Font Setup
        font = QFont(font_family, font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.terminal.setFont(font)
        
        # 5. Global Terminal Styling
        self.terminal.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                color: rgba(255, 255, 255, {alpha});
                border: none;
                padding: 10px;
            }}
        """)
        self.layout.addWidget(self.terminal)
        
        # 6. Minimalist Ghost Scrollbar
        self.terminal.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.terminal.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scrollbar_width = 7 # Sleek 7px visual width
        self.terminal.verticalScrollBar().setStyleSheet(f"""
            QScrollBar:vertical {{
                background: transparent;
                width: {scrollbar_width}px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.2);
                min-height: 40px;
                border-radius: 3px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.5);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)
        
        # 7. Default Window Geometry
        self.resize(800, 600)
        
        # 8. Mouse Polling for Interactivity
        # This timer drives the hybrid hit-testing logic safely.
        self.mouse_poll_timer = QTimer(self)
        self.mouse_poll_timer.timeout.connect(self._update_mouse_interactivity)
        
        # 9. Apply Win32 Ghost Mode (Delayed for stability)
        # We wait 500ms to ensure the window is fully mapped before applying OS-level affinity.
        QTimer.singleShot(500, self._apply_ghost_mode)
        
    def _apply_ghost_mode(self):
        """Apply Win32 transparency protocols and start hit-test polling."""
        try:
            hwnd = int(self.winId())
            if apply_ghost_mode(hwnd):
                logger.success("Ghost Protocol applied to terminal window.")
            set_always_on_top(hwnd, True)
            
            # Start mouse polling (50ms interval = snappy 20fps hit-testing)
            self.mouse_poll_timer.start(50)
            logger.success("Dynamic Hit-Testing ACTIVE (Scrollbar interaction ready)")
        except Exception as e:
            logger.error(f"Critical error applying ghost mode: {e}")
            
    def _update_mouse_interactivity(self):
        """
        Toggles window click-through state based on mouse proximity to the scrollbar.
        This provides a 'Solid' feel for interactions without breaking the 'Ghost' experience.
        """
        if not self.isVisible():
            return

        try:
            hwnd = int(self.winId())
            cursor_pos = QCursor.pos() # Pure Qt global mouse position
            
            sb = self.terminal.verticalScrollBar()
            should_be_interactive = False
            
            if sb.isVisible():
                # 1. Precise Scrollbar Hit
                sb_rect = sb.rect()
                sb_global_pos = sb.mapToGlobal(sb_rect.topLeft())
                sb_global_rect = sb_rect.translated(sb_global_pos)
                
                # 2. Virtual Interaction Zone (25px margin from right edge)
                # This ensures the user can easily trigger the scrollbar without 
                # needing pixel-perfect precision on the 7px visual bar.
                window_rect = self.geometry()
                right_edge_margin = 25
                interaction_zone = QRect(
                    window_rect.right() - right_edge_margin,
                    window_rect.top(),
                    right_edge_margin,
                    window_rect.height()
                )
                
                if sb_global_rect.contains(cursor_pos) or interaction_zone.contains(cursor_pos):
                    should_be_interactive = True
            
            # Update the Win32 Layered style ONLY when the state changes.
            is_click_through = not should_be_interactive
            if is_click_through != self._is_currently_click_through:
                set_click_through(hwnd, is_click_through)
                self._is_currently_click_through = is_click_through
                
        except Exception:
            # Silent fail for hit-testing to prevent UI stutters
            pass

    def append_text(self, text: str):
        """Append text to the terminal with full ANSI color support."""
        chunks = ANSIParser.parse(text)
        
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        for chunk_text, text_format in chunks:
            cursor.insertText(chunk_text, text_format)
        
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()
        self._trim_history()
        
    def _trim_history(self):
        """Maintain performance by limiting the terminal buffer length."""
        doc = self.terminal.document()
        if doc.blockCount() > self.max_lines:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(doc.blockCount() - self.max_lines):
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar() # Remove trailing block separator
                
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
        
    def scroll_up(self, lines: int = 5):
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() - (lines * 20)) 
        
    def scroll_down(self, lines: int = 5):
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + (lines * 20))
