# Explore 19a: JUCE Project Structure Research for C++ Audio App on Windows

**Date**: 2026-06-04
**Context**: Researching JUCE project setup for a Windows audio app that does WASAPI loopback capture + processing + playback + system tray.

---

## 1. CMake vs Projucer: Recommended Approach in 2026

| Approach | Status | Recommendation |
|----------|--------|---------------|
| **CMake (native)** | Primary, fully supported since JUCE 7.x | **USE THIS** |
| **Projucer** | Legacy, still works but deprecated path | Avoid for new projects |
| **Both** | Projucer can export CMake, but not needed | Skip |

**Rationale**: JUCE 8.x ships with a mature native CMake API (`juce_add_gui_app`, `juce_add_plugin`, `juce_add_console_app`). The official JUCE repo provides example CMake projects in `examples/CMake/`. The community has standardized on CMake. Pamplejuce (2026 template) uses CMake exclusively.

**Key resources**:
- JUCE CMake API docs: `docs/CMake API.md` in JUCE repo
- Pamplejuce template: github.com/sudara/pamplejuce
- JUCE examples: `examples/CMake/` directory

---

## 2. CMakeLists.txt Structure for Audio Capture + Processing + Playback App

```cmake
cmake_minimum_required(VERSION 3.25)

project(MyAudioApp
    VERSION 1.0.0
    DESCRIPTION "Windows audio capture + processing + playback"
    LANGUAGES CXX
)

# --- C++ Standard ---
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- JUCE Integration ---
# Option A: JUCE as git submodule (recommended)
add_subdirectory(JUCE)

# Option B: Installed JUCE
# find_package(JUCE CONFIG REQUIRED)

# --- JUCE target: GUI application ---
juce_add_gui_app(${PROJECT_NAME}
    PRODUCT_NAME "My Audio App"
    COMPANY_NAME "MyCompany"
    BUNDLE_ID "com.mycompany.myaudioapp"
    VERSION ${PROJECT_VERSION}

    # Windows: WASAPI capture needs permissions
    MICROPHONE_PERMISSION_ENABLED TRUE
    MICROPHONE_PERMISSION_TEXT "Capture system audio via WASAPI."

    ICON_BIG "${CMAKE_SOURCE_DIR}/Resources/AppIcon.png"
)

# --- Link JUCE modules ---
target_link_libraries(${PROJECT_NAME} PRIVATE
    # Core
    juce::core

    # Audio pipeline
    juce::audio_basics
    juce::audio_devices
    juce::audio_utils
    juce::audio_formats

    # DSP
    juce::dsp

    # GUI
    juce::gui_basics
    juce::gui_extra

    # Events
    juce::events

    # Recommended JUCE flags
    juce::juce_recommended_config_flags
    juce::juce_recommended_warning_flags
    juce::juce_recommended_lto_flags
)

# --- Source files ---
file(GLOB_RECURSE SOURCES
    CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/Source/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/Source/*.h"
)
target_sources(${PROJECT_NAME} PRIVATE ${SOURCES})

# --- Preprocessor definitions ---
target_compile_definitions(${PROJECT_NAME} PRIVATE
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0
)

# --- Windows-specific ---
if(WIN32)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        ole32.lib
        oleaut32.lib
        uuid.lib
        avrt.lib
    )
endif()
```

---

## 3. JUCE Modules Required (Feature Map)

| Feature | JUCE Module | Key Classes |
|---------|-------------|-------------|
| WASAPI device enum + I/O | `juce_audio_devices` | `AudioDeviceManager`, `WASAPIDeviceMode` |
| WASAPI loopback capture | `juce_audio_devices` (native) | Select output device as input in shared mode |
| Audio playback output | `juce_audio_devices` | `AudioSourcePlayer`, `AudioDeviceManager` |
| Audio buffers | `juce_audio_basics` | `AudioBuffer<float>`, `AudioSource` |
| Audio file read/write | `juce_audio_formats` | `WavAudioFormat`, `AudioFormatReader/Writer` |
| FFT | `juce_dsp` | `dsp::FFT` (2^order points) |
| Convolution (partitioned FFT) | `juce_dsp` | `dsp::Convolution`, `dsp::Convolution::NonUniform` |
| FIR/IIR filters | `juce_dsp` | `dsp::FIRFilter`, `dsp::IIR::Filter` |
| Processing spec/context | `juce_dsp` | `dsp::ProcessSpec`, `dsp::ProcessContextReplacing` |
| System tray icon | `juce_gui_extra` | `SystemTrayIconComponent` |
| Window management | `juce_gui_basics` | `DocumentWindow`, `Component` |
| Event loop / timer | `juce_events` | `MessageManager`, `Timer` |
| Core types | `juce_core` | `String`, `File`, `Thread`, `MemoryBlock` |
| Utility classes | `juce_audio_utils` | `AudioAppComponent`, `AudioThumbnail` |

### WASAPI Loopback: Important Caveat

JUCE's built-in WASAPI does NOT have explicit loopback mode support. Workaround:

