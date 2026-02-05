import sounddevice as sd
from colorama import Fore

def get_wasapi_input_devices():
    """Returns a list of tuples (id, name) for all WASAPI input devices."""
    devices = sd.query_devices()
    host_apis = sd.query_hostapis()
    
    wasapi_api_idx = next((i for i, api in enumerate(host_apis) if "WASAPI" in api["name"]), None)
    
    if wasapi_api_idx is None:
        return []

    input_devices = []
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0 and dev['hostapi'] == wasapi_api_idx:
            input_devices.append((i, dev['name']))
    
    return input_devices

def select_audio_device_cli():
    """Interactive CLI for selecting a WASAPI input device."""
    print(f"{Fore.YELLOW}[i] Scanning for WASAPI Audio Input Devices...")
    input_devices = get_wasapi_input_devices()

    if not input_devices:
        print(f"{Fore.RED}[!] No WASAPI input devices found.")
        return None

    print(f"\n{Fore.WHITE}Available WASAPI Input Devices:")
    for idx, (dev_id, name) in enumerate(input_devices):
        print(f"  {Fore.GREEN}[{idx}] {Fore.WHITE}{name} (ID: {dev_id})")

    while True:
        try:
            choice = input(f"\n{Fore.YELLOW}Select device index [0-{len(input_devices)-1}]: ")
            selected_idx = int(choice)
            if 0 <= selected_idx < len(input_devices):
                dev_id, dev_name = input_devices[selected_idx]
                print(f"{Fore.GREEN}[+] Selected: {dev_name} (WASAPI)")
                sd.default.device = (dev_id, None)
                return dev_id
        except ValueError:
            print(f"{Fore.RED}[!] Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            return None
