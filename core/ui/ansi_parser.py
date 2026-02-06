import re
from typing import List, Tuple
from PyQt6.QtGui import QColor, QTextCharFormat

class ANSIParser:
    """
    Parses ANSI escape codes (colorama output) and converts to Qt text formatting.
    Supports standard 16-color palette and basic text attributes.
    """
    
    # ANSI color code mappings (colorama standard)
    ANSI_COLORS = {
        '30': QColor(0, 0, 0),           # Black
        '31': QColor(255, 85, 85),       # Red (Bright)
        '32': QColor(85, 255, 85),       # Green (Bright)
        '33': QColor(255, 255, 85),      # Yellow (Bright)
        '34': QColor(85, 170, 255),      # Blue (Bright)
        '35': QColor(255, 85, 255),      # Magenta (Bright)
        '36': QColor(85, 255, 255),      # Cyan (Bright)
        '37': QColor(255, 255, 255),     # White (Bright)
        '90': QColor(128, 128, 128),     # Bright Black (Gray)
        '91': QColor(255, 0, 0),         # Bright Red
        '92': QColor(0, 255, 0),         # Bright Green
        '93': QColor(255, 255, 0),       # Bright Yellow
        '94': QColor(0, 128, 255),       # Bright Blue
        '95': QColor(255, 0, 255),       # Bright Magenta
        '96': QColor(0, 255, 255),       # Bright Cyan
        '97': QColor(255, 255, 255),     # Bright White
    }
    
    # ANSI escape sequence regex
    ANSI_ESCAPE = re.compile(r'\x1b\[([0-9;]+)m')
    
    @staticmethod
    def parse(text: str) -> List[Tuple[str, QTextCharFormat]]:
        """
        Parse ANSI escape codes and return (text, format) tuples.
        
        Args:
            text: Raw text with ANSI escape codes
            
        Returns:
            List of (text_chunk, QTextCharFormat) tuples
        """
        chunks = []
        current_format = QTextCharFormat()
        current_format.setForeground(QColor(255, 255, 255))  # Default white
        
        last_end = 0
        
        for match in ANSIParser.ANSI_ESCAPE.finditer(text):
            # Add text before this escape code
            if match.start() > last_end:
                chunk_text = text[last_end:match.start()]
                chunks.append((chunk_text, QTextCharFormat(current_format)))
            
            # Parse the escape code
            codes = match.group(1).split(';')
            for code in codes:
                if code == '0':
                    # Reset
                    current_format = QTextCharFormat()
                    current_format.setForeground(QColor(255, 255, 255))
                elif code in ANSIParser.ANSI_COLORS:
                    # Foreground color
                    current_format.setForeground(ANSIParser.ANSI_COLORS[code])
                elif code == '1':
                    # Bold
                    current_format.setFontWeight(700)
                elif code == '22':
                    # Normal weight
                    current_format.setFontWeight(400)
            
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            chunk_text = text[last_end:]
            chunks.append((chunk_text, QTextCharFormat(current_format)))
        
        return chunks
    
    @staticmethod
    def strip_ansi(text: str) -> str:
        """
        Remove all ANSI escape codes from text.
        
        Args:
            text: Text with ANSI codes
            
        Returns:
            Plain text without ANSI codes
        """
        return ANSIParser.ANSI_ESCAPE.sub('', text)