```cpp
// Create shared-mode WASAPI device type
auto wasapiType = juce::AudioIODeviceType::createAudioIODeviceType_WASAPI(
    juce::WASAPIConfig::WASAPIDeviceMode::shared
);
wasapiType->scanForDevices();
auto outputNames = wasapiType->getDeviceNames(false); // output devices
// Open output device as input for loopback
auto device = wasapiType->createDevice({}, outputNames[0]);
```

**Better alternative**: Use raw Win32 WASAPI directly (`IAudioClient` + `AUDCLNT_STREAMFLAGS_LOOPBACK`) and pipe into JUCE audio pipeline. This is the most reliable approach for loopback.

**Community forks**: mattgonzalez/JUCE (direct2d branch) adds loopback, not merged upstream.

---

## 4. Minimum Required Versions

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| **CMake** | **3.22** | **3.25+** | 3.22 is JUCE minimum. 3.25 for modern features (CPM, presets). |
| **JUCE** | **7.0.0** | **8.0.9+** | 8.x current. Latest stable: 8.0.9 (Sep 2025). |
| **C++ Standard** | C++17 | C++20/23 | JUCE minimum C++17. C++20 recommended. |
| **Visual Studio** | VS 2019 | VS 2022 | VS 2026 generator: `"Visual Studio 18 2026"` |
| **Windows SDK** | 10.0.17763 | 10.0.19041+ | Windows 10 1607 minimum target. |
| **Windows Target** | Win 10 1607 | Win 10/11 | JUCE deployment minimum. |

---

## 5. Build System Setup for Windows/MSVC

### VS 2022 Generator
```powershell
cmake -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release
```

### VS 2026 Generator
```powershell
cmake -B build -G "Visual Studio 18 2026" -A x64
```

### CMakePresets.json (recommended)
```json
{
    "version": 6,
    "configurePresets": [
        {
            "name": "windows-release",
            "generator": "Visual Studio 17 2022",
            "architecture": { "value": "x64", "strategy": "set" },
            "binaryDir": "${sourceDir}/build/release",
            "cacheVariables": { "CMAKE_BUILD_TYPE": "Release" }
        }
    ],
    "buildPresets": [
        { "name": "release", "configurePreset": "windows-release" }
    ]
}
```

### MSVC flags for audio apps
```cmake
if(MSVC)
    target_compile_options(${PROJECT_NAME} PRIVATE
        /arch:AVX2        # AVX2 for DSP
        /MP                # Multiprocess build
        /fp:fast           # Fast math (safe for audio)
    )
    set_target_properties(${PROJECT_NAME} PROPERTIES
        WIN32_EXECUTABLE TRUE
        INTERPROCEDURAL_OPTIMIZATION_RELEASE TRUE
    )
endif()
```

---

## 6. Typical Directory Structure

```
MyAudioApp/
├── CMakeLists.txt
├── CMakePresets.json
├── .gitignore
├── .gitmodules
│
├── JUCE/                          # Git submodule
│   ├── modules/
│   └── CMakeLists.txt
│
├── Source/
│   ├── Main.cpp                   # START_JUCE_APPLICATION
│   ├── App/
│   │   ├── Application.h/cpp      # JUCEApplication
│   │   └── MainWindow.h/cpp       # DocumentWindow
│   ├── Audio/
│   │   ├── AudioCapture.h/cpp     # WASAPI loopback wrapper
│   │   ├── AudioPlayback.h/cpp    # Audio output device
│   │   └── AudioGraph.h/cpp       # Optional processor graph
│   ├── DSP/
│   │   ├── FFTProcessor.h/cpp     # STFT analysis/resynthesis
│   │   ├── ConvolutionProcessor.h/cpp  # dsp::Convolution
│   │   └── ProcessingChain.h/cpp  # Pipeline coordinator
│   ├── UI/
│   │   ├── MainComponent.h/cpp    # AudioAppComponent
│   │   └── TrayComponent.h/cpp    # SystemTrayIconComponent
│   └── Utils/
│       └── DeviceManager.h/cpp    # AudioDeviceManager helper
│
├── Resources/
│   ├── AppIcon.png
│   ├── TrayIcon.png
│   └── ImpulseResponses/
│
└── tests/
    └── CMakeLists.txt
```

---

## Summary of Key Decisions

1. **Build system**: CMake-only, no Projucer. Minimum CMake 3.25, target JUCE 8.x.
2. **Required modules**: `juce_core`, `juce_audio_basics`, `juce_audio_devices`, `juce_audio_utils`, `juce_audio_formats`, `juce_dsp`, `juce_gui_basics`, `juce_gui_extra`, `juce_events`.
3. **WASAPI loopback**: Use shared-mode WASAPI via `AudioDeviceManager` selecting output device as input, or raw Win32 WASAPI with `AUDCLNT_STREAMFLAGS_LOOPBACK`. JUCE has no native loopback -- requires workaround.
4. **FFT/Convolution**: `juce_dsp` provides `dsp::FFT` and `dsp::Convolution` (partitioned, latency-controlled).
5. **System tray**: `SystemTrayIconComponent` in `juce_gui_extra`.
6. **Windows toolchain**: VS 2022 generator, x64, AVX2, `/fp:fast`.
7. **Template base**: Pamplejuce or `examples/CMake/GUIApp` from JUCE repo.
