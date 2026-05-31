# AGENTS.md — Mapa de navegación para agentes de IA

> Este archivo es el **punto de entrada** para cualquier agente que trabaje en este
> repositorio. NO es una biblia de reglas: es un **mapa**. Lee solo lo que
> necesites cuando lo necesites (divulgación progresiva).

---

## 1. Antes de empezar (obligatorio)

1. Ejecuta python3 scripts/check_harness.py y verifica que termina sin errores. Si falla, **para**
   y resuelve el entorno antes de tocar código.
2. Lee progress/current.md para entender en qué estado quedó la última sesión.
3. Lee eature_list.json y elige **una** tarea con estado pending. No
   trabajes en más de una a la vez.

## 2. Mapa del repositorio

| Archivo / carpeta            | Qué contiene                                              | Cuándo leerlo |
|------------------------------|-----------------------------------------------------------|---------------|
| eature_list.json          | Lista de tareas con estado (pending / in_progress / testing / done / blocked) | Siempre, al empezar |
| progress/current.md        | Estado de la sesión actual                                | Siempre, al empezar |
| progress/history.md        | Bitácora append-only de sesiones anteriores               | Si necesitas contexto histórico |
| docs/architecture.md       | Qué significa "hacer un buen trabajo" en este proyecto    | Antes de implementar |
| docs/conventions.md        | Reglas de estilo, nombres, estructura                     | Antes de escribir código |
| docs/verification.md       | Cómo verificar que tu trabajo funciona                    | Antes de declarar una tarea como done |
| scripts/check_harness.py   | Orquestador de verificaciones (punto de entrada)          | Cada vez que quieras validar el estado |
| scripts/sync_push.py       | Push solo src/ contents al remote (vía git subtree)       | Para subir cambios al remoto |
| scripts/sync_pull.py       | Pull solo src/ contents desde el remote                   | Para traer cambios del remoto |
| .claude/agents/            | Definiciones de subagentes (líder, implementador, revisor) | Si orquestas trabajo con Claude Code |
| .opencode/agents/          | Definiciones de subagentes (líder, implementador, revisor) | Si orquestas trabajo con opencode |
| src/                       | Código de la aplicación                                   | Para implementar |
| 	ests/                     | Tests automáticos                                         | Para verificar |

## 3. Reglas duras (no negociables)

- **Una sola feature a la vez.** No mezcles cambios de varias tareas en la misma sesión.
- **Las tareas pasan por testing antes de done.** El implementer deja en 	esting, el líder pregunta al humano si las pruebas pasaron, y solo entonces se marca done.
- **Cada feature en su rama.** Antes de empezar una feature, crea una rama eature/<id>-<name> desde develop.
- **El remoto solo contiene src/.** El harness (.agents/, scripts/, docs/, progress/, etc.) **no se sube al remoto**. Solo el contenido de src/ via git subtree push --prefix=src.
- **Los MRs van contra develop.** Nunca edites main directamente. Tras aprobación humana, crea un Merge Request contra develop.
- **Documenta lo que haces** en progress/current.md mientras trabajas, no al final.
- **Deja el repositorio limpio** antes de cerrar la sesión (ver §5).
- **Si no sabes algo, busca en docs/** antes de inventarlo.

## 4. Cómo elegir y arrancar una tarea

`
1. git checkout develop
2. git pull origin develop  (via: python3 scripts/sync_pull.py develop)  # si hay cambios remotos
3. Lee feature_list.json, filtra por status == "pending", coge la de menor "id"
4. Crea rama: git checkout -b feature/<id>-<name>
5. Cambia su status a "in_progress" en feature_list.json y guarda
6. Anota en progress/current.md: feature, rama, hora de inicio, plan breve
`

## 5. Cierre de sesión (lifecycle)

Antes de terminar:

1. Ejecuta python3 scripts/check_harness.py — todo verde.
2. Si la tarea está acabada: marca status: "done" en eature_list.json y registra la transición.
3. El **líder** pregunta al usuario el costo de la sesión y ejecuta
   python3 scripts/log_cost.py con los datos.
4. El **implementer** carga el skill git-commit desde
   .agents/skills/git-commit/SKILL.md y ejecuta el commit en la rama feature.
5. El **líder** sube la rama feature al remoto (solo src/ contents):
   `ash
   python3 scripts/sync_push.py feature/<id>-<name>
   `
6. El **líder** crea el Merge Request contra develop:
   `ash
   gh pr create --base develop --head feature/<id>-<name> --title "Feature <id>: <name>" --body "<descripción breve>"
   `
7. Mueve el resumen de progress/current.md al final de progress/history.md.
8. Vacía progress/current.md dejando solo la plantilla.
9. No dejes archivos temporales, ni print() de debug, ni TODOs sin contexto.

## 6. Si te bloqueas

- Relee la sección relevante de docs/.
- Si la herramienta no hace lo que esperas, **no inventes un workaround**:
  documenta el bloqueo en progress/current.md y para la sesión.
