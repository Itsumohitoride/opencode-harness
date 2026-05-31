# Verificación — Cómo demostrar que el trabajo funciona

> Regla de oro: **el agente no dice "funciona", lo demuestra**.
> Toda feature termina con evidencia ejecutable, no con afirmaciones.

## Niveles de verificación

### Nivel 1 — Tests unitarios (obligatorio)

Toda función pública en `src/` tiene al menos un test en `tests/` que:

1. Cubre el camino feliz.
2. Cubre al menos un camino de error si la función puede fallar.

Comando (Python):
```bash
python3 -m unittest discover -s tests -v
```

### Nivel 2 — Verificación del stack específico

Cada stack tiene su propia verificación:

| Stack | Comando de verificación |
|-------|------------------------|
| Python | `python3 -m unittest discover -s tests -v` |
| React | `npm test` o `npx vitest run` |
| Terraform | `terraform fmt -check && terraform validate` |
| CI/CD | `act` (GitHub Actions local) o simulación del pipeline |

### Nivel 3 — Verificación integrada

Siempre antes de cerrar:
```bash
python3 scripts/check_harness.py  # debe terminar con exit code 0
```

## Anti-patrones (no hacer)

- ❌ "He añadido el código, debería funcionar." → falta test ejecutable.
- ❌ Test que solo verifica que la función no lanza excepción. → tiene que
  comprobar el resultado concreto.
- ❌ `mock` del filesystem. → usa recursos temporales reales.
- ❌ Marcar la feature como `done` sin pasar `python3 scripts/check_harness.py`.

## Verificación final antes de cerrar

```bash
python3 scripts/check_harness.py  # debe terminar con [OK] Entorno listo
```

Si `check_harness.py` está rojo, **no** marques nada como `done`. Anota el bloqueo
en `progress/current.md` con estado `blocked` en `feature_list.json`.
