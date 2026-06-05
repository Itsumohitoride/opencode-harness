# Explore 19c — JUCE system tray & installer research

**Date:** 2026-06-04
**Context:** Feature 19 — C++/JUCE migration for Rafear (MonoSpatial).
**Question:** Patterns for system tray background apps + Windows installer creation in JUCE.

---

## 1. JUCE system tray / notification area support

**Yes — juce::SystemTrayIconComponent** (in juce_gui_extra module).

- Header: modules/juce_gui_extra/misc/juce_SystemTrayIconComponent.h
- Native impl: modules/juce_gui_extra/native/juce_SystemTrayIcon_windows.cpp
- Doc: https://docs.juce.com/master/classjuce_1_1SystemTrayIconComponent.html

### Key API surface

| Method | Purpose |
|--------|---------|
| setIconImage(const Image& colourImage, const Image& templateImage) | Sets tray icon bitmap |
| setIconTooltip(const String& tooltip) | Tooltip on hover |
| setHighlighted(bool) | Highlight state (Windows supports this) |
| showInfoBubble(const String& title, const String& content) | Toast notification balloon |
| hideInfoBubble() | Dismiss balloon |
| showDropdownMenu(const PopupMenu& menu) | macOS native menu; on Windows shows PopupMenu near icon |
| getNativeHandle() | Raw OS handle for low-level access |

### Mouse event overrides (inherited from Component)

Override mouseDown(), mouseUp(), mouseDoubleClick(), mouseMove().
Canonical pattern: left-click shows window, right-click shows popup menu.
x/y positions will NOT be valid for tray clicks — use only for click-type detection.

### Caveats

- Behaviour differs across OSes. "Not fully implemented for all OSes."
- On Windows: creates a NOTIFYICONDATA via Shell_NotifyIcon (NIM_ADD).
- On macOS: uses NSStatusItem. Known issue with showDropdownMenu hanging on Mac in some JUCE versions (forum thread). Workaround: use PopupMenu::showMenuAsync() instead.
- On Linux: depends on desktop environment (app-indicator protocol vs. XEmbed). May not work on Wayland without extra setup.

### Module dependency

Must link against juce_gui_extra. Add JUCE_MODULE_AVAILABLE_juce_gui_extra or include via CMake:
juce_add_module("juce_gui_extra")

---

## 2. JUCE app running in background (no window, only tray icon)

### Pattern: Do NOT create a main window in initialise()

Standard JUCE GUI app template creates a MainWindow in JUCEApplication::initialise(). For tray-only, skip creating any DocumentWindow:

`cpp
class RafearApplication : public JUCEApplication {
public:
    void initialise(const String&) override {
        // 1. Create tray icon — no DocumentWindow created
        trayIcon = std::make_unique<SystemTrayIconComponent>();
        trayIcon->setIconImage(ImageCache::getFromMemory(BinaryData::tray_icon_png,
                                BinaryData::tray_icon_pngSize), {});
        trayIcon->setIconTooltip("Rafear - MonoSpatial Audio");
        trayIcon->addMouseListener(this, false);

        // 2. Create config window but keep hidden
        configWindow = std::make_unique<ConfigWindow>();
        // configWindow->setVisible(false);

        // 3. Init audio device manager (background processing)
        deviceManager.initialise(0, 2, nullptr, true);
    }

    void shutdown() override {
        trayIcon = nullptr;
        configWindow = nullptr;
        deviceManager.closeAudioDevice();
    }

    // On left-click: show/hide config window
    void mouseDown(const MouseEvent& e) override {
        if (e.mods.isRightButtonDown()) {
            showTrayMenu();
        } else {
            toggleWindowVisibility();
        }
    }

private:
    std::unique_ptr<SystemTrayIconComponent> trayIcon;
    std::unique_ptr<ConfigWindow> configWindow;
    AudioDeviceManager deviceManager;
};
`

### Key points

- No DocumentWindow is created in initialise() — app starts with no visible window.
- Tray icon is created immediately so user can interact.
- Config window created but hidden; toggled via tray icon click.
- On macOS: call Process::setDockIconVisible(false) in initialise() to hide dock icon.
- On Windows: no taskbar button if no window is shown. Window with WS_EX_TOOLWINDOW also avoids taskbar.

