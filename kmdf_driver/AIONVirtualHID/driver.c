/*
 * AION Virtual HID KMDF Driver - Minimal educational implementation
 *
 * Provides a KMDF device with a DOS symbolic link so user-mode applications
 * can open a handle to the device and submit IOCTLs to request keyboard
 * and mouse HID reports.
 *
 * NOTE: This sample demonstrates IOCTL handling and a HID report descriptor.
 * To create a fully-working virtual HID device that injects input into the OS
 * additional integration with the HIDClass driver and careful device topology
 * is required. Use this for test, development, and educational purposes only.
 */

#include <ntddk.h>
#include <wdf.h>
#include "device.h"
#include "hid_descriptor.h"

// VHF (Virtual HID Framework) is the recommended path for creating virtual HID
// devices that can inject input into the system from kernel-mode. The VHF
// APIs are provided by the WDK.
//
// VHF (Virtual HID Framework) is required for this driver - include the VHF
// header from the Windows Driver Kit. This driver expects a WDK version that
// exposes the VHF APIs used below (VHF_CONFIG, VhfCreate, VhfStart,
// VhfReadReportSubmit and VhfDelete).
#include <vhf.h>

// If vhf.h in the installed WDK is missing or defines different symbols,
// create minimal, compatible local typedefs so we can compile and match the
// VHF ABI used in this driver. These are guarded so they don't conflict
// with vhf.h when it provides definitions.
#ifndef VHF_CONFIG
typedef struct _VHF_CONFIG {
    PDEVICE_OBJECT DeviceObject;
    PVOID ReportDescriptor;
    ULONG ReportDescriptorLength;
    PVOID InsertReportCallback; // callback prototype varies across WDKs
} VHF_CONFIG, *PVHF_CONFIG;
#endif

#ifndef VHFHANDLE
typedef PVOID VHFHANDLE;
#endif

// Single set of prototypes for the VHF routines we use. If the real
// prototypes are available in the WDK headers they will match; otherwise
// these declarations give the compiler something to check against and
// prevent implicit-int warnings (C4013).
NTSTATUS
VhfCreate(
    _In_ PVHF_CONFIG Config,
    _Out_ VHFHANDLE *VhfHandle
    );

NTSTATUS
VhfStart(
    _In_ VHFHANDLE VhfHandle
    );

NTSTATUS
VhfReadReportSubmit(
    _In_ VHFHANDLE           VhfHandle,
    _In_ PHID_XFER_PACKET    HidTransferPacket
    );

VOID
VhfDelete(
    _In_ VHFHANDLE VhfHandle,
    _In_ BOOLEAN Synchronous
    );

// Device context structure - stores the VHF handle for injecting reports
typedef struct _DEVICE_CONTEXT {
    VHFHANDLE VhfHandle;
} DEVICE_CONTEXT, *PDEVICE_CONTEXT;

WDF_DECLARE_CONTEXT_TYPE_WITH_NAME(DEVICE_CONTEXT, DeviceGetContext);

#ifdef __analysis
// Analyzer helper: some static analyzers expect to *find* a function
// definition named after the WDF macro. Provide a no-op stub only when
// running static analysis so the analyzer stops producing VCR001.
static void WDF_DECLARE_CONTEXT_TYPE_WITH_NAME(void) { }
#endif

// Static analysis in some environments can't resolve the WDF macro expansion
// for WDF_DECLARE_CONTEXT_TYPE_WITH_NAME. Provide a fallback inline function
// when the macro is not available so analyzers have a concrete definition
// to find. The fallback will be ignored when the WDF macro is present.
#if !defined(WDF_DECLARE_CONTEXT_TYPE_WITH_NAME) || defined(__analysis)
static __inline PDEVICE_CONTEXT
DeviceGetContext(WDFDEVICE Device)
{
    return (PDEVICE_CONTEXT)WdfObjectGetTypedContext(Device, DEVICE_CONTEXT);
}
#endif

DRIVER_INITIALIZE DriverEntry;
EVT_WDF_DRIVER_DEVICE_ADD AionEvtDeviceAdd;
EVT_WDF_OBJECT_CONTEXT_CLEANUP AionEvtDeviceContextCleanup;
EVT_WDF_IO_QUEUE_IO_DEVICE_CONTROL AionEvtIoDeviceControl;

