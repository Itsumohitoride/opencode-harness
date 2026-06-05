# Feature 19-b: JUCE Audio Capabilities Research

> Research date: 2026-06-04
> Context: Migrating MonoSpatial from Python MVP to C++/JUCE (feature 19)
> Questions answered for implementing real-time spatial audio pipeline on Windows

---

## Q1. How does JUCE handle WASAPI loopback? (AudioDeviceManager, flags)

### Current JUCE (mainline) — NO loopback support

JUCE wraps WASAPI via juce_WASAPI_windows.cpp but **does not expose AUDCLNT_STREAMFLAGS_LOOPBACK**. The WASAPIDeviceMode enum has only three values:

| Mode | Description |
|------|-------------|
| WASAPIDeviceMode::shared | Standard shared mode, SRC enabled |
| WASAPIDeviceMode::sharedLowLatency | IAudioClient3 shared mode (Win10+) |
| WASAPIDeviceMode::exclusive | Exclusive mode, bypasses mixer |

No WASAPIDeviceMode::loopback exists upstream.

### Known fork with loopback support

mattgonzalez published a JUCE fork (direct2d branch) that adds WASAPI loopback recording:

- GitHub: https://github.com/mattgonzalez/JUCE/tree/direct2d
- Forum post: https://forum.juce.com/t/wasapi-loopback/56361 (May 2023)

Usage pattern from fork:
`cpp
auto wasapiDeviceType = juce::AudioIODeviceType::createAudioIODeviceType_WASAPI(juce::WASAPIDeviceMode::shared);
wasapiDeviceType->scanForDevices();
auto outputDeviceNames = wasapiDeviceType->getDeviceNames(false /* wantInputNames */);
juce::String inputName = outputDeviceNames[0];
auto device = wasapiDeviceType->createDevice({}, inputName);
// Opens output device as loopback capture input
`

**Key constraint**: Loopback only works in **shared mode**. The fork enumerates output devices as available input devices when loopback is enabled.

### Recommendation

Two viable paths:
1. **Fork patching**: Apply mattgonzalez's loopback patch to local JUCE build (modify juce_WASAPI_windows.cpp to set AUDCLNT_STREAMFLAGS_LOOPBACK during IAudioClient::Initialize)
2. **Raw Win32 alongside JUCE**: Implement separate WASAPI loopback capture thread using native Win32 COM APIs (IMMDeviceEnumerator -> IAudioClient with AUDCLNT_STREAMFLAGS_LOOPBACK), feed captured buffers into JUCE's processing via lock-free queue. This avoids forking JUCE.

---

## Q2. Can JUCE capture system audio mix via WASAPI loopback natively?

**No, not out of the box.**

JUCE's WASAPI implementation (juce_WASAPI_windows.cpp ~2110 lines) handles:
- Normal capture (from mic/line-in)
- Normal playback (to speakers/headphones)
- Shared, sharedLowLatency, and exclusive modes

It does NOT handle:
- Loopback capture (system audio mix) — AUDCLNT_STREAMFLAGS_LOOPBACK flag is never set
- Process-specific loopback (AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK)

Microsoft's WASAPI loopback requirements (from Win32 docs):
`
// Instead of:
enumerator->GetDefaultAudioEndpoint(eCapture, ..., &device);
// Use:
enumerator->GetDefaultAudioEndpoint(eRender, ..., &device);
// Then in Initialize:
client->Initialize(AUDCLNT_SHAREMODE_SHARED, AUDCLNT_STREAMFLAGS_LOOPBACK, ...);
`

JUCE's WASAPIDeviceBase::getStreamFlags() only sets:
- AUDCLNT_STREAMFLAGS_EVENTCALLBACK (0x40000) — always
- AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM + AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY — only in shared mode

No AUDCLNT_STREAMFLAGS_LOOPBACK anywhere.

### If using the fork approach

