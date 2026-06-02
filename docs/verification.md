# Verificación — MonoSpatial

## Cómo verificar que una feature funciona

### 1. Tests unitarios
```bash
pytest tests/ -v
```

### 2. Verificación de entorno
```bash
python scripts/verify_env.py
```

### 3. Check harness completo
```bash
python scripts/check_harness.py
```

### 4. Test offline (WAV)
```bash
python src/test_offline.py
```
Esto toma un archivo WAV estéreo, aplica procesamiento espacial monoaural
y escribe un archivo `output_mono_spatial.wav`. Verificar:
- El archivo de salida existe y es mono
- Al escucharlo con UN solo auricular, se perciben fuentes a la izquierda
  y derecha de forma diferenciable
- La duración coincide con la entrada

### 5. Test de latencia
```bash
python -c "from optimized_convolver import OverlapSaveConvolver; ...
```
Verificar que block_size=512 produce latencia < 11ms.

### 6. Test de calibración
```bash
python src/calibration_ui.py
```
Verificar:
- La ventana PyQt6 se abre sin errores
- Los sliders responden
- El sonido de prueba se reproduce
- La discriminación front/back funciona

## Criterios de Aceptación Generales

- Código pasa `ruff check` sin errores
- Type hints en todas las funciones públicas
- Tests unitarios para el módulo implementado
- Sin print() de debug en código de producción
- Documentación actualizada si la feature cambia APIs públicas