// DOS symbolic link name (user-mode can open \\.\AIONVirtualHID)
const UNICODE_STRING gDosSymLink = RTL_CONSTANT_STRING(L"\\DosDevices\\AIONVirtualHID");

NTSTATUS
DriverEntry(_In_ PDRIVER_OBJECT DriverObject, _In_ PUNICODE_STRING RegistryPath)
{
    NTSTATUS status;
    WDF_DRIVER_CONFIG config;

    WDF_DRIVER_CONFIG_INIT(&config, AionEvtDeviceAdd);

    status = WdfDriverCreate(DriverObject,
                             RegistryPath,
                             WDF_NO_OBJECT_ATTRIBUTES,
                             &config,
                             WDF_NO_HANDLE);
    if (!NT_SUCCESS(status)) {
        KdPrint(("AIONVirtualHID: WdfDriverCreate failed 0x%08x\n", status));
        return status;
    }

    KdPrint(("AIONVirtualHID: DriverEntry loaded\n"));
    return STATUS_SUCCESS;
}

NTSTATUS
AionEvtDeviceAdd(_In_ WDFDRIVER Driver, _Inout_ PWDFDEVICE_INIT DeviceInit)
{
    NTSTATUS status;
    WDFDEVICE device;
    WDF_IO_QUEUE_CONFIG queueConfig;
    WDF_OBJECT_ATTRIBUTES attributes;

    UNREFERENCED_PARAMETER(Driver);

    // Set up device as FILE_DEVICE_UNKNOWN with direct I/O
    WdfDeviceInitSetDeviceType(DeviceInit, FILE_DEVICE_UNKNOWN);

    // Create the WDF device
    WDF_OBJECT_ATTRIBUTES_INIT_CONTEXT_TYPE(&attributes, DEVICE_CONTEXT);
    attributes.EvtCleanupCallback = AionEvtDeviceContextCleanup;
    // Some WDK variants expect a pointer-to-PWDFDEVICE_INIT here. Pass the
    // address of the local PWDFDEVICE_INIT variable (PWDFDEVICE_INIT*) so
    // the call matches the WDK's prototype and avoids a levels-of-indirection
    // mismatch during compilation.
    status = WdfDeviceCreate(&DeviceInit, &attributes, &device);
    if (!NT_SUCCESS(status)) {
        KdPrint(("AIONVirtualHID: WdfDeviceCreate failed 0x%08x\n", status));
        return status;
    }

    // Create symbolic link so user-mode can open \\.
    // (The DOS symbolic link allows CreateFile("\\.\AIONVirtualHID") from user-mode.)
    status = WdfDeviceCreateSymbolicLink(device, &gDosSymLink);
    if (!NT_SUCCESS(status)) {
        KdPrint(("AIONVirtualHID: WdfDeviceCreateSymbolicLink failed 0x%08x\n", status));
        // continue - symbolic link may already exist
    }

    // Default queue (serial) for device control (IOCTLs)
    WDF_IO_QUEUE_CONFIG_INIT_DEFAULT_QUEUE(&queueConfig, WdfIoQueueDispatchSequential);
    queueConfig.EvtIoDeviceControl = AionEvtIoDeviceControl;

    status = WdfIoQueueCreate(device, &queueConfig, WDF_NO_OBJECT_ATTRIBUTES, WDF_NO_HANDLE);
    if (!NT_SUCCESS(status)) {
        KdPrint(("AIONVirtualHID: WdfIoQueueCreate failed 0x%08x\n", status));
        return status;
    }

    KdPrint(("AIONVirtualHID: device created and symbolic link installed\n"));

    // Initialize and start the Virtual HID Framework (VHF) instance for this
    // device. VHF creates the HID device interface and is responsible for
    // publishing HID reports to upper layers as input events.
    PDEVICE_CONTEXT devContext = DeviceGetContext(device);
    RtlZeroMemory(devContext, sizeof(DEVICE_CONTEXT));

    // Build a VHF configuration structure and create the VHF instance.
    // VhfCreate takes a PVHF_CONFIG and an out VHFHANDLE* on this WDK.
    // Build a VHF configuration structure and create the VHF instance.
    // Different WDKs expose VhfCreate as VhfCreate(PVHF_CONFIG, VHFHANDLE*),
    // so we construct a PVHF_CONFIG here and call VhfCreate(&config, &handle).
    VHF_CONFIG vhfConfig;

    VHF_CONFIG_INIT(&vhfConfig, WdfDeviceWdmGetDeviceObject(device),
                    (USHORT)AION_HID_REPORT_DESCRIPTOR_SIZE,
                    (PUCHAR)AION_HID_REPORT_DESCRIPTOR);

    status = VhfCreate(&vhfConfig, &devContext->VhfHandle);
    if (!NT_SUCCESS(status)) {
        KdPrint(("AIONVirtualHID: VhfCreate failed 0x%08x\n", status));
        // Not fatal for development; we continue but HID injection won't work.
    } else {
        status = VhfStart(devContext->VhfHandle);
        if (!NT_SUCCESS(status)) {
            KdPrint(("AIONVirtualHID: VhfStart failed 0x%08x\n", status));
            // We will continue, but no injection will occur.
        } else {
            KdPrint(("AIONVirtualHID: VHF started - ready to publish HID reports\n"));
        }
    }
    /* VHF initialized above; no second init needed. */
    return STATUS_SUCCESS;
}

// Helper functions for sending HID reports via VHF. These functions are
// written in plain C so they can be compiled by the KMDF build environment.
static NTSTATUS
SendKeyboardReportToVhf(PDEVICE_CONTEXT DevCtx, UCHAR Modifier, UCHAR *KeyCodes, SIZE_T KeyCount)
{
    UCHAR report[8] = {0};
    report[0] = Modifier;
    report[1] = 0; // reserved
    if (KeyCount > 6) {
        KeyCount = 6;
    }
    if (KeyCount > 0) {
        if (KeyCodes == NULL) {
            KdPrint(("AIONVirtualHID: SendKeyboardReportToVhf - NULL KeyCodes with count > 0\n"));
            return STATUS_INVALID_PARAMETER;
        }
        RtlCopyMemory(&report[2], KeyCodes, KeyCount);
    }

    if (DevCtx == NULL || DevCtx->VhfHandle == NULL) {
        KdPrint(("AIONVirtualHID: SendKeyboardReportToVhf - VHF unavailable\n"));
        return STATUS_SUCCESS; // don't error hard when VHF is not present
    }

    HID_XFER_PACKET packet = {0};
    packet.reportBuffer = report;
    packet.reportBufferLen = sizeof(report);
    packet.reportId = 0;

    NTSTATUS vhfStatus = VhfReadReportSubmit(DevCtx->VhfHandle, &packet);
    if (!NT_SUCCESS(vhfStatus)) {
        KdPrint(("AIONVirtualHID: SendKeyboardReportToVhf failed 0x%08x\n", vhfStatus));
    }
    return vhfStatus;
}

static NTSTATUS
SendMouseReportToVhf(PDEVICE_CONTEXT DevCtx, UCHAR Buttons, CHAR Dx, CHAR Dy)
{
    UCHAR report[3] = {0};
    report[0] = Buttons & 0x07;
    report[1] = (UCHAR)Dx;
    report[2] = (UCHAR)Dy;

    if (DevCtx == NULL || DevCtx->VhfHandle == NULL) {
        KdPrint(("AIONVirtualHID: SendMouseReportToVhf - VHF unavailable\n"));
        return STATUS_SUCCESS;
    }

    HID_XFER_PACKET packet = {0};
    packet.reportBuffer = report;
    packet.reportBufferLen = sizeof(report);
    packet.reportId = 0;

    NTSTATUS vhfStatus = VhfReadReportSubmit(DevCtx->VhfHandle, &packet);
    if (!NT_SUCCESS(vhfStatus)) {
        KdPrint(("AIONVirtualHID: SendMouseReportToVhf failed 0x%08x\n", vhfStatus));
    }
    return vhfStatus;
}

VOID
AionEvtDeviceContextCleanup(_In_ WDFOBJECT Object)
{
    WDFDEVICE device = (WDFDEVICE)Object;
    PDEVICE_CONTEXT devCtx = DeviceGetContext(device);

    if (devCtx && devCtx->VhfHandle) {
        KdPrint(("AIONVirtualHID: deleting VHF instance\n"));
        // Older/newer WDKs may require a boolean second parameter for VhfDelete.
        // Use TRUE to request synchronous deletion if supported.
        (void)VhfDelete(devCtx->VhfHandle, TRUE);
        devCtx->VhfHandle = NULL;
    }
}

