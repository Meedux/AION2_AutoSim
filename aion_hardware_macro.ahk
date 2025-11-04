; ============================================================================
; AION Hardware-Level Input Macro
; ============================================================================
; This script provides hardware-level keyboard and mouse inputs for AION
; Uses the most reliable input methods that games cannot easily block
;
; USAGE:
;   1. Run this script (it will stay in system tray)
;   2. Focus the AION game window
;   3. Use the hotkeys below or call functions from Python
;
; HOTKEYS (for manual testing):
;   F9  - Test key press (W key)
;   F10 - Test mouse click at cursor
;   F11 - Toggle script on/off
;   F12 - Reload script
; ============================================================================

#NoEnv
#SingleInstance Force
SetWorkingDir %A_ScriptDir%

; ============================================================================
; INPUT CONFIGURATION - Optimized for AION
; ============================================================================

; SendMode Input is the fastest and most reliable for games
SendMode Input

; Add small delays to mimic human input - critical for anti-cheat
SetKeyDelay, 10, 10        ; Delay between keystrokes (press, release)
SetMouseDelay, 10           ; Delay between mouse events

; Set coordinate mode to screen (absolute coordinates)
CoordMode, Mouse, Screen
CoordMode, Pixel, Screen

; Script state
global ScriptEnabled := true
global GameWindowTitle := "AION"  ; Adjust if needed
global GameWindowClass := ""      ; Will auto-detect

; ============================================================================
; STARTUP
; ============================================================================

; Show startup notification
TrayTip, AION Macro, Script loaded and ready!, 3, 1

; Auto-detect AION window on startup
DetectAIONWindow()

Return  ; End of auto-execute section

; ============================================================================
; WINDOW DETECTION
; ============================================================================

DetectAIONWindow() {
    global GameWindowTitle, GameWindowClass
    
    ; Try to find AION window
    WinGet, id, List, %GameWindowTitle%
    if (id > 0) {
        WinGetClass, GameWindowClass, ahk_id %id1%
        TrayTip, AION Macro, AION window detected!, 2, 1
        return true
    }
    
    ; Try alternative window titles
    WinGet, id, List, Aion
    if (id > 0) {
        WinGetClass, GameWindowClass, ahk_id %id1%
        GameWindowTitle := "Aion"
        TrayTip, AION Macro, AION window detected!, 2, 1
        return true
    }
    
    return false
}

; ============================================================================
; WINDOW ACTIVATION - Ensures AION is focused
; ============================================================================

ActivateGameWindow() {
    global GameWindowTitle, GameWindowClass
    
    ; Try to activate by title
    WinActivate, %GameWindowTitle%
    WinWaitActive, %GameWindowTitle%,, 1
    if (ErrorLevel) {
        ; Try by class if title fails
        if (GameWindowClass != "") {
            WinActivate, ahk_class %GameWindowClass%
            WinWaitActive, ahk_class %GameWindowClass%,, 1
        }
    }
    
    Sleep, 100  ; Give window time to fully activate
    return !ErrorLevel
}

; ============================================================================
; KEYBOARD INPUT FUNCTIONS
; ============================================================================

; Send a single key press (hardware-level)
SendKey(key, presses := 1, interval := 50) {
    global ScriptEnabled
    
    if (!ScriptEnabled)
        return
    
    ; Activate game window first
    ActivateGameWindow()
    
    Loop, %presses% {
        ; Use Send (Input mode) for hardware-level input
        Send, {%key%}
        
        if (presses > 1 && A_Index < presses)
            Sleep, %interval%
    }
}

; Send key with modifiers (e.g., Ctrl+C, Shift+1)
SendKeyWithModifier(modifier, key) {
    global ScriptEnabled
    
    if (!ScriptEnabled)
        return
    
    ActivateGameWindow()
    
    ; Hold modifier, press key, release
    Send, {%modifier% down}{%key%}{%modifier% up}
}

; Hold key down for duration (milliseconds)
HoldKey(key, duration := 1000) {
    global ScriptEnabled
    
    if (!ScriptEnabled)
        return
    
    ActivateGameWindow()
    
    Send, {%key% down}
    Sleep, %duration%
    Send, {%key% up}
}

; Type a string (for chat, etc.)
TypeString(text) {
    global ScriptEnabled
    
    if (!ScriptEnabled)
        return
    
    ActivateGameWindow()
    SendInput, %text%
}

; ============================================================================
; MOUSE INPUT FUNCTIONS
; ============================================================================

