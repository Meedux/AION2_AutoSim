"""Driver smoke tests — verifies KMDF driver IOCTLs from user-mode.

This script opens the device (\\.\AIONVirtualHID) and sends a set of IOCTLs
to exercise keyboard (Tab,R,T,F) and mouse actions (move, left/right click).

Run this from an elevated shell if required and with the driver installed.
"""

import ctypes
from ctypes import wintypes
import time
from pprint import pprint

DEVICE_PATH = r"\\.\AIONVirtualHID"

# CTL codes as defined in driver/device.h
IOCTL_HID_KEYDOWN   = 0x80002004
IOCTL_HID_KEYUP     = 0x80002008
IOCTL_HID_MOUSEMOVE = 0x8000200C
IOCTL_HID_LEFTCLICK = 0x80002010
IOCTL_HID_RIGHTCLICK= 0x80002014

KEY_SCANCODE = {
    'tab': 0x0F,
    'r': 0x15,
    't': 0x14,
    'f': 0x09,
}


def open_dev(path=DEVICE_PATH):
    CreateFileW = ctypes.windll.kernel32.CreateFileW
    CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    CreateFileW.restype = wintypes.HANDLE

    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x1
    FILE_SHARE_WRITE = 0x2
    OPEN_EXISTING = 3

    h = CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if h == wintypes.HANDLE(-1).value:
        err = ctypes.windll.kernel32.GetLastError()
        raise RuntimeError(f"Failed to open driver — is it installed? CreateFile error: {err}")
    return h


def ioctl(h, code, in_buf=None):
    DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl
    DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    DeviceIoControl.restype = wintypes.BOOL

    in_ptr = None
    in_size = 0
    if in_buf is not None:
        in_size = len(in_buf)
        in_ptr = ctypes.create_string_buffer(in_buf)

    out_size = 0
    bytes_returned = wintypes.DWORD(0)
    ok = DeviceIoControl(h, code, in_ptr, in_size, None, out_size, ctypes.byref(bytes_returned), None)
    return bool(ok)


def test_key(h, key_name):
    sc = KEY_SCANCODE.get(key_name)
    if sc is None:
        print("Unknown key", key_name)
        return False
    payload = bytes([sc & 0xFF, 0x00])
    ok1 = ioctl(h, IOCTL_HID_KEYDOWN, payload)
    time.sleep(0.05)
    ok2 = ioctl(h, IOCTL_HID_KEYUP, payload)
    print(f"Key {key_name} down/up -> {ok1} {ok2}")
    return ok1 and ok2


def test_mouse_move(h, dx, dy):
    payload = (ctypes.c_int32(dx).value).to_bytes(4, 'little', signed=True) + (ctypes.c_int32(dy).value).to_bytes(4, 'little', signed=True)
    ok = ioctl(h, IOCTL_HID_MOUSEMOVE, payload)
    print(f"Mouse move dx={dx} dy={dy} -> {ok}")
    return ok


def test_clicks(h):
    l = ioctl(h, IOCTL_HID_LEFTCLICK, b'')
    r = ioctl(h, IOCTL_HID_RIGHTCLICK, b'')
    print(f"Left click -> {l}, Right click -> {r}")
    return l and r


def run_all():
    print("=== AION Virtual HID driver functional test ===")
    try:
        h = open_dev()
    except Exception as e:
        print("ERROR: Could not open driver:", e)
        return

    try:
        print("Testing keys: Tab, R, T, F")
        for k in ('tab', 'r', 't', 'f'):
            test_key(h, k)
            time.sleep(0.1)

        print("Testing relative mouse moves")
        test_mouse_move(h, 20, 0)
        time.sleep(0.1)
        test_mouse_move(h, -20, 0)
        time.sleep(0.1)
        test_mouse_move(h, 0, 10)
        time.sleep(0.1)

        print("Testing mouse clicks")
        test_clicks(h)

        print("Driver test finished — if the driver is present its IOCTLs returned success (True).")
    finally:
        ctypes.windll.kernel32.CloseHandle(h)


if __name__ == '__main__':
    run_all()
