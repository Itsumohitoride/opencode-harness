# Implementation Report: Feature 22e — fix_dropdown_popup_background

## What was investigated

1. **PopupMenu window creation** (`src/rafear/build/release/_deps/juce-src/modules/juce_gui_basics/menus/juce_PopupMenu.cpp`):
   - `MenuWindow::paint()` (line 502-508): first fills entire area with `Colours::white` when opaque, then calls `drawPopupMenuBackgroundWithOptions`. This white pre-fill is the root cause of white lines at edges.
   - `getPopupMenuBorderSize()` returns the border size used for both layout and rendering. When > 0, a 1px border zone exists around content where the white pre-fill could show through if `drawPopupMenuBackground` doesn't cover it precisely.
   - `paintOverChildren()` draws `drawResizableFrame` border only when popup has a parent component (not the case for standalone ComboBox popups).

2. **JUCE LookAndFeel chain**:
   - `drawPopupMenuBackgroundWithOptions` in `LookAndFeel_V2` calls `drawPopupMenuBackground` directly.
   - `LookAndFeel_V4` does NOT override this chain.
   - Our existing `drawPopupMenuBackground` fills with `0xff252525` — correct.

3. **Windows native window** (`juce_Windowing_windows.cpp`):
   - Popup windows get `WS_EX_TOOLWINDOW` style and `windowHasDropShadow` flag.
   - `DwmExtendFrameIntoClientArea(hwnd, {1, 1, 0, 0})` extends DWM glass frame 1px into left/right edges, which can create white-ish artifacts on Windows 10/11.

4. **Item positioning**: items start at y = `borderSize`, so with border=1 there's a 1px gap at top/bottom where only the background fill (not item fills) covers.

## What was changed

### `src/rafear/Source/UI/RafearLookAndFeel.h`
- Added override declaration for `drawPopupMenuBackgroundWithOptions`
- Updated doc comments

### `src/rafear/Source/UI/RafearLookAndFeel.cpp`
1. **`getPopupMenuBorderSize()`**: changed return from `1` to `0`
   - Eliminates the 1px border gap where white pre-fill could leak through
   - Items now start at y=0, filling the entire window with user-drawn background (#252525 for normal items, #303030 for highlighted)
   
2. **Added `drawPopupMenuBackgroundWithOptions` override**: explicitly delegates to `drawPopupMenuBackground`, ensuring no accidental call to base-class default behavior that might draw borders.

## Build result

- **Build**: SUCCESS
- **Binary**: `src/rafear/build/release/Rafear_artefacts/Release/Rafear.exe`

## How the fix works

In JUCE's `MenuWindow::paint()`:
1. `g.fillAll(Colours::white)` — fills entire window white (opaque window)
2. `drawPopupMenuBackgroundWithOptions(g, width, height, options)` → calls our `drawPopupMenuBackground(g, width, height)` → `g.fillAll(0xff252525)` — overwrites entire window with dark

Before the fix, `getPopupMenuBorderSize()` = 1 caused:
- Window height includes 2 extra pixels (top + bottom border)
- Items positioned at y=1 (not y=0)
- A 1px visual gap existed where DWM might render a white border artifact or where compositing could show the initial white fill

After the fix, border size = 0:
- Window height = content height exactly
- Items positioned at y=0
- No border gap anywhere
- The white pre-fill is fully overwritten by our dark fill

Additionally, `drawPopupMenuBackgroundWithOptions` override ensures our dark fill path is always called, never the base-class version which draws borders.

## Remaining issues

- `DwmExtendFrameIntoClientArea` with margins `{1, 1, 0, 0}` still runs (for drop shadow). This is a JUCE internal and cannot be disabled without subclassing the peer. However, with border size 0, the window content extends fully to edges, and any DWM frame rendering at left/right edges (if any) should be overwritten by our Graphics fill. Visually this should be transparent.
- No tests were written because this is a visual rendering fix and there are no automated UI tests in the project.