### Reference

JUCE Forum: https://forum.juce.com/t/macos-app-as-background-process-with-system-tray-icon-and-native-menu/39905
Solution: get rid of the auto-created main document window.

---

## 3. Auto-start with Windows in a JUCE app

Two approaches, both work with JUCE:

### Approach A: Windows Registry Run key (recommended)

JUCE provides juce::WindowsRegistry class (in juce_core).

`cpp
#include <juce_core/misc/juce_WindowsRegistry.h>

void setAutoStart(bool enabled) {
    String path = "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run";
    String keyName = "Rafear";

    if (enabled) {
        File exeFile = File::getSpecialLocation(File::currentExecutableFile);
        WindowsRegistry::setValue(path + "\\" + keyName, exeFile.getFullPathName());
    } else {
        WindowsRegistry::deleteValue(path + "\\" + keyName);
    }
}
`

- **HKCU** = current user only, no admin required. Preferred for user-level tray apps.
- **HKLM** = all users, requires admin. Use in installer.
- Key: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
- Value: REG_SZ with full path to executable.

### Approach B: Startup folder shortcut

`cpp
void setAutoStartShortcut(bool enabled) {
    File startupFolder = File::getSpecialLocation(File::userApplicationDirectory)
                            .getChildFile("Microsoft\\Windows\\Start Menu\\Programs\\Startup");
    File shortcut = startupFolder.getChildFile("Rafear.lnk");
    if (enabled) {
        File exeFile = File::getSpecialLocation(File::currentExecutableFile);
        shortcut.createShortcut(exeFile.getFullPathName());
    } else {
        shortcut.deleteFile();
    }
}
`

### Approach C: Task Scheduler

For "run on boot before user logon". Overkill for a user tray app. Requires admin.
JUCE has no built-in Task Scheduler API — shell out to schtasks.exe.

### Recommendation

**Use Registry Run key (HKCU)**. No admin, simple with WindowsRegistry, standard for tray apps (Discord, Spotify, etc.).

### Caveats (from JUCE forum)

- Autostart issues on Windows 11 with JUCE apps reported (exit code 3221225477). Caused by dependencies not being available at early boot. Mitigation: use schtasks with a small delay or bundle all DLLs.
- If using MSI installer, set HKLM Run key as part of the MSI (more robust).

---

## 4. MSI installer options for a JUCE app

### Option A: CPack + WiX (recommended for JUCE CMake projects)

JUCE has first-class CMake support. CPack with the WIX generator is the natural fit.

**Workflow:**
1. Add install() targets in CMakeLists.txt
2. Configure CPack for WIX generator
3. Build MSI with cpack -G WIX

**Required CMakeLists.txt additions:**
`cmake
install(TARGETS Rafear RUNTIME DESTINATION bin COMPONENT Applications)

set(CPACK_PACKAGE_NAME "Rafear")
set(CPACK_PACKAGE_VERSION "1.0.0")
set(CPACK_PACKAGE_VENDOR "MonoSpatial")
set(CPACK_GENERATOR "WIX")
set(CPACK_WIX_UPGRADE_GUID "YOUR-GUID-HERE")
set(CPACK_WIX_LICENSE_RTF "/LICENSE.rtf")
set(CPACK_WIX_PRODUCT_ICON "/icon.ico")
set(CPACK_CREATE_DESKTOP_LINKS "Rafear")
set(CPACK_PACKAGE_EXECUTABLES "Rafear" "Rafear")
`

**Build command:**
`ash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
cpack -G WIX -B build/packages --config build/CPackConfig.cmake
`

**Pros:** Free, open-source, integrated with CMake, proper MSI with Windows Installer service, supports upgrades/patches, GitHub Actions Windows runners have WiX pre-installed.

**Cons:** WiX XML is verbose, learning curve for custom UI dialogs.

**WiX v3 vs v4:** CPack supports both via CPACK_WIX_VERSION variable. v3 is default and stable.

### Option B: InstallForge (free, GUI-based)

- https://installforge.net/
- Freeware GUI-based setup builder
- Can generate MSI or executable installers
- Simpler than WiX but less flexible
- No CPack integration (manual step in CI)

