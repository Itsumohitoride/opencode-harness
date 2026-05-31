# CHECKPOINTS — Evaluación del estado final

> En sistemas multi-agente no se evalúa el camino, se evalúa el destino.
> Estos son los checkpoints objetivos que un juez (humano o IA) puede usar
> para decidir si el proyecto está sano.

## C1 — El arnés está completo

- [ ] Existen los 4 archivos base: `AGENTS.md`, `scripts/check_harness.py`, `feature_list.json`,
      `progress/current.md`.
- [ ] Existen los 3 docs: `docs/architecture.md`, `docs/conventions.md`,
      `docs/verification.md`.
- [ ] `python3 scripts/check_harness.py` termina con exit code 0.

## C2 — El estado es coherente

- [ ] Como mucho una feature en `in_progress` en `feature_list.json`.
- [ ] Toda feature `done` tiene tests asociados que pasan.
- [ ] Toda feature con estado `testing` tiene al menos una transición
      `from: "in_progress", to: "testing"`.
- [ ] El último `to` del array `transitions` coincide con el `status` actual.
- [ ] `progress/current.md` está vacío o describe la sesión activa
      (no contiene basura de sesiones anteriores).

## C3 — El código respeta la arquitectura

- [ ] El código en `src/` (o directorio principal) respeta la organización
      definida en `docs/architecture.md`.
- [ ] No hay dependencias externas no declaradas.
- [ ] No hay `print()`/`console.log()` sueltos para debug, ni TODOs sin contexto.

## C4 — La verificación es real

- [ ] `tests/` tiene al menos un test por módulo de código fuente.
- [ ] Los tests usan recursos temporales reales, no mocks de I/O (a menos que
      `docs/architecture.md` especifique lo contrario).
- [ ] El comando de tests definido en `scripts/check_harness.py` muestra > 0 tests y todos verdes.

## C5 — La sesión se cerró bien

- [ ] No hay archivos sin trackear sospechosos (`*.tmp`, `__pycache__`,
      `node_modules/` no ignorados, etc.).
- [ ] `progress/history.md` tiene una entrada por la última sesión.
- [ ] La última feature trabajada está reflejada en su estado correcto.

## C6 — Costo de sesión registrado

- [ ] `progress/cost_log.json` existe y tiene estructura válida.
- [ ] La última feature completada tiene una entrada de costo en
      `progress/cost_log.json`.
- [ ] Los campos de la entrada son completos y veraces (modelo, tokens,
      costo USD, duración, agentes participantes).

## C7 — Documentación de despliegue y configuración

- [ ] `docs/deployment.md` existe y no es la plantilla vacía (tiene
      contenido relevante al proyecto).
- [ ] `docs/configuration.md` existe y no es la plantilla vacía (tiene
      contenido relevante al proyecto).
- [ ] Si la última feature afectó despliegue o configuración,
      los documentos correspondientes se actualizaron.

---

**Cómo usar este archivo:** un agente revisor (`.claude/agents/reviewer.md` o
`.opencode/agents/reviewer.md`) recorre cada checkbox, marca `[x]` o `[ ]`,
y rechaza el cierre de sesión si quedan boxes vacíos en C1-C7.
