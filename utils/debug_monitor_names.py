import ctypes
from ctypes import wintypes
import mss

def get_display_names():
    user32 = ctypes.windll.user32
    # EnumDisplayDevicesW is the Unicode version
    # https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumdisplaydevicesw
    
    DISPLAY_DEVICE_ATTACHED_TO_DESKTOP = 0x00000001
    
    class DISPLAY_DEVICE(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("DeviceName", wintypes.WCHAR * 32),
            ("DeviceString", wintypes.WCHAR * 128),
            ("StateFlags", wintypes.DWORD),
            ("DeviceID", wintypes.WCHAR * 128),
            ("DeviceKey", wintypes.WCHAR * 128),
        ]

    monitors_info = []
    
    # 1. Enumerate Adapters (Graphics Cards / Outputs)
    i = 0
    while True:
        adapter = DISPLAY_DEVICE()
        adapter.cb = ctypes.sizeof(adapter)
        if not user32.EnumDisplayDevicesW(None, i, ctypes.byref(adapter), 0):
            break
        
        if adapter.StateFlags & DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            # 2. For each active adapter, get the Monitor connected to it
            # We call EnumDisplayDevices again, passing the Adapter Name
            j = 0
            while True:
                monitor = DISPLAY_DEVICE()
                monitor.cb = ctypes.sizeof(monitor)
                if not user32.EnumDisplayDevicesW(adapter.DeviceName, j, ctypes.byref(monitor), 0):
                    break
                
                # This 'monitor' struct now contains the actual screen name (e.g., "Dell U2415")
                monitors_info.append({
                    "adapter_device": adapter.DeviceName,
                    "monitor_name": monitor.DeviceString,
                    "device_id": monitor.DeviceID
                })
                j += 1
        i += 1
        
    return monitors_info

def list_mss_and_names():
    print("--- MSS Monitors (Geometry) ---")
    with mss.mss() as sct:
        for idx, mon in enumerate(sct.monitors):
            print(f"Index {idx}: {mon}")
            
    print("\n--- Windows API (Names) ---")
    names = get_display_names()
    for n in names:
        print(f"Name: {n['monitor_name']} | Adapter: {n['adapter_device']}")

if __name__ == "__main__":
    list_mss_and_names()
