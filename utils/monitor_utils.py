import ctypes
from ctypes import wintypes
import mss

# --- Windows API Structures ---
class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32)
    ]

class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]

def _get_monitor_info_map():
    """
    Internal helper to get Windows monitor details.
    Returns a list of dicts with device, name, and rect.
    """
    user32 = ctypes.windll.user32
    monitors = []

    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        mi = MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(mi)
        user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi))
        
        device_name = mi.szDevice
        
        # Get Friendly Name
        display_device = DISPLAY_DEVICEW()
        display_device.cb = ctypes.sizeof(display_device)
        
        friendly_name = "Generic Monitor"
        
        # 1. Enum Adapter
        if user32.EnumDisplayDevicesW(device_name, 0, ctypes.byref(display_device), 0):
             # 2. Enum Monitor on Adapter
             monitor_device = DISPLAY_DEVICEW()
             monitor_device.cb = ctypes.sizeof(monitor_device)
             if user32.EnumDisplayDevicesW(device_name, 0, ctypes.byref(monitor_device), 0):
                 friendly_name = monitor_device.DeviceString

        monitors.append({
            "device": device_name,
            "name": friendly_name,
            "rect": (mi.rcMonitor.left, mi.rcMonitor.top, mi.rcMonitor.right, mi.rcMonitor.bottom)
        })
        return True

    # Handle HMONITOR type definition
    try:
        HMONITOR = wintypes.HMONITOR
    except AttributeError:
        HMONITOR = ctypes.c_void_p

    MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(monitor_enum_proc), 0)
    return monitors

def list_monitors():
    """
    Returns a list of dictionaries containing:
    { 'index': int, 'name': str, 'res': str, 'primary': bool }
    """
    win_monitors = _get_monitor_info_map()
    results = []
    
    with mss.mss() as sct:
        # sct.monitors[0] is 'all' (virtual), skip it.
        for mss_idx, mss_mon in enumerate(sct.monitors):
            if mss_idx == 0: continue
            
            matched_name = "Unknown Display"
            
            for wm in win_monitors:
                w_w = wm['rect'][2] - wm['rect'][0]
                w_h = wm['rect'][3] - wm['rect'][1]
                
                # Match based on position and size
                if (wm['rect'][0] == mss_mon['left'] and 
                    wm['rect'][1] == mss_mon['top'] and
                    w_w == mss_mon['width'] and
                    w_h == mss_mon['height']):
                    
                    matched_name = wm['name']
                    break
            
            is_primary = (mss_mon['top'] == 0 and mss_mon['left'] == 0)
            
            results.append({
                "index": mss_idx,
                "name": matched_name,
                "res": f"{mss_mon['width']}x{mss_mon['height']}",
                "primary": is_primary
            })
            
    return results
