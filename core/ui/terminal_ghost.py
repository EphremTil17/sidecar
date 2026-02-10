from PyQt6.QtWidgets import QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QFont, QTextCursor, QCursor, QTextCharFormat
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
    
    def __init__(self, bg_low: float, bg_high: float, text_low: float, text_high: float, 
                 font_size: int = 10, font_family: str = "Consolas",
                 width: int = 800, height: int = 600):
        super().__init__()
        
        self.bg_low = bg_low
        self.bg_high = bg_high
        self.text_low = text_low
        self.text_high = text_high
        self.max_lines = 1000
        self._is_currently_click_through = False
        self._focus_mode = False # Toggle state for Clarity/Blur mode
        self._history_cache = [] # Cache of (text, format) chunks
        
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
        
        # 4. Monospaced Font Setup
        font = QFont(font_family, font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        self.terminal.setFont(font)
        
        # 5. Global Terminal Styling
        text_alpha = int(self.text_low * 255)
        self.terminal.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                color: rgba(255, 255, 255, {text_alpha});
                border: none;
                padding: 10px 0px 10px 10px;
            }}
        """)
        self.layout.addWidget(self.terminal)
        
        # 6. Minimalist Ghost Scrollbar
        self.terminal.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.terminal.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 6.5 Status Dot (Indicator for hidden text)
        self.status_dot = QWidget(self.central_widget)
        self.status_dot.setFixedSize(5, 5)
        self.status_dot.setStyleSheet("background-color: rgba(0, 255, 255, 0.5); border-radius: 2px;")
        self.status_dot.hide() # Hidden by default
        
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
        self.resize(width, height)
        self._reposition_status_dot()
        
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

    def _reposition_status_dot(self):
        """Keep the status dot in the top-right corner."""
        self.status_dot.move(self.central_widget.width() - 10, 5)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_status_dot()

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

        # 2. Update Terminal Style (Base Text Opacity / Padding)
        text_alpha_255 = int(text_alpha_val * 255)
        self.terminal.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                color: rgba(255, 255, 255, {text_alpha_255});
                border: none;
                padding: 10px 0px 10px 10px;
            }}
        """)
        
        # 3. Force re-render from cache with new alpha
        self._refresh_text_stream()

    def _refresh_text_stream(self):
        """Force re-rendering from cache without resetting scroll position."""
        v_scroll = self.terminal.verticalScrollBar()
        scroll_pos = v_scroll.value()
        
        self.terminal.clear()
        
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Calculate current alpha based on visibility
        current_text_opacity = self.text_high if self._focus_mode else self.text_low
        alpha_255 = int(current_text_opacity * 255)
        
        # Batch insert from parsed cache (Zero Regex Overhead)
        for chunk_text, text_format in self._history_cache:
            # IMPORTANT: Clone the format to avoid mutating the master cache
            fmt = QTextCharFormat(text_format)
            color = fmt.foreground().color()
            color.setAlpha(alpha_255)
            fmt.setForeground(color)
            cursor.insertText(chunk_text, fmt)
            
        self.terminal.setTextCursor(cursor)
        
        # Restore scroll position to prevent reset during toggle
        v_scroll.setValue(scroll_pos)

    def show_hud_notification(self, message: str):
        """Displays a concise HUD message in the terminal."""
        # Simplified single-line format for space efficiency
        self.append_text(f"\n[INFO] {message}\n")

    def add_turn_divider(self):
        """Adds a subtle visual divider between AI turns."""
        divider_width = 40
        # Using Gray color (90m) for the divider
        divider_msg = f"\x1b[90m{'-' * divider_width}\x1b[0m\n"
        self.append_text(divider_msg)

    def append_text(self, text: str):
        """Parse once, cache, and render."""
        chunks = ANSIParser.parse(text)
        
        # 1. Update Persistent Cache
        for chunk_text, text_format in chunks:
            self._history_cache.append((chunk_text, text_format))
            
        # 2. Render specifically these new chunks
        self._render_chunks(chunks)
        self._trim_history()

    def _render_chunks(self, chunks):
        """Appends pre-parsed chunks to the document."""
        cursor = self.terminal.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Calculate current alpha based on Focus Mode
        current_text_opacity = self.text_high if self._focus_mode else self.text_low
        alpha_255 = int(current_text_opacity * 255)
        
        for chunk_text, text_format in chunks:
            # IMPORTANT: Clone the format to avoid mutating the master cache
            fmt = QTextCharFormat(text_format)
            color = fmt.foreground().color()
            color.setAlpha(alpha_255)
            fmt.setForeground(color)
            cursor.insertText(chunk_text, fmt)
        
        self.terminal.setTextCursor(cursor)
        self.terminal.ensureCursorVisible()

        self.terminal.ensureCursorVisible()

    def _trim_history(self):
        """Maintain performance by limiting the terminal buffer length."""
        # 1. Trim the visual widget
        doc = self.terminal.document()
        blocks_to_remove = doc.blockCount() - self.max_lines
        
        if blocks_to_remove > 0:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(blocks_to_remove):
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()
            
            # Trim the pre-parsed cache (2x multiplier to account for chunking)
            if len(self._history_cache) > self.max_lines * 2:
                self._history_cache = self._history_cache[-(self.max_lines * 2):]
                
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
        
    def scroll_up(self, steps: int = 3):
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() - (scrollbar.singleStep() * steps)) 
        
    def scroll_down(self, steps: int = 3):
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + (scrollbar.singleStep() * steps))