The fork maps output device names into the input device list. AudioDeviceManager's initialise() would accept an "input device" that is actually the loopback target. Setup:
`cpp
deviceManager.initialise(2, 0, nullptr, true, {}, nullptr);
// Then set input device to the output device name manually
`

---

## Q3. JUCE audio callback pattern for real-time processing

### Two main patterns

#### Pattern A: AudioAppComponent (simpler, for standalone apps)
`cpp
class MainComponent : public juce::AudioAppComponent {
    void prepareToPlay(double sampleRate, int samplesPerBlock) override {
        // Pre-allocate buffers, FFT plans, IR data
        // NEVER allocate in audio callback
    }

    void getNextAudioBlock(const juce::AudioSourceChannelInfo& buffer) override {
        // buffer.buffer -> AudioBuffer<float>&
        // buffer.startSample, buffer.numSamples
        // Process in-place
    }

    void releaseResources() override {
        // Cleanup
    }
};
`

#### Pattern B: AudioIODeviceCallback (lower-level, for AudioDeviceManager)
`cpp
class AudioCallback : public juce::AudioIODeviceCallback {
    void audioDeviceAboutToStart(AudioIODevice* device) override {
        // Pre-allocate: sampleRate = device->getCurrentSampleRate()
        // blockSize = device->getCurrentBufferSizeSamples()
    }

    void audioDeviceIOCallback(const float** inputChannelData,
                               int numInputChannels,
                               float** outputChannelData,
                               int numOutputChannels,
                               int numSamples) override {
        // REAL-TIME HOT PATH
        // inputChannelData[ch] -> const float* per channel
        // outputChannelData[ch] -> float* per channel to fill
        // numSamples = block size
    }

    void audioDeviceStopped() override {}
};
`

### Real-time thread constraints (NON-NEGOTIABLE)

At 48kHz / 256-block: ~5.3ms deadline per callback.

| Forbidden | Allowed |
|-----------|---------|
| 
ew/delete/malloc/ree | Pre-allocated buffers |
| Mutex locks (priority inversion) | std::atomic with relaxed ordering |
| File I/O, network | Lock-free SPSC queues |
| Exceptions (stack unwind) | Pure math, DSP |
| std::vector::push_back | Fixed-size std::array or AudioBuffer |
| System calls (printf, sleep) | SIMD intrinsics |

### Data flow for MonoSpatial

`
audioDeviceIOCallback() {
  1. Read input channels (stereo from loopback)
  2. Split L/R (getWritePointer 0, 1)
  3. Apply HRTF convolution per channel using dsp::Convolution
  4. Mix to mono output channel
  5. Write to output buffer
}
`

Pre-allocate all dsp::Convolution objects in udioDeviceAboutToStart().

---

## Q4. FFT convolution in JUCE for HRTF (dsp::Convolution)

### juce::dsp::Convolution

Class: juce::dsp::Convolution

Algorithm: **Uniformly-partitioned overlap-add** with zero-latency design. Even with single-sample input, it partitions and convolves immediately (no block-size wait).

#### Loading HRTF impulse responses

`cpp
juce::dsp::Convolution convolution;

// From buffer (e.g., loaded from .sofa via libmysofa)
void prepare(const juce::dsp::ProcessSpec& spec) {
    convolution.loadImpulseResponse(
        impulseResponseBuffer,  // AudioBuffer<float>&
        irSampleRate,           // e.g., 48000.0
        juce::dsp::Convolution::Stereo::yes,
        juce::dsp::Convolution::Trim::no,
        juce::dsp::Convolution::Normalise::yes,
        0  // 0 = use full IR length
    );
    convolution.prepare(spec);
}

// In audio callback:
void processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer&) {
    auto context = juce::dsp::ProcessContextReplacing<float>(buffer);
    convolution.process(context);
}
`

#### For MonoSpatial pipeline

