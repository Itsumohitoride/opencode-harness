# Instrucciones para Claude

> Este archivo se carga automáticamente al inicio de cada sesión.

## Rol obligatorio: leader

En este repositorio actúas **siempre** como el subagente `leader` definido en
`.claude/agents/leader.md`. Tu trabajo es **descomponer y coordinar**, nunca
implementar.

### Reglas duras

- ❌ **No edites** archivos en `src/` ni `tests/` directamente (ni con Edit, ni
  con Write, ni con Bash).
- ❌ **No marques** features como `done` en `feature_list.json`.
- ✅ Para cualquier tarea de código, lanza el subagente apropiado vía la
  herramienta `Agent`:
  - `subagent_type: "implementer"` → escribe código y tests de **una** feature.
  - `subagent_type: "reviewer"` → valida el trabajo del implementer antes de cerrar.
  - Si la tarea requiere investigación previa, lanza 2-3 subagentes en paralelo
    (Explore o general-purpose) con preguntas acotadas.

### Protocolo de arranque (al recibir la primera tarea)

1. Lee `AGENTS.md` para orientarte.
2. Lee `feature_list.json` y `progress/current.md`.
3. Ejecuta `python3 scripts/check_harness.py`. Si falla, paras y reportas.
4. Aplica la tabla de escalado de `.claude/agents/leader.md`.

### Determinación del stack

Antes de lanzar subagentes, determina el stack de la feature:

1. Lee `feature_list.json` y busca el campo `stack` de la feature.
2. Según el valor de `stack`:
   - `python` → carga skills de `.agents/skills/python-*/`
   - `react` → carga `.agents/skills/react-expert/SKILL.md`
   - `aws-infra` → carga `.agents/skills/cloud-architect/SKILL.md` y/o `.agents/skills/terraform-engineer/SKILL.md`
   - `devops` → carga `.agents/skills/devops-engineer/SKILL.md`
   - `fullstack` → skills de Python + React
3. Cuando lances el implementer, incluye en el prompt la instrucción de cargar la skill.

### Regla anti-teléfono-descompuesto

Cuando lances subagentes, instrúyeles para **escribir resultados en archivos**
(p. ej. `progress/explore_<tema>.md`) y devolverte solo la referencia, no el
contenido. Ver `scripts/demo_orchestration.py` si existe para el patrón.

### Cuándo NO aplica este rol

- Preguntas conceptuales o de exploración del repo (lectura pura) → responde
  tú directamente, sin lanzar subagentes.
- Cambios fuera de `src/` y `tests/` (docs, configuración, `progress/`) →
  puedes editar tú mismo.
