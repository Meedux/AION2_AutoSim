/*
 * AION Virtual HID Driver - Public header for IOCTLs
 * This header is consumed by both the KMDF driver and the user-mode Python code.
 */

#pragma once

// device.h is a shared header for both the kernel driver and user-mode
// code. Don't include <windows.h> here (that pulls in user-mode headers
// and breaks kernel builds). Use fixed-width types and a GUID string so
// both driver and user-mode code can consume the file safely.

// Avoid including the C runtime header when building the kernel driver.
// Including <stdint.h> in kernel-mode can pull in vcruntime headers
// which produce redefinition warnings under the WDK build. Provide a
// lightweight fallback for kernel-mode builds and use stdint.h for
// user-mode builds.
#if defined(_KERNEL_MODE) || defined(KERNEL_MODE) || defined(_WDFDDK_) || defined(_WDMDDK_)
    // WDK kernel headers provide fixed-width integer types via ntddk/ntdef
    #include <ntddk.h>
    typedef UCHAR uint8_t;
    typedef INT32 int32_t;
#else
    #include <stdint.h>
#endif

// Public device interface GUID (string form). If you need the C GUID value
// in user-mode or kernel-mode, create the GUID from this string where
// appropriate (user-mode can use DEFINE_GUID or IIDFromString).
#define AION_DEVINTERFACE_GUID_STR "{E1A1D2F7-7E20-4B9E-8E6A-1A8F8C3C9C01}"

// Device type for IOCTLs
#define FILE_DEVICE_AION_VIRTUAL_HID  0x8000

// IOCTL function codes
#define IOCTL_HID_KEYDOWN   CTL_CODE(FILE_DEVICE_AION_VIRTUAL_HID, 0x801, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_HID_KEYUP     CTL_CODE(FILE_DEVICE_AION_VIRTUAL_HID, 0x802, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_HID_MOUSEMOVE CTL_CODE(FILE_DEVICE_AION_VIRTUAL_HID, 0x803, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_HID_LEFTCLICK CTL_CODE(FILE_DEVICE_AION_VIRTUAL_HID, 0x804, METHOD_BUFFERED, FILE_ANY_ACCESS)
#define IOCTL_HID_RIGHTCLICK CTL_CODE(FILE_DEVICE_AION_VIRTUAL_HID, 0x805, METHOD_BUFFERED, FILE_ANY_ACCESS)

// Keyboard scan codes supported (driver will interpret scancodes and send keyboard HID reports)
// We'll define a small enum for convenience
typedef enum _AION_KEY_SCANCODE {
    AION_SC_TAB = 0x0F,    // USB HID Boot Keyboard uses 0x2B for Tab in usage-id; we use scan-code style here for simplicity
    AION_SC_R   = 0x15,    // placeholder - driver supports scancode values supplied by user
    AION_SC_T   = 0x14,
    AION_SC_F   = 0x09
} AION_KEY_SCANCODE;

// Key event buffer
typedef struct _AION_KEY_EVENT {
    uint8_t ScanCode; // Scancode value - limited to the keys above for safety
    uint8_t Padding;  // reserved
} AION_KEY_EVENT, *PAION_KEY_EVENT;

// Mouse move buffer
typedef struct _AION_MOUSE_MOVE {
    int32_t DeltaX;   // relative movement in pixels (signed)
    int32_t DeltaY;   // relative movement in pixels (signed)
} AION_MOUSE_MOVE, *PAION_MOUSE_MOVE;

// Mouse click buffer - no input data required but keep struct for future flags
typedef struct _AION_MOUSE_CLICK {
    uint8_t Reserved;
} AION_MOUSE_CLICK, *PAION_MOUSE_CLICK;