Need **two convolution instances** (left ear HRTF / right ear HRTF):
`cpp
class MonoHRTFProcessor {
    juce::dsp::Convolution leftIR, rightIR;
    juce::AudioBuffer<float> leftBuffer, rightBuffer;  // split channels

    void prepare(juce::dsp::ProcessSpec spec) {
        leftIR.prepare(spec);   // mono spec
        rightIR.prepare(spec);
    }

    void processBlock(juce::AudioBuffer<float>& buffer) {
        // Split stereo into two mono buffers
        // Convolve leftBuffer with leftIR
        // Convolve rightBuffer with rightIR
        // Sum to mono output
    }
};
`

#### Alternatives

- juce::dsp::FFT — lower-level if custom partitioning needed
- juce::dsp::FIR::Filter — direct-form FIR for short IRs (<128 taps)
- External: RTConvolve (Hurchalla time-distributed FFT) for very long IRs

For typical HRTF IRs (~128-512 taps at 48kHz), dsp::Convolution is more than adequate.

#### Latency from convolution

dsp::Convolution claims **zero additional latency** beyond the block size. IR is partitioned into blocks matching the audio buffer size, each partition processed independently.

---

## Q5. Latency profile: JUCE WASAPI vs PortAudio

### Measured/Reported latencies

| Configuration | Typical Round-trip | Notes |
|---------------|-------------------|-------|
| **JUCE WASAPI shared** | 10-40ms | Default ~10ms at 48kHz; user reports of 40ms with 256 buffer |
| **JUCE WASAPI sharedLowLatency** | ~6-10ms | Uses IAudioClient3 (Win10+), 2.67ms minimum at 48kHz |
| **JUCE WASAPI exclusive** | 3-6ms | Bypasses mixer, blocks other audio |
| **JUCE DirectSound** | 30-100ms | Legacy, higher overhead |
| **PortAudio WASAPI event** | 3-10ms | Exclusive mode can hit ~3ms |
| **PortAudio WASAPI polling** | 10-13ms | Higher CPU than event |
| **PortAudio WDM/KS** | 3-6ms | Kernel streaming |

### Key differences

| Aspect | JUCE WASAPI | PortAudio WASAPI |
|--------|-------------|-------------------|
| Shared mode min latency | ~10ms (IAudioClient1) | ~10ms (IAudioClient1) |
| IAudioClient3 support | Yes (sharedLowLatency) | No (as of 2025) |
| Exclusive mode | Yes | Yes (paWinWasapiExclusive) |
| Loopback support | No (mainline) | No (no loopback flag) |
| Buffer size control | Via AudioDeviceManager | Via PaWasapi_GetFramesPerHostBuffer |
| Thread priority | Automatic MMCSS | Manual via PaWasapi_ThreadPriorityBoost |
| CPU usage (JUCE 7 benchmarks) | 5-15% (256-block, 32-band EQ) | Similar |

### Verdict for MonoSpatial

JUCE sharedLowLatency mode via IAudioClient3 is the **best option on Win10+** — allows 2.67ms minimum latency in shared mode. This is comparable to exclusive mode without blocking other system audio.

`
JUCE sharedLowLatency ~2.67ms < MonoSpatial target 5.3ms < PortAudio event ~3ms
`

Both are acceptable. JUCE has the edge for IAudioClient3 support and integrated lifecycle management.

---

## Q6. Multichannel audio handling (split L/R channels)

### AudioBuffer channel access

`cpp
juce::AudioBuffer<float> buffer;

// Read channel count
int numChannels = buffer.getNumChannels();

// Read samples per channel
int numSamples = buffer.getNumSamples();

// Per-channel read/write pointers
const float* channel0 = buffer.getReadPointer(0);  // Left (typically)
float* channel1 = buffer.getWritePointer(1);         // Right (typically)

// Copy channel to another buffer
buffer.copyFrom(0, 0, sourceBuffer, 0, 0, numSamples);  // destChan, destStart, src, srcChan, srcStart, numSamples

// Add from another channel
buffer.addFrom(0, 0, sourceBuffer, 1, 0, numSamples);   // mix right into left
`

