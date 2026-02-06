import ctypes
from ctypes import wintypes

# Win32 Constants
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008

LWA_ALPHA = 0x00000002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Additional SWP Flags
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
SWP_HIDEWINDOW = 0x0080
SWP_NOOWNERZORDER = 0x0200

def apply_ghost_mode(hwnd: int):
    """
    Sets display affinity to hide the window from capture APIs (Zoom, Teams, etc.)
    """
    if not hwnd:
        return False
    
    result = user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
    return bool(result)

def set_click_through(hwnd: int, enabled: bool):
    """
    Toggles the WS_EX_TRANSPARENT style to allow mouse clicks to pass through.
    """
    if not hwnd:
        return False

    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    
    if enabled:
        style |= WS_EX_TRANSPARENT
    else:
        style &= ~WS_EX_TRANSPARENT
        
    result = user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
    
    # SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
    flags = SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, flags)
    
    return bool(result)

def set_always_on_top(hwnd: int, enabled: bool):
    """
    Sets the window to stay on top of all other windows.
    """
    if not hwnd:
        return False
        
    flag = -1 if enabled else -2 # HWND_TOPMOST or HWND_NOTOPMOST
    # SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
    flags = SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
    result = user32.SetWindowPos(hwnd, flag, 0, 0, 0, 0, flags)
    return bool(result)
