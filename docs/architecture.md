# Arquitectura — Multi-stack: Python / React / AWS

> Este documento define el estándar de calidad para proyectos que usan este template.
> Dependiendo del stack de cada feature, aplican reglas específicas.

## Principios generales

1. **Separación por capas.** Cada stack tiene sus propias capas con responsabilidades bien definidas:
   - **Python (backend):** API layer → service layer → persistence layer.
   - **React (frontend):** components → hooks → state management → API client.
   - **AWS (infraestructura):** networking → compute → storage → security.

2. **Infraestructura como código.** Toda la infraestructura AWS se define con Terraform. No se permiten cambios manuales en la consola de AWS sin reflejarlos en el código.

3. **Tipado estricto.** Python usa tipado completo (`mypy --strict`). React usa TypeScript strict mode. Terraform valida tipos con `validation` blocks.

4. **Inmutabilidad por defecto.** Los objetos de dominio son inmutables. En React, estado inmutable con hooks. En Terraform, infraestructura inmutable con reemplazo en vez de modificación in-place.

5. **Pruebas en cada capa.** Cada stack tiene su propio nivel de verificación:
   - Python: `pytest` + `unittest` (tests unitarios + integración).
   - React: `vitest` + `@testing-library/react` (componentes + hooks).
   - Terraform: `terraform plan` + `terraform validate` + `tflint`.

## Flujo de datos (Fullstack)

```
Usuario → React (Next.js) → API REST (FastAPI) → Servicio → Base de datos (RDS/Aurora)
                                                      ↓
                                                AWS S3 (archivos)
                                                      ↓
                                                EventBridge → Lambda (procesamiento async)
```

## Stack: Python (FastAPI)

- **Framework:** FastAPI con Pydantic v2 para validación.
- **Base de datos:** SQLAlchemy 2.0 async + Alembic para migraciones.
- **Autenticación:** JWT con OAuth2.
- **Tests:** pytest con httpx AsyncClient.
- **Linter/formateador:** ruff (reglas desde `pyproject.toml`).
- **Tipado:** mypy strict mode.

### Estructura de directorios
```
src/
  api/          ← Routers de FastAPI
  core/         ← Config, dependencias, middlewares
  domain/       ← Entidades, value objects, excepciones
  services/     ← Lógica de negocio
  infrastructure/  ← Repositorios, clientes externos, DB
tests/
  unit/
  integration/
```

## Stack: React (Frontend)

- **Framework:** Next.js 14+ con App Router.
- **Estado:** React Context + TanStack Query (server state) + Zustand (client state).
- **Estilo:** Tailwind CSS + shadcn/ui.
- **Tests:** vitest + @testing-library/react + MSW (mocks de API).
- **Linter/formateador:** ESLint + Prettier.
- **Tipado:** TypeScript strict mode.

### Estructura de directorios
```
src/
  app/          ← App Router pages y layouts
  components/   ← Componentes reutilizables
  hooks/        ← Custom hooks
  lib/          ← Utilidades, API client
  state/        ← Estado global (Zustand stores)
  types/        ← TypeScript types/interfaces
```

## Stack: AWS (Infraestructura)

- **IaC:** Terraform (provider AWS ~> 5.0) con remote state en S3 + DynamoDB.
- **Red:** VPC con subnets públicas/privadas, NAT Gateway, VPC Flow Logs.
- **Compute:** ECS Fargate (backend) + S3 + CloudFront (frontend estático).
- **Base de datos:** RDS Aurora (PostgreSQL) en subnets privadas.
- **Seguridad:** IAM roles con least privilege, KMS para cifrado, WAF + Shield.
- **CI/CD:** GitHub Actions con stages: plan → apply → smoke test.

## Qué NO hacer (general)

- No mezclar stacks en un mismo módulo/componente.
- No hardcodear configuración de entorno (usar variables de entorno o secrets manager).
- No exponer recursos internos (RDS, ECS) a Internet directamente.
- No usar print()/console.log() para debug.
- No ignorar errores de linter o type checker en CI.
- No mezclar responsabilidades de frontend y backend en el mismo paquete/directorio.
