# Sesión actual

- **Feature completado:** 16 — soft_compressor
- **Estado:** done
- **Costo:** \.00, 10K/10K tokens, 10min
- **Modelo:** big-pickle

## Resumen

- Parámetro compress (0.0-1.0, default 0.0=off)
- Flag --compress en CLI
- Soft-knee compressor: threshold -12dB, ratio 3:1, knee 6dB, attack 1ms, release 50ms
- Aplica post-low-cut, pre-anti-clip
- 15 tests nuevos, 138 total, 0 failing
- Pipeline: head shadow → presencia → brillo → sum → front/back → elevation → low-cut → compressor → anti-clip

## Próximo paso

Feature 17 — wasapi_loopback
