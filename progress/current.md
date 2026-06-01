# Sesión actual

- **Feature completado:** 13 — presence_boost
- **Estado:** done
- **Costo:** \.00, 10K/10K tokens, 10min
- **Modelo:** big-pickle

## Resumen

- Parámetro clarity (0.0-1.0, default 0.0=off)
- Flag --clarity en CLI
- SOS bandpass 3-5kHz al canal ipsolateral escalado por clarity * 0.3
- 15 tests nuevos, 95 total, 0 failing
- Pipeline: head shadow → presence boost → sum → front/back → elevation → anti-clip

## Próximo paso

Feature 14 — high_shelf_boost (--brillo)