### Option C: Inno Setup

- Script-based, generates .exe (not MSI)
- Very popular, can be called from CMake post-build
- No CPack integration

### Option D: Advanced Installer (commercial)

- Professional MSI authoring
- Free tier has limitations
- GUI-based

### Option E: Manual WiX authoring

Write .wxs files by hand. More control, more work.

### Recommendation for this project

**CPack + WiX (v3)** — best integration with existing JUCE CMake build system. If WiX proves too complex, fall back to **InstallForge**.

---

## 5. Audio device auto-detection in JUCE

### Core class: juce::AudioDeviceManager

- Module: juce_audio_devices
- Doc: https://docs.juce.com/master/classjuce_1_1AudioDeviceManager.html

### Initialisation

`cpp
AudioDeviceManager deviceManager;
String error = deviceManager.initialise(0, 2, nullptr, true);
if (error.isNotEmpty()) { /* handle error */ }
`

Parameters: maxInputChannels, maxOutputChannels, savedState (XML), selectDefaultDeviceOnFailure, preferredDefaultDeviceName, preferredSetupOptions.

### Enumerate available devices

`cpp
auto* deviceTypes = deviceManager.getAvailableDeviceTypes();
for (auto* type : deviceTypes) {
    StringArray deviceNames = type->getDeviceNames();
    for (auto& name : deviceNames) {
        if (name.containsIgnoreCase("CABLE Output")) { /* found it */ }
    }
}
`

### Device change detection

AudioDeviceManager is a ChangeBroadcaster. Register a ChangeListener:

`cpp
class RafearApp : public JUCEApplication, public ChangeListener {
    void initialise(const String&) override {
        deviceManager.addChangeListener(this);
        deviceManager.initialise(0, 2, nullptr, true);
    }
    void changeListenerCallback(ChangeBroadcaster* source) override {
        if (source == &deviceManager) {
            auto* device = deviceManager.getCurrentAudioDevice();
            // Re-adapt processing pipeline
        }
    }
    AudioDeviceManager deviceManager;
};
`

### Device hot-plug detection

JUCE does NOT have a built-in callback for device arrival/removal.
The ChangeBroadcaster fires when device settings change, not when new hardware appears.

**Approaches:**

1. **Periodic polling** — use a Timer to call getAvailableDeviceTypes() and compare.

`cpp
class DeviceWatcher : public Timer, public ChangeBroadcaster {
    void timerCallback() override {
        bool changed = rescanIfNeeded();  // compare device lists
        if (changed) sendChangeMessage();
    }
};
`

2. **Windows-specific: IMMNotificationClient** — register for Win32 audio endpoint notifications via COM. Can be wrapped through getNativeHandle().

3. **JUCE's internal scanDevicesIfNeeded()** — call periodically. Has internal listNeedsScanning flag.

### Audio callback setup

`cpp
class RafearAudioCallback : public AudioIODeviceCallback {
    void audioDeviceAboutToStart(AudioIODevice* device) override {
        sampleRate = device->getCurrentSampleRate();
        bufferSize = device->getCurrentBufferSizeSamples();
    }
    void audioDeviceStopped() override {}
    void audioDeviceIOCallback(const float** inputChannelData,
                               int numInputChannels,
                               float** outputChannelData,
                               int numOutputChannels,
                               int numSamples) override {
        // Process WASAPI loopback -> HRTF -> output
    }
};
`

### WASAPI loopback in JUCE

JUCE's WASAPI audio device supports loopback mode internally. The standard AudioDeviceManager abstraction with "Windows Audio" device type uses WASAPI. For explicit loopback control, use WASAPIAudioDevice directly or bridge the feature-17 C++ WASAPI loopback implementation that uses IAudioClient / IAudioCaptureClient via CoInitializeEx.

---

## 6. Recommended JUCE app lifecycle for a tray app

### Lifecycle

