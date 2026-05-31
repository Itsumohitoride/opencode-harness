# Harness Engineering Template

Template de proyecto estructurado para **Harness Engineering**: un repositorio
diseñado para que agentes de IA (Claude Code, opencode) trabajen sobre él de
forma autónoma y verificable.

> Lo importante de este repo no es **qué** hace la aplicación, sino **cómo**
> está estructurado para que un agente pueda implementar features, una a la vez,
> con verificación automática.

## Para empezar

```bash
python3 scripts/check_harness.py
```

Si todo está verde, abre `AGENTS.md` y sigue desde ahí.

## Personalización

Este template es multi-stack. Antes de empezar a implementar:

1. Edita `docs/architecture.md` con la arquitectura de **tu** proyecto.
2. Edita `docs/conventions.md` con las convenciones de **tu** stack.
3. Edita `scripts/verify_env.py` — activa las verificaciones de tu stack. Personaliza `scripts/run_tests.py` con el comando de tests de tu proyecto.
4. Edita `feature_list.json` — cambia `project` y `description`, y añade
   tus propias features.

## Estructura del arnés

```
.
├── AGENTS.md              # Mapa para agentes (divulgación progresiva)
├── CHECKPOINTS.md         # Criterios de "estado final correcto"
├── feature_list.json      # Alcance: una feature a la vez
├── scripts/
│   ├── check_harness.py   # Orquestador maestro
│   ├── verify_env.py      # Verificación de entorno
│   ├── verify_files.py    # Verificación de archivos base
│   ├── verify_features.py # Validación de feature_list.json
│   └── run_tests.py       # Ejecutor de tests
├── progress/
│   ├── current.md         # Sesión activa (estado vivo)
│   └── history.md         # Bitácora append-only
├── docs/
│   ├── architecture.md    # Qué significa "buen trabajo" (personalizable)
│   ├── conventions.md     # Estilo, nombres, errores (personalizable)
│   └── verification.md    # Cómo demostrar que funciona
├── .claude/
│   ├── agents/            # Definiciones de líder, implementador, revisor
│   └── settings.json      # Hooks que automatizan la verificación
├── .opencode/
│   ├── agents/            # Definiciones de líder, implementador, revisor
│   └── ...                # Config opencode
├── src/                   # Código de tu aplicación
└── tests/                 # Tests automáticos
```

## Principios del arnés

| Pilar | Manifestación |
|-------|---------------|
| **El repositorio ES el sistema** | `AGENTS.md`, `scripts/check_harness.py`, `feature_list.json`, `progress/`, `docs/` |
| **Orquestación multi-agente** | `.claude/agents/` y `.opencode/agents/` |
| **Verificación ejecutable** | `scripts/check_harness.py` corre tests reales |

## Ecosistemas soportados

- **Claude Code**: usa `CLAUDE.md` + `.claude/agents/`
- **opencode**: usa `opencode.json` + `.opencode/agents/`
