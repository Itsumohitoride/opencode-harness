# Convenciones de código — Multi-stack

> Homogeneidad extrema dentro de cada stack. Cada ecosistema (Python, React, Terraform)
> tiene sus propias reglas. Respeta las del stack de la feature que implementas.

---

## Stack: Python

### Estilo
| Aspecto | Convención |
|---------|-----------|
| Formateo | `ruff format` |
| Linter | `ruff check` |
| Línea máxima | 100 caracteres |
| Strings | Comillas dobles `"` |
| Interpolación | f-strings siempre |
| Imports | stdlib → terceros → locales (separados por línea en blanco) |
| Type hints | Obligatorios en toda función pública |

### Nombres
| Tipo | Convención | Ejemplo |
|------|-----------|---------|
| Archivos | `snake_case` | `user_service.py` |
| Clases | `PascalCase` | `UserService` |
| Funciones | `snake_case` | `get_user_by_id` |
| Constantes | `UPPER_SNAKE` | `MAX_RETRIES` |
| Privadas | Prefijo `_` | `_internal_helper` |

### Tests
- Ubicación: `tests/test_<módulo>.py`
- Framework: `unittest` o `pytest`
- Recursos: usar `tempfile.TemporaryDirectory` real, no mocks del filesystem
- Nombres: `test_<escenario>_<resultado_esperado>`

### Manejo de errores
- Excepciones nombradas del dominio (ej. `NoteNotFoundError`)
- Usar `Result[T, E]` pattern para operaciones que pueden fallar sin side effects

## Stack: React / TypeScript

### Estilo
| Aspecto | Convención |
|---------|-----------|
| Formateo | Prettier |
| Linter | ESLint + `@typescript-eslint` |
| Línea máxima | 100 caracteres |
| Strings | Comillas simples `'` (JSX: dobles) |
| Imports | absolutos con alias `@/` |
| Tipado | Strict mode, evitar `any` |

### Nombres
| Tipo | Convención | Ejemplo |
|------|-----------|---------|
| Archivos componentes | `PascalCase` | `UserCard.tsx` |
| Archivos utilidad | `kebab-case` | `format-date.ts` |
| Componentes | `PascalCase` | `function UserCard()` |
| Hooks | `camelCase` con prefijo `use` | `useUserData` |
| Props type | `PascalCase` con sufijo `Props` | `UserCardProps` |
| Handlers | `handle<Evento>` | `handleSubmit` |

### Tests
- Framework: `vitest` + `@testing-library/react`
- Ubicación: `__tests__/` junto al componente o `tests/` centralizado
- Mocks de API: MSW (Mock Service Worker)
- Nombres: `describe('UserCard')` / `it('muestra el nombre del usuario')`

### Estado
- Server state: TanStack Query (fetching, caching, mutations)
- Client state: Zustand (UI state, modals, formularios complejos)
- Evitar prop drilling profundo (>3 niveles)

## Stack: Terraform / AWS

### Estilo
| Aspecto | Convención |
|---------|-----------|
| Formateo | `terraform fmt` |
| Linter | `tflint` |
| Versionado | Provider pinning (`~> 5.0`) |
| Nombres | `snake_case` con prefijo de recurso |
| Tags | Obligatorios: `Name`, `Environment`, `CostCenter`, `ManagedBy` |

### Estructura
```
terraform/
  environments/
    dev/
    staging/
    prod/
  modules/
    networking/
    compute/
    database/
  global/
    iam/
    s3-backend/
```

### Seguridad
- IAM: least privilege, usar `aws_iam_policy_document` inline
- Secrets: AWS Secrets Manager, nunca variables de entorno hardcodeadas
- Red: subnets privadas para RDS y ECS, solo ALB públicos
- Cifrado: KMS para RDS, S3, EBS
- Backup: RDS automated backups (retención 30 días)

### Convenciones de variables
- `variable "name" { description = "...", type = string }`
- `variable "environment" { validation { ... } }` para valores permitidos
- Outputs solo para valores necesarios en otros módulos