`
START_JUCE_APPLICATION
    |
    v
JUCEApplication::initialise()
    |-- Process::setDockIconVisible(false)         [macOS]
    |-- Create SystemTrayIconComponent, set icon
    |-- Create config window (hidden)
    |-- Init AudioDeviceManager + callback
    |-- Load saved settings
    |-- Check auto-start
    v
Application running (event loop)
    |
    |-- [Tray left-click]  -->  toggle config window
    |-- [Tray right-click] -->  popup menu:
    |       "Start/Stop Processing"
    |       "Settings..."
    |       "Run at startup" (checkbox)
    |       separator
    |       "Quit"
    |-- [Audio device change] --> reinit pipeline
    |-- [Timer tick] --> periodic device scan
    |-- [Window close] --> hide (not quit)
    |-- [Quit] --> JUCEApplication::quit()
    v
JUCEApplication::shutdown()
    |-- Save settings
    |-- Stop audio device
    |-- Remove tray icon
    v
Process exits
`

### Window visibility toggling

`cpp
void toggleWindowVisibility() {
    if (configWindow != nullptr) {
        if (configWindow->isVisible()) {
            configWindow->setVisible(false);
        } else {
            configWindow->setVisible(true);
            configWindow->toFront(true);
        }
    }
}
`

### Right-click popup menu

`cpp
void showTrayMenu() {
    PopupMenu menu;
    menu.addItem(1, isProcessing ? "Stop Processing" : "Start Processing");
    menu.addSeparator();
    menu.addItem(2, "Settings...");
    menu.addItem(3, "Run at startup", true, isAutoStartEnabled);
    menu.addSeparator();
    menu.addItem(4, "Quit");

    menu.showMenuAsync(PopupMenu::Options(),
        [this](int result) {
            switch (result) {
                case 1: toggleProcessing(); break;
                case 2: showSettingsWindow(); break;
                case 3: toggleAutoStart(); break;
                case 4: JUCEApplication::quit(); break;
            }
        });
}
`

### Avoiding taskbar icon on Windows

Use WS_EX_TOOLWINDOW extended style on the config window:

`cpp
configWindow->addToDesktop(ComponentPeer::windowAppearsOnTaskbar, 0);
`

### Quit behavior

Call JUCEApplication::quit() (or JUCEApplicationBase::quit()) to exit cleanly. The systemRequestedQuit() default calls quit(). Override for confirm-dialog if needed.

---

## Summary — Implementation plan for feature 19

| Aspect | Recommended approach |
|--------|---------------------|
| System tray | juce::SystemTrayIconComponent with icon + right-click PopupMenu |
| Hidden start | No DocumentWindow in initialise(). Tray icon only. Config window hidden |
| Auto-start | WindowsRegistry::setValue() on HKCU\...\Run key |
| Installer | CPack + WiX v3, integrated with CMake build |
| Device detection | AudioDeviceManager::initialise() + ChangeListener + periodic Timer scan for hotplug |
| App lifecycle | start hidden -> tray icon -> left-click toggles window -> right-click menu -> quit |
| WASAPI loopback | JUCE WASAPI device type or native IAudioClient for explicit loopback |
| Settings storage | JUCE PropertiesFile or WindowsRegistry for persistence |

---

## Key references

1. SystemTrayIconComponent API — https://docs.juce.com/master/classjuce_1_1SystemTrayIconComponent.html
2. AudioDeviceManager API — https://docs.juce.com/master/classjuce_1_1AudioDeviceManager.html
3. WindowsRegistry API — https://docs.juce.com/master/classjuce_1_1WindowsRegistry.html
4. JUCEApplication API — https://docs.juce.com/master/classjuce_1_1JUCEApplication.html
5. JUCE CMake API — https://github.com/juce-framework/JUCE/blob/master/docs/CMake%20API.md
6. CPack WIX Generator — https://cmake.org/cmake/help/latest/cpack_gen/wix.html
7. JUCE Forum: Mac background process — https://forum.juce.com/t/macos-app-as-background-process-with-system-tray-icon-and-native-menu/39905
8. JUCE Forum: Windows autostart — https://forum.juce.com/t/windows-autostart-of-juce-app/55116
9. JUCE Tutorial: AudioDeviceManager — https://juce.com/tutorials/tutorial_audio_device_manager/
10. CPack packaging tutorial — https://www.studyplan.dev/cmake/creating-installers
11. InstallForge — https://installforge.net/
12. WiX Toolset — https://github.com/wixtoolset/