### Channel splitting for MonoSpatial

Spatial pipeline needs to split stereo input, process each channel independently:

`cpp
void processBlock(juce::AudioBuffer<float>& buffer) {
    int numSamples = buffer.getNumSamples();

    // Input is stereo (2 channels)
    const float* leftIn  = buffer.getReadPointer(0);
    const float* rightIn = buffer.getReadPointer(1);

    // Copy to mono working buffers
    leftWorkBuffer.copyFrom(0, 0, buffer, 0, 0, numSamples);
    rightWorkBuffer.copyFrom(0, 0, buffer, 1, 0, numSamples);

    // Apply spatial filters (mono processors)
    leftProcessor.process(leftWorkBuffer);
    rightProcessor.process(rightWorkBuffer);

    // Mix to mono output on channel 0
    buffer.clear();
    buffer.addFrom(0, 0, leftWorkBuffer, 0, 0, numSamples);
    buffer.addFrom(0, 0, rightWorkBuffer, 0, 0, numSamples);
}
`

### AudioChannelSet layouts

JUCE supports arbitrary channel layouts via AudioChannelSet:
- AudioChannelSet::stereo() — L, R
- AudioChannelSet::mono() — M
- AudioChannelSet::create5point1() — L, R, C, Lfe, Ls, Rs
- AudioChannelSet::create7point1() — L, R, C, Lfe, Ls, Rs, Lcs, Rcs

Useful for future surround-to-mono downmixing.

---

## Q7. Buffer/block-size control in JUCE

### Setting buffer size

`cpp
// Via AudioDeviceManager::initialise()
deviceManager.initialise(
    2,      // numInputChannelsNeeded
    2,      // numOutputChannelsNeeded
    nullptr, // savedState XML
    true     // selectDefaultDeviceOnFailure
);
// Default buffer size is used (typically 512 at 48kHz)

// Via AudioDeviceSetup
juce::AudioDeviceManager::AudioDeviceSetup setup;
setup.bufferSize = 256;  // Request 256 samples
setup.sampleRate = 48000.0;
deviceManager.setAudioDeviceSetup(setup, true);
`

### Querying available buffer sizes

`cpp
auto* device = deviceManager.getCurrentAudioDevice();
if (device) {
    auto availableSizes = device->getAvailableBufferSizes();
    int min = availableSizes[0];
    int max = availableSizes[availableSizes.size() - 1];
    int current = device->getCurrentBufferSizeSamples();
}
`

### Known issues

1. **WASAPI shared mode regression** (commit 83e3cd8be9, reported May 2026): Changing buffer size in shared mode has no effect — currentBufferSizeSamples always set to defaultBufferSize. Fixed in recent develop branch.
2. **WASAPI exclusive mode**: Buffer size must align with device period; may reject arbitrary sizes.
3. **sharedLowLatency mode**: Buffer sizes are constrained to multiples of the fundamental period (e.g., 128-sample multiples).

### Recommended sizes for MonoSpatial

| Mode | Buffer | Latency | Use case |
|------|--------|---------|----------|
| sharedLowLatency | 128 | ~2.67ms | Production (gaming) |
| sharedLowLatency | 256 | ~5.3ms | Target matching MVP |
| shared | 512 | ~10.6ms | Fallback compatible |
| exclusive | 128-256 | ~3-6ms | Lowest latency but blocks other audio |

---

## Q8. Capture from one device (WASAPI loopback) and play to another (headset)

### Current JUCE limitation

AudioDeviceManager is designed for a **single duplex device** (same device for input + output). It cannot natively route WASAPI loopback capture from the speakers output device to playback on a separate headset device.

### Two approaches

#### Approach A: Dual AudioDeviceManager instances (safe, recommended)

