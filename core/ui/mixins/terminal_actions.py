from PyQt6.QtGui import QTextCursor

from core.utils.logger import logger


class TerminalActionMixin:
    """
    Mixin component for Sidecar terminal windows to provide
    standardized scrolling, scaling, and movement actions.
    """

    def increase_font_size(self):
        current_font = self.terminal.font()
        new_size = min(current_font.pointSize() + 1, 24)
        current_font.setPointSize(new_size)
        self.terminal.setFont(current_font)
        logger.debug(f"Terminal font scaled to {new_size}pt")

    def decrease_font_size(self):
        current_font = self.terminal.font()
        new_size = max(current_font.pointSize() - 1, 8)
        current_font.setPointSize(new_size)
        self.terminal.setFont(current_font)
        logger.debug(f"Terminal font scaled to {new_size}pt")

    def scroll_up(self, steps=5):
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() - scrollbar.singleStep() * steps)

    def scroll_down(self, steps=5):
        scrollbar = self.terminal.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + scrollbar.singleStep() * steps)

    def move_relative(self, dx: int, dy: int):
        self.move(self.x() + dx, self.y() + dy)

    def _trim_history(self, max_lines: int):
        """Maintain performance by limiting the terminal buffer length."""
        doc = self.terminal.document()
        blocks_to_remove = doc.blockCount() - max_lines
        if blocks_to_remove > 0:
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.NextBlock,
                QTextCursor.MoveMode.KeepAnchor,
                blocks_to_remove,
            )
            cursor.removeSelectedText()