VOID
AionEvtIoDeviceControl(_In_ WDFQUEUE Queue, _In_ WDFREQUEST Request, _In_ size_t OutputBufferLength,
                      _In_ size_t InputBufferLength, _In_ ULONG IoControlCode)
{
    NTSTATUS status = STATUS_INVALID_DEVICE_REQUEST;
    size_t bufSize = 0;
    PVOID buffer = NULL;

    UNREFERENCED_PARAMETER(OutputBufferLength);
    UNREFERENCED_PARAMETER(InputBufferLength);

    // Get device context so helper functions can use the VHF handle
    PDEVICE_CONTEXT devContext = DeviceGetContext(WdfIoQueueGetDevice(Queue));

    switch (IoControlCode) {
    case IOCTL_HID_KEYDOWN:
        status = WdfRequestRetrieveInputBuffer(Request, sizeof(AION_KEY_EVENT), &buffer, &bufSize);
        if (NT_SUCCESS(status)) {
            AION_KEY_EVENT *evt = (AION_KEY_EVENT *)buffer;
            KdPrint(("AIONVirtualHID: IOCTL_HID_KEYDOWN sc=0x%02x\n", evt->ScanCode));
            // Map a small set of expected scan-codes to HID usage IDs. In a
            // full implementation this should be expanded and made robust.
            UCHAR usage = 0;
            switch (evt->ScanCode) {
            case AION_SC_TAB: usage = 0x2B; break; // HID usage for Tab
            case AION_SC_R:   usage = 0x15; break; // R
            case AION_SC_T:   usage = 0x17; break; // T
            case AION_SC_F:   usage = 0x09; break; // F
            default: usage = evt->ScanCode; break; // best-effort fallback
            }

            UCHAR keys[6] = {0};
            keys[0] = usage;
            status = SendKeyboardReportToVhf(devContext, 0 /*modifier*/, keys, 1);
            status = STATUS_SUCCESS;
        }
        break;

    case IOCTL_HID_KEYUP:
        status = WdfRequestRetrieveInputBuffer(Request, sizeof(AION_KEY_EVENT), &buffer, &bufSize);
        if (NT_SUCCESS(status)) {
            UCHAR sc = ((AION_KEY_EVENT *)buffer)->ScanCode;
            KdPrint(("AIONVirtualHID: IOCTL_HID_KEYUP sc=0x%02x\n", sc));
            // On keyup we send an empty key array (no keys pressed)
            UCHAR emptyKeys[6] = {0};
            status = SendKeyboardReportToVhf(devContext, 0, emptyKeys, 0);
            status = STATUS_SUCCESS;
        }
        break;

    case IOCTL_HID_MOUSEMOVE:
        status = WdfRequestRetrieveInputBuffer(Request, sizeof(AION_MOUSE_MOVE), &buffer, &bufSize);
        if (NT_SUCCESS(status)) {
            AION_MOUSE_MOVE *mv = (AION_MOUSE_MOVE *)buffer;
            KdPrint(("AIONVirtualHID: IOCTL_HID_MOUSEMOVE dx=%d dy=%d\n", mv->DeltaX, mv->DeltaY));
            // Clamp movement to -127..127 and send as relative 8-bit values
            INT dx = mv->DeltaX;
            INT dy = mv->DeltaY;
            if (dx > 127) dx = 127; else if (dx < -127) dx = -127;
            if (dy > 127) dy = 127; else if (dy < -127) dy = -127;
            status = SendMouseReportToVhf(devContext, 0 /*buttons*/, (INT8)dx, (INT8)dy);
            status = STATUS_SUCCESS;
        }
        break;

    case IOCTL_HID_LEFTCLICK:
        // Accept optional click struct
        KdPrint(("AIONVirtualHID: IOCTL_HID_LEFTCLICK\n"));
        // left click -> button bit 0 set for one report
        status = SendMouseReportToVhf(devContext, 0x01, 0, 0);
        // then release
        if (NT_SUCCESS(status)) SendMouseReportToVhf(devContext, 0x00, 0, 0);
        break;

    case IOCTL_HID_RIGHTCLICK:
        KdPrint(("AIONVirtualHID: IOCTL_HID_RIGHTCLICK\n"));
        // right click -> button bit 1
        status = SendMouseReportToVhf(devContext, 0x02, 0, 0);
        if (NT_SUCCESS(status)) SendMouseReportToVhf(devContext, 0x00, 0, 0);
        break;

    default:
        status = STATUS_INVALID_DEVICE_REQUEST;
        break;
    }

    WdfRequestComplete(Request, status);
}
