from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import Qt
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Keyword, Name, String, Number, Comment, Operator, Token
from core.utils.logger import logger

class MarkdownHighlighter(QSyntaxHighlighter):
    """
    Sidecar 3.4 Production Highlighter.
    
    SOLUTIONS (PM Audit):
    1. Aliases: Supports 'js', 'py', 'sh', 'yml'.
    2. Logic: Fixed inverted fence state.
    3. Error Handling: Replaced bare except with logged fallback.
    """
    
    LANG_ALIASES = {
        "js": "javascript",
        "py": "python",
        "sh": "bash",
        "yml": "yaml",
        "json": "json"
    }

    def __init__(self, parent_doc, opacity_callback):
        super().__init__(parent_doc)
        self.get_opacity = opacity_callback
        self.current_lang = "python"

        # Lexer cache to avoid repeated lexer creation (performance optimization)
        self._lexer_cache = {}

        self.theme = {
            Keyword: "#F92672",
            Name.Builtin: "#66D9EF",
            Name.Function: "#A6E22E",
            Name.Class: "#A6E22E",
            Name: "#FD971F",
            String: "#E6DB74",
            Number: "#AE81FF",
            Comment: "#75715E",
            Operator: "#F92672",
            Token.Text: "#F8F8F2",
        }

    def _get_lexer(self):
        """Returns a cached lexer or creates a new one if not cached."""
        if self.current_lang not in self._lexer_cache:
            try:
                self._lexer_cache[self.current_lang] = get_lexer_by_name(self.current_lang)
            except Exception:
                logger.warning(f"Lexer '{self.current_lang}' not found. Falling back to Python.")
                self._lexer_cache[self.current_lang] = get_lexer_by_name("python")
        return self._lexer_cache[self.current_lang]

    def _get_fmt(self, token_type):
        alpha = int(self.get_opacity() * 255)
        color_hex = "#F8F8F2"
        for p_token, p_hex in self.theme.items():
            if token_type in p_token:
                color_hex = p_hex
                break
        color = QColor(color_hex)
        color.setAlpha(alpha)
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        return fmt

    def highlightBlock(self, text: str):
        prev_state = self.previousBlockState()
        
        # 1. Fence & Language Detection
        if text.strip().startswith("```"):
            lang = text.strip("`").strip().lower()
            if lang:
                # Apply Aliases (js -> javascript, etc)
                self.current_lang = self.LANG_ALIASES.get(lang, lang)
            
            # Apply Header Style (Electric Blue)
            alpha = int(self.get_opacity() * 255)
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(102, 217, 239, alpha)) 
            fmt.setFontWeight(QFont.Weight.Bold)
            self.setFormat(0, len(text), fmt)
            
            # Fixed Inverted Logic: 0 if previously in block, else 1
            self.setCurrentBlockState(0 if prev_state == 1 else 1)
            return

        # 2. State Persistence
        current_state = 1 if prev_state == 1 else 0
        self.setCurrentBlockState(current_state)

        if current_state == 1:
            lexer = self._get_lexer()
            tokens = lex(text, lexer)
            index = 0
            for ttype, val in tokens:
                self.setFormat(index, len(val), self._get_fmt(ttype))
                index += len(val)
        else:
            self.setFormat(0, len(text), self._get_fmt(Token.Text))