; Move mouse to absolute screen coordinates
MoveMouse(x, y, speed := 0) {
    global ScriptEnabled
    
    if (!ScriptEnabled)
        return
    
    ; Speed 0 = instant, 1-100 = gradual movement
    MouseMove, %x%, %y%, %speed%
}

; Click at specific coordinates
ClickAt(x, y, button := "Left", clicks := 1) {
    global ScriptEnabled
    
    if (!ScriptEnabled)
        return
    
    ActivateGameWindow()
    
    ; Move to position
    MouseMove, %x%, %y%, 0
    Sleep, 50
    
    ; Perform click(s)
    if (button = "Left") {
        Loop, %clicks% {
            Click, Left
            if (clicks > 1 && A_Index < clicks)
                Sleep, 50
        }
    }
    else if (button = "Right") {
        Click, Right
    }
    else if (button = "Middle") {
        Click, Middle
    }
}

; Double-click at coordinates
DoubleClickAt(x, y) {
    global ScriptEnabled
    
    if (!ScriptEnabled)
        return
    
    ActivateGameWindow()
    
    MouseMove, %x%, %y%, 0
    Sleep, 50
    Click, Left, 2  ; Double-click
}

; Drag mouse from one point to another
DragMouse(x1, y1, x2, y2, button := "Left") {
    global ScriptEnabled
    
    if (!ScriptEnabled)
        return
    
    ActivateGameWindow()
    
    MouseMove, %x1%, %y1%, 0
    Sleep, 50
    
    Click, %button%, Down
    Sleep, 50
    
    MouseMove, %x2%, %y2%, 5
    Sleep, 50
    
    Click, %button%, Up
}

; ============================================================================
; HOTKEYS FOR MANUAL TESTING
; ============================================================================

; F9 - Test key press (W key)
F9::
    SendKey("w")
    TrayTip, AION Macro, Sent W key, 1, 1
Return

; F10 - Test mouse click at current cursor position
F10::
    MouseGetPos, mx, my
    ClickAt(mx, my, "Left", 1)
    TrayTip, AION Macro, Clicked at cursor position, 1, 1
Return

; F11 - Toggle script on/off
F11::
    ScriptEnabled := !ScriptEnabled
    if (ScriptEnabled) {
        TrayTip, AION Macro, Script ENABLED, 2, 1
    } else {
        TrayTip, AION Macro, Script DISABLED, 2, 1
    }
Return

; F12 - Reload script
F12::
    TrayTip, AION Macro, Reloading script..., 1, 1
    Reload
Return

; ============================================================================
; PYTHON INTEGRATION - COM Interface
; ============================================================================
; These functions can be called from Python using ahk library
; Example: ahk.call('SendKey', 'w', 1, 50)

; Expose functions for Python
#Include *i %A_ScriptDir%\ahk_python_bridge.ahk

; ============================================================================
; UTILITY FUNCTIONS
; ============================================================================

; Get current mouse position
GetMousePos() {
    MouseGetPos, mx, my
    return mx "," my
}

; Check if game window is active
IsGameActive() {
    global GameWindowTitle
    WinGetActiveTitle, activeTitle
    if (InStr(activeTitle, GameWindowTitle)) {
        return true
    }
    return false
}

; Wait for specific pixel color (for detection)
WaitForPixelColor(x, y, color, timeout := 5000) {
    endTime := A_TickCount + timeout
    Loop {
        PixelGetColor, pixelColor, %x%, %y%
        if (pixelColor = color)
            return true
        if (A_TickCount > endTime)
            return false
        Sleep, 100
    }
}

; ============================================================================
; EMERGENCY STOP - ESC key
; ============================================================================

; Double-tap ESC to emergency stop all macros
~Esc::
    if (A_PriorHotkey = "~Esc" && A_TimeSincePriorHotkey < 500) {
        ScriptEnabled := false
        TrayTip, AION Macro, EMERGENCY STOP!, 3, 2
        Sleep, 2000
        ScriptEnabled := true
    }
Return

; ============================================================================
; TRAY MENU
; ============================================================================

Menu, Tray, NoStandard
Menu, Tray, Add, Toggle On/Off (F11), ToggleMacro
Menu, Tray, Add, Reload Script (F12), ReloadScript
Menu, Tray, Add
Menu, Tray, Add, Exit, ExitScript
Menu, Tray, Default, Toggle On/Off (F11)
Menu, Tray, Click, 1

ToggleMacro:
    Send, {F11}
Return

ReloadScript:
    Reload
Return

ExitScript:
    ExitApp
Return
