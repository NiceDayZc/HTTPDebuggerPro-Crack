import os
import sys
import time
import psutil
import winreg
import re
import ctypes
from ctypes import wintypes
import colorama
from colorama import Fore, Style

colorama.init()

def terminate_process(process_name):
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                proc.terminate()
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def is_process_running(process_name):
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def get_app_version(k):
    try:
        version = winreg.QueryValueEx(k, "AppVer")[0]
        parsed_version = re.search(r'(\d+.*)', version).group(1)
        parsed_version = parsed_version.replace('.', '')
        return parsed_version
    except Exception as e:
        print(f"[{Fore.RED}-{Style.RESET_ALL}] Error getting App Version: {e}")
        sys.exit(1)

def get_volume_serial_number():
    volumeNameBuffer = ctypes.create_unicode_buffer(1024)
    fileSystemNameBuffer = ctypes.create_unicode_buffer(1024)
    serial_number = wintypes.DWORD()
    max_component_length = wintypes.DWORD()
    file_system_flags = wintypes.DWORD()

    res = ctypes.windll.kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p("C:\\"),
        volumeNameBuffer,
        ctypes.wintypes.DWORD(len(volumeNameBuffer)),
        ctypes.byref(serial_number),
        ctypes.byref(max_component_length),
        ctypes.byref(file_system_flags),
        fileSystemNameBuffer,
        ctypes.wintypes.DWORD(len(fileSystemNameBuffer))
    )

    if res == 0:
        raise ctypes.WinError()

    return serial_number.value

def get_serial_number(app_version):
    volume_serial = get_volume_serial_number()
    app_version_int = int(app_version)

    volume_serial &= 0xFFFFFFFF
    app_version_int &= 0xFFFFFFFF

    tmp = (~volume_serial) & 0xFFFFFFFF
    tmp = (tmp >> 1) & 0xFFFFFFFF
    tmp = (tmp + 0x2E0) & 0xFFFFFFFF

    serial_number = (app_version_int ^ tmp ^ 0x590D4) & 0xFFFFFFFF

    return str(serial_number)

def generate_random_bytes():
    b = os.urandom(3)
    return b[0], b[1], b[2]

def create_key():
    while True:
        v1, v2, v3 = generate_random_bytes()
        key = "{:02X}{:02X}{:02X}7C{:02X}{:02X}{:02X}{:02X}".format(
            v1,
            v2 ^ 0x7C,
            0xFF ^ v1,
            v2,
            v3 % 255,
            (v3 % 255) ^ 7,
            v1 ^ (0xFF ^ (v3 % 255))
        )
        if len(key) == 16:
            return key

def write_key(k, sn, key):
    winreg.SetValueEx(k, "SN" + sn, 0, winreg.REG_SZ, key)

def crack(k):
    av = get_app_version(k)
    sn = get_serial_number(av)
    key = create_key()
    write_key(k, sn, key)
    return av, sn, key

def main():
    terminate_process("HTTPDebuggerUI.exe")

    key_path = r'SOFTWARE\MadeForNet\HTTPDebuggerPro'
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except FileNotFoundError:
        print(f"[{Fore.RED}-{Style.RESET_ALL}] Registry key not found.")
        sys.exit(1)
    except Exception as e:
        print(f"[{Fore.RED}-{Style.RESET_ALL}] Error opening registry key: {e}")
        sys.exit(1)

    av, sn, key = crack(k)
    print("Crack Successful!")
    print("----------------------------")
    print(f"[{Fore.GREEN}+{Style.RESET_ALL}] App Version   : {av}")
    print(f"[{Fore.GREEN}+{Style.RESET_ALL}] Serial Number : {sn}")
    print(f"[{Fore.GREEN}+{Style.RESET_ALL}] Key           : {key}")
    print("----------------------------")
    print("Please open HTTP Debugger Pro to apply changes.")

    while not is_process_running("HTTPDebuggerUI.exe"):
        time.sleep(0.5)

    input()

if __name__ == "__main__":
    main()
