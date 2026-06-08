# Feature 22e — Tray popup menu LookAndFeel fix

## Change summary

Applied the custom `RafearLookAndFeel` (dark #252525 background) to the system tray icon's right-click context menu.

## Files modified

### `src/rafear/Source/App/Application.h` (RafearTrayIcon)
- Added `juce::LookAndFeel* customLookAndFeel{nullptr};` private member
- Added `void setCustomLookAndFeel(juce::LookAndFeel* lf)` setter
- In `mouseDown()`: if `customLookAndFeel != nullptr`, call `menu.setLookAndFeel(customLookAndFeel)` before `showMenuAsync()`

### `src/rafear/Source/UI/MainComponent.h`
- Replaced forward declaration `class RafearLookAndFeel;` with `#include "RafearLookAndFeel.h"` (needed for upcast to `juce::LookAndFeel*`)
- Added public getter: `juce::LookAndFeel* getLookAndFeelPtr() const { return lookAndFeel.get(); }`

### `src/rafear/Source/App/Application.cpp`
- After `trayIcon` construction, added: `pimpl->trayIcon->setCustomLookAndFeel(pimpl->mainWindow->getLookAndFeelPtr());`

## Verification
- Build: **succeeded** (Release, VS 2022)
- Harness check: **all green**
- The existing `RafearLookAndFeel::drawPopupMenuItem()` already draws dark (#252525) background with #e0e0e0 text
- The existing `RafearLookAndFeel::drawPopupMenuBackground()` fills with #252525
- The existing `RafearLookAndFeel::getPopupMenuBorderSize()` returns 0 (no white border)
