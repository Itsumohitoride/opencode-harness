# Sesión actual

- **Feature:** 17 — wasapi_loopback (v2)
- **Estado:** in_progress
- **Branch harness:** develop
- **Branch src:** feature/17-wasapi_loopback
- **Inicio:** 2026-06-01T19:20

## Objetivo (actualizado)

WASAPI loopback nativo vía Windows API con comtypes.
Eliminar CABLE + sounddevice capture. Usar IAudioClient con AUDCLNT_STREAMFLAGS_LOOPBACK.

## Plan v2

1. Crear WasapiLoopbackCapture class (comtypes → Windows WASAPI)
2. Modificar RealtimeProcessor: loopback capture thread + output-only sd.OutputStream
3. Tests con mocking
4. Verificar sin CABLE

## Próximo paso

Implementar WasapiLoopbackCapture + integración.