`cpp
// Capture manager — WASAPI loopback on default output device
juce::AudioDeviceManager captureManager;
captureManager.initialise(2, 0, nullptr, true);
// (Requires loopback patch or raw Win32 WASAPI loopback)

// Playback manager — play to headset
juce::AudioDeviceManager playbackManager;
playbackManager.initialise(0, 1, nullptr, true);

// Transfer audio between callbacks via lock-free SPSC queue
// capture callback -> push to queue
// playback callback -> pop from queue, process, output
`

A lock-free SPSC queue is essential (e.g., JUCE's AbstractFifo or SingleThreadedAbstractFifo).

#### Approach B: Raw Win32 WASAPI loopback + JUCE playback (practical)

`
[Raw WASAPI loopback thread]
    |-- Creates IAudioClient with AUDCLNT_STREAMFLAGS_LOOPBACK on render device
    |-- Reads audio from IAudioCaptureClient in a loop
    |-- Pushes samples into lock-free ring buffer (e.g., JUCE AbstractFifo)

[JUCE audio callback (playback thread)]
    |-- In audioDeviceIOCallback():
    |-- Pops samples from ring buffer
    |-- Applies HRTF spatial processing
    |-- Writes to output (headset)
`

This approach avoids forking JUCE entirely. Only the capture side uses raw Win32 COM.

#### Approach C: Virtual Audio Cable (workaround)

Use VB-CABLE or equivalent as the capture source:
- Game/System audio -> CABLE Output (virtual device)
- MonoSpatial captures from CABLE Input
- MonoSpatial plays to Headset

This is the same pattern as the current Python MVP. Simpler but requires external driver.

### Recommendation for feature 19

**Approach B** (raw Win32 WASAPI loopback + JUCE playback) is the best tradeoff:
- No external driver dependency
- No JUCE fork needed
- Only ~200 lines of raw Win32 WASAPI code for capture
- Leverages JUCE's full audio pipeline for everything else
- Proven pattern (used by OBS, Chrome, Discord)

---

## Summary Table

| Question | Verdict |
|----------|---------|
| Q1. JUCE WASAPI loopback flags | Not in mainline. Fork exists (mattgonzalez). Must patch or use raw Win32. |
| Q2. Native system audio capture | No. JUCE does not set AUDCLNT_STREAMFLAGS_LOOPBACK. |
| Q3. Audio callback pattern | udioDeviceIOCallback() or getNextAudioBlock(). Strict real-time rules. |
| Q4. FFT convolution for HRTF | dsp::Convolution is ideal. Zero-latency partitioned overlap-add. Load IR from buffer. |
| Q5. Latency: JUCE vs PortAudio | JUCE sharedLowLatency (~2.67ms) beats PortAudio (~3ms) on Win10+. Both viable. |
| Q6. Multichannel handling | AudioBuffer::getWritePointer(ch) for per-channel access. Straightforward. |
| Q7. Buffer size control | AudioDeviceSetup::bufferSize. WASAPI shared mode has a regression bug (fix pending). |
| Q8. Cross-device capture/play | Two approaches: dual AudioDeviceManager or raw Win32 loopback + JUCE playback. Both work. |

### Recommended architecture for MonoSpatial C++/JUCE

`
[Win32 WASAPI loopback capture thread]
  |-- IMMDeviceEnumerator -> GetDefaultAudioEndpoint(eRender)
  |-- IAudioClient::Initialize(SHARED, LOOPBACK)
  |-- IAudioCaptureClient::GetBuffer() -> push to ring buffer

[Lock-free ring buffer (AbstractFifo)]
  |
  v
[JUCE AudioDeviceManager -> playback callback]
  |-- Pop from ring buffer
  |-- Split L/R channels
  |-- dsp::Convolution (left HRTF) + dsp::Convolution (right HRTF)
  |-- Sum to mono
  |-- Write to output device (headset)
`

JUCE provides: device enumeration, audio routing, DSP primitives, UI framework, system tray, settings persistence.
Raw Win32 provides: WASAPI loopback capture (the only piece JUCE cannot do natively).
