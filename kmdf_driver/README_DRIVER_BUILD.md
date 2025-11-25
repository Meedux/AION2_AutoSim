KMDF Virtual HID Driver (AION Virtual Input)
=========================================

This folder contains a KMDF-based virtual HID driver skeleton that exposes a virtual keyboard and virtual mouse and accepts IOCTLs from user-mode applications to inject input events.

WARNING: Kernel drivers are powerful and can destabilize your system if misused. Only install and test this driver on a development machine. Do NOT use on production systems.

Files
-----
- driver.c   - Main KMDF driver C source (EvtDeviceAdd, IOCTLs, queue)
- device.h   - Public header with IOCTL definitions and shared structures
- hid_descriptor.h - HID report descriptor bytes for keyboard + mouse virtual devices
- AIONVirtualHID.inf - INF file for installing the driver
- install_driver.ps1 - Automated PowerShell helper to build, sign (test) and install the driver for testing

Build instructions (Windows with Visual Studio + WDK)
---------------------------------------------------

1) Prerequisites
   - Windows 10/11 development machine
   - Visual Studio 2019/2022 with "Desktop development with C++" workload
   - Windows Driver Kit (WDK) matching your Visual Studio version

2) Create a driver project
   - Open Visual Studio > File > New > Project > Kernel Mode Driver, Empty (KMDF)
   - Name the project "AIONVirtualHID" and point the sources at this folder (or copy files into the project)
   - Add driver.c and device.h, hid_descriptor.h to the project

3) Build
   - Use the Visual Studio configuration for your target (x64/Debug/Release) with the WDK build tools
   - The output will be a .sys file in the build output folder

4) Test-signing the driver
   - Generate a test certificate using SignTool or makecert and sign the driver (see install_driver.ps1 for automation)
   - Enable test-signing mode: run as Administrator `bcdedit /set testsigning on` and reboot

5) Install the driver
   - Use an elevated console and run `pnputil /add-driver AIONVirtualHID.inf /install` or use the included PowerShell helper script

6) Uninstall driver
   - Use pnputil to remove the driver package and reboot

Note: This sample implements an IOCTL interface and uses the Virtual HID Framework (VHF) to publish HID reports to the OS input stack so IOCTLs can create actual keyboard and mouse events. VHF integration is included in `driver.c` (VhfCreate / VhfStart / VhfReadReportSubmit). Ensure your WDK has VHF support and link against the appropriate libraries when building.

Security & stability reminder
--------------------------------
- VHF can send input events at kernel level, which can interact with focus and system security. Only test on a properly isolated development machine.
- If you plan to distribute or install on other machines, follow Microsoft driver signing and driver store best practices.
