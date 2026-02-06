from PyQt6.QtWidgets import QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor
from core.ui.ansi_parser import ANSIParser
from core.drivers.window_manager import apply_ghost_mode, set_always_on_top
from core.utils.logger import logger

class TerminalGhostWindow(QMainWindow):
    """
    Transparent terminal window that displays stdout/stderr with ANSI color support.
    Designed to be pixel-perfect match to PowerShell/CMD terminal aesthetics.
    
    Window is fully click-through (WS_EX_TRANSPARENT). All interaction is via hotkeys:
    - Ctrl+Alt+Arrow: Move window
    - Ctrl+Alt+=/- : Font size
    - Ctrl+Alt+PgUp/PgDn: Scroll (if implemented)
    """
    
    def __init__(self, opacity: float = 0.78, font_size: int = 10, font_family: str = "Consolas"):
        super().__init__()
        
        self.opacity = opacity
        self.max_lines = 1000  # Limit history to prevent memory bloat
        
        # 1. Window Configuration
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 2. Central Widget with visible border
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
        
        # 3. Terminal Display (QPlainTextEdit for monospaced console output)
        self.terminal = QPlainTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        
        # Disable text interaction (window is click-through anyway)
        self.terminal.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.terminal.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.terminal.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # 4. Font Configuration (Monospaced Console Font)
        font = QFont(font_family, font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.terminal.setFont(font)
        
        # 5. Styling (Transparent background, translucent text)
        self.terminal.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                color: rgba(255, 255, 255, {alpha});
                border: none;
                padding: 8px;
            }}
        """)
        
        self.layout.addWidget(self.terminal)
        
        # 6. Custom Scrollbar styling (visible but click-through)
        self.terminal.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.terminal.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scrollbar_style = f"""
            QScrollBar:vertical {{
                background: rgba(50, 50, 50, {int(alpha * 0.3)});
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(200, 200, 200, 0.4);
                min-height: 30px;
                border-radius: 4px;
                margin: 1px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(200, 200, 200, 0.8);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """
        self.terminal.verticalScrollBar().setStyleSheet(scrollbar_style)
        
        # 7. Default Geometry
        self.resize(800, 600)
        
        # 8. Apply Win32 Ghost Mode (delayed to ensure window handle is ready)
        QTimer.singleShot(200, self._apply_ghost_mode)
        
    def _apply_ghost_mode(self):
        """Apply Win32 transparency and ghost protocol."""
        from core.drivers.window_manager import set_click_through
        
        hwnd = int(self.winId())
        
        # Apply ghost mode (hide from screen capture)
        if apply_ghost_mode(hwnd):
            logger.success("Ghost Protocol applied to terminal window.")
        else:
            logger.warning("Failed to apply Ghost Protocol.")
            
        # Set always on top
        set_always_on_top(hwnd, True)
        
        # Apply click-through to the entire window
        # Window is moved via hotkeys (Ctrl+Alt+Arrow keys)
        set_click_through(hwnd, True)
        
    def append_text(self, text: str):
        """
        Append text to terminal with ANSI color support.
        
        Args:
            text: Raw text with ANSI escape codes
        """
        # Parse ANSI codes
        chunks = ANSIParser.parse(text)
        
        # Move cursor to end
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Insert formatted chunks
        for chunk_text, text_format in chunks:
            cursor.insertText(chunk_text, text_format)
        
        # Auto-scroll to bottom
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()
        
        # Trim history if too long
        self._trim_history()
        
    def _trim_history(self):
        """Remove old lines if terminal history exceeds max_lines."""
        doc = self.terminal.document()
        if doc.blockCount() > self.max_lines:
            # Remove oldest lines
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(doc.blockCount() - self.max_lines):
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # Remove the newline
                
    def increase_font_size(self):
        """Increase font size by 1pt (max: 24pt)."""
        current_font = self.terminal.font()
        new_size = min(current_font.pointSize() + 1, 24)
        current_font.setPointSize(new_size)
        self.terminal.setFont(current_font)
        logger.debug(f"Font size: {new_size}pt")
        
    def decrease_font_size(self):
        """Decrease font size by 1pt (min: 8pt)."""
        current_font = self.terminal.font()
        new_size = max(current_font.pointSize() - 1, 8)
        current_font.setPointSize(new_size)
        self.terminal.setFont(current_font)
        logger.debug(f"Font size: {new_size}pt")
        
    # Window movement methods (called via hotkeys)

    def move_up(self, pixels: int = 50):
        """Move window up by specified pixels."""
        self.move(self.x(), self.y() - pixels)
        logger.debug(f"Window moved up {pixels}px")
        
    def move_down(self, pixels: int = 50):
        """Move window down by specified pixels."""
        self.move(self.x(), self.y() + pixels)
        logger.debug(f"Window moved down {pixels}px")
        
    def move_left(self, pixels: int = 50):
        """Move window left by specified pixels."""
        self.move(self.x() - pixels, self.y())
        logger.debug(f"Window moved left {pixels}px")
        
    def move_right(self, pixels: int = 50):
        """Move window right by specified pixels."""
        self.move(self.x() + pixels, self.y())
        logger.debug(f"Window moved right {pixels}px")
        
    # Scroll methods (called via hotkeys since window is click-through)
    def scroll_up(self, lines: int = 5):
        """Scroll terminal content up by specified lines."""
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() - (lines * 20))  # ~20px per line
        
    def scroll_down(self, lines: int = 5):
        """Scroll terminal content down by specified lines."""
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + (lines * 20))  # ~20px per line
