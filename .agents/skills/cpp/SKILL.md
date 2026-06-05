# Skill: C++/JUCE Audio Development

## C++ Best Practices for JUCE Audio Apps

### Memory model
- Audio callbacks are REAL-TIME. No allocation, no locks, no I/O.
- All DSP objects must be pre-allocated in `prepareToPlay()`.
- Use `std::array` or fixed-size pools, never `std::vector` in callbacks.

### JUCE module reference

| Module | Header pattern | Key classes |
|--------|---------------|-------------|
| juce_core | `#include <juce_core/juce_core.h>` | String, File, Thread, MemoryBlock |
| juce_events | `#include <juce_events/juce_events.h>` | Timer, MessageManager |
| juce_gui_basics | `#include <juce_gui_basics/juce_gui_basics.h>` | Component, Graphics, Colour |
| juce_gui_extra | `#include <juce_gui_extra/juce_gui_extra.h>` | SystemTrayIconComponent |
| juce_audio_basics | `#include <juce_audio_basics/juce_audio_basics.h>` | AudioBuffer, AudioSourceChannelInfo |
| juce_audio_devices | `#include <juce_audio_devices/juce_audio_devices.h>` | AudioDeviceManager, AudioIODeviceCallback |
| juce_audio_utils | `#include <juce_audio_utils/juce_audio_utils.h>` | AudioAppComponent |
| juce_dsp | `#include <juce_dsp/juce_dsp.h>` | Convolution, FFT, IIR::Filter, ProcessSpec |

### WASAPI loopback (raw Win32)
JUCE does NOT support WASAPI loopback natively. Use this pattern:

```cpp
// 1. Initialize COM
CoInitializeEx(nullptr, COINIT_MULTITHREADED);

// 2. Get default render device
IMMDeviceEnumerator* enumerator = nullptr;
CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr,
    CLSCTX_ALL, __uuidof(IMMDeviceEnumerator), (void**)&enumerator);
IMMDevice* device = nullptr;
enumerator->GetDefaultAudioEndpoint(eRender, eConsole, &device);

// 3. Activate IAudioClient with LOOPBACK flag
IAudioClient* audioClient = nullptr;
device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr, (void**)&audioClient);
WAVEFORMATEX* mixFormat = nullptr;
audioClient->GetMixFormat(&mixFormat);
audioClient->Initialize(AUDCLNT_SHAREMODE_SHARED,
    AUDCLNT_STREAMFLAGS_LOOPBACK | AUDCLNT_STREAMFLAGS_EVENTCALLBACK,
    hnsBufferDuration, 0, mixFormat, nullptr);

// 4. Get capture client and read
IAudioCaptureClient* captureClient = nullptr;
audioClient->GetService(__uuidof(IAudioCaptureClient), (void**)&captureClient);
audioClient->Start();

// 5. Push to JUCE AbstractFifo
juce::AbstractFifo fifo(capacity);
// In read loop:
BYTE* data; DWORD flags; UINT32 frames;
captureClient->GetBuffer(&data, &frames, &flags, nullptr, nullptr);
// Write to fifo, then ReleaseBuffer
```

### Audio pipeline pattern
```cpp
class SpatialAudioProcessor {
public:
    void prepare(const juce::dsp::ProcessSpec& spec) {
        leftConvolution.prepare(spec);
        rightConvolution.prepare(spec);
        // Pre-allocate all IIR filters
        headShadow.prepare(spec);
        elevationUp.prepare(spec);
        // etc.
    }

    void process(juce::AudioBuffer<float>& buffer) {
        // Split stereo to mono per channel
        // Apply HRTF convolution per channel
        // Apply spatial filters per channel
        // Sum to mono
        // Apply compressor
    }

private:
    juce::dsp::Convolution leftConvolution;
    juce::dsp::Convolution rightConvolution;
    juce::dsp::ProcessorDuplicator<juce::dsp::IIR::Filter<float>,
                                    juce::dsp::IIR::Coefficients<float>> headShadow;
};
```

### Common pitfalls
1. `JUCEApplication` must be a singleton (one per process)
2. Always check `deviceManager.initialise()` return value
3. WASAPI shared mode: buffer size changes may not take effect (JUCE bug)
4. System tray icon: create in initialise(), NOT in constructor
5. Audio callbacks: never call juce::AlertWindow or any GUI from audio thread
6. Use `MessageManager::callAsync()` to dispatch UI updates from audio thread
7. `dsp::Convolution::loadImpulseResponse()` is NOT real-time safe - call in prepare()
