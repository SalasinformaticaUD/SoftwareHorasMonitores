# Plan de implementacion backend - Plataforma e integracion

Fecha base: 19/08/2026

Este plan corresponde al frente de Plataforma e integracion definido para 1 persona. Su responsabilidad es dejar el backend profesionalmente preparado para que los demas frentes implementen sin romper contratos: configuracion NestJS, Prisma compartido, autenticacion, usuarios, roles, permisos, dependencias, auditoria, convenciones de API e integracion futura con Gestion de Monitores.

Este frente debe avanzar primero porque desbloquea al Core operativo y a los Modulos paralelos.

---

## 0. Reglas del frente

- [X] No cambiar rutas funcionales existentes sin documentarlo y coordinarlo.
- [X] No conectar directamente a la base de datos de Gestion de Monitores.
- [X] No almacenar datos propios de Monitores dentro de esta base, salvo identificadores externos necesarios para integracion por API.
- [X] Proteger credenciales, tokens y secretos desde el inicio.
- [X] Cada cambio transversal debe incluir una prueba smoke o e2e minima.
- [X] Todo contrato comun debe quedar documentado en `backend/docs` o `backend/src/MODULES.md`.
- [X] Cerrar cada fase con `npm test -- --runInBand` y `npx tsc --noEmit --incremental false`.

---

## 1. Semana 1 - Infraestructura base de NestJS

Objetivo: convertir la app Nest en una API consistente y lista para crecimiento.

### 1.1 Configuracion de entorno

- [X] Instalar y configurar `@nestjs/config`.
- [X] Crear `.env.example` en `backend`.
- [X] Definir variables minimas:
  - [X] `DATABASE_URL`
  - [X] `PORT`
  - [X] `JWT_SECRET`
  - [X] `JWT_EXPIRES_IN`
  - [X] `FRONTEND_URL`
  - [X] `NODE_ENV`
  - [X] `MONITORES_API_URL` si aplica para integracion futura
- [X] Validar variables con un helper propio o libreria aprobada por el equipo.
- [X] Garantizar que `.env` no se versiona.

### 1.2 Bootstrap de API

- [X] Configurar `app.setGlobalPrefix('api')` o decidir explicitamente mantener rutas sin prefijo.
- [X] Habilitar CORS restringido a `FRONTEND_URL`.
- [X] Registrar `ValidationPipe` global:
  - [X] `whitelist: true`
  - [X] `transform: true`
  - [X] `forbidNonWhitelisted: true` si no rompe integracion inicial
- [X] Crear filtro global de excepciones con respuesta uniforme.
- [X] Definir formato de exito recomendado: objeto directo o `{ data }`, pero uno solo para todo el backend.
- [X] Crear endpoint `GET /health` o `GET /api/health`.

### 1.3 Pruebas

- [X] Ajustar e2e actual para health y 404 raiz segun la decision de prefijo.
- [X] Verificar arranque con `npm run start:dev`.
- [X] Verificar tipos con `npx tsc --noEmit --incremental false`.

Criterio de cierre: cualquier modulo nuevo hereda validacion, CORS, errores y configuracion.

---

## 2. Semana 1 - PrismaModule y PrismaService

Objetivo: centralizar el acceso a base de datos y evitar que cada modulo invente su conexion.

### 2.1 Crear modulo compartido

- [X] Crear `backend/src/prisma/prisma.module.ts`.
- [X] Crear `backend/src/prisma/prisma.service.ts`.
- [X] Extender `PrismaClient` desde el cliente generado por Prisma.
- [X] Implementar `onModuleInit` para conectar.
- [X] Implementar `enableShutdownHooks` o manejo equivalente para cierre ordenado.
- [X] Exportar `PrismaService` desde `PrismaModule`.
- [X] Importar `PrismaModule` en `AppModule` o marcarlo como global.

### 2.2 Ajustar Prisma 7

- [X] Confirmar que `prisma/schema.prisma` genera cliente en `generated/prisma`.
- [X] Confirmar ruta real de import para el `PrismaClient`.
- [X] Si se prefiere convencion mas comun, evaluar cambiar generator a `prisma-client-js` y documentarlo antes de tocar migraciones.
- [X] Verificar que `prisma.config.ts` toma `DATABASE_URL`.

### 2.3 Scripts y flujo de base de datos

- [X] Agregar scripts al `package.json` si faltan:
  - [X] `prisma:generate`
  - [X] `prisma:migrate`
  - [X] `prisma:deploy`
  - [X] `prisma:studio`
- [X] Documentar comandos para desarrollo local.
- [X] Crear seed inicial cuando auth y permisos esten listos.

### 2.4 Pruebas

- [X] Test unitario simple de `PrismaService` con mock si no hay DB.
- [X] Smoke test que arranque `AppModule` con `PrismaModule`.
- [X] Validar que los servicios funcionales puedan inyectarlo sin ciclos.

Criterio de cierre: Core y Paralelos pueden reemplazar stubs por consultas reales.

---

## 3. Semana 1 - Contratos comunes de API

Objetivo: evitar incompatibilidades entre equipos.

### 3.1 Convenciones

- [X] Definir si la API usa prefijo `/api`.
- [X] Definir plural/singular de rutas. Recomendacion: conservar rutas actuales y no renombrar durante MVP salvo errores claros.
- [X] Definir paginacion comun:
  - [X] `page`
  - [X] `limit`
  - [X] `total`
  - [X] `items`
- [X] Definir filtros por query string.
- [X] Definir formato de fechas en ISO 8601.
- [X] Definir uso de UUID como string.

### 3.2 Errores

- [X] 400 para validacion.
- [X] 401 para no autenticado.
- [X] 403 para sin permiso.
- [X] 404 para recurso inexistente.
- [X] 409 para conflicto de negocio, por ejemplo horario cruzado.
- [X] 500 para error inesperado sin filtrar secretos.

### 3.3 Documentacion

- [X] Crear tabla de endpoints por modulo.
- [X] Incluir permisos requeridos por endpoint.
- [X] Incluir ejemplo de request/response para los endpoints consumidos por frontend.
- [X] Mantener `backend/src/MODULES.md` como mapa tecnico y `backend/docs` como plan/contratos.

Criterio de cierre: frontend puede conectar sin depender de leer servicios internos.

---

## 4. Semana 1 y 2 - Usuarios, dependencias, roles y permisos

Objetivo: implementar los modulos transversales antes de proteger operaciones.

### 4.1 Dependencias

- [X] Completar DTOs de `dependencias`.
- [X] Implementar CRUD real con Prisma.
- [X] Evitar borrar dependencias con usuarios asociados.
- [X] Seed inicial:
  - [X] Aulas de Software
  - [X] Electrica y Electronica
  - [X] Fisica

### 4.2 Modulos y permisos

- [X] Crear seed de `Modulo` con los modulos del documento:
  - [X] dashboard
  - [X] horarios
  - [X] aulas
  - [X] disponibilidad
  - [X] practicas-libres
  - [X] prestamos-docentes
  - [X] audiovisuales
  - [X] software
  - [X] observaciones
  - [X] limpieza
  - [X] tareas
  - [X] multas
  - [X] credenciales
  - [X] reportes
  - [X] administracion
- [X] Crear permisos por accion minima: leer, crear, actualizar, eliminar, aprobar, exportar.
- [X] Implementar `permisos` con consultas por modulo.
- [X] Implementar `roles` con asignacion de permisos.

### 4.3 Usuarios

- [X] Completar DTOs de `usuarios`.
- [X] Implementar crear usuario con password hasheada.
- [X] Implementar listado con filtros por estado, dependencia y rol.
- [X] Implementar desactivacion, no borrado fisico.
- [X] Implementar asignacion de roles.
- [X] Evitar devolver `passwordHash` en respuestas.

### 4.4 Pruebas

- [X] Unit tests de usuarios sin exponer password.
- [X] E2E de crear dependencia, rol, permiso y usuario.
- [X] E2E de desactivar usuario.

Criterio de cierre: existe administracion basica para autenticar y autorizar.

---

## 5. Semana 1 y 2 - Autenticacion centralizada

Objetivo: reemplazar el login simulado del frontend por auth real.

### 5.1 Dependencias

- [X] Instalar `@nestjs/jwt`.
- [X] Instalar libreria de hash aprobada, por ejemplo `bcryptjs`.
- [X] Definir si se usara Passport o guard JWT propio simple.

### 5.2 DTOs

- [X] `LoginDto`: usuario/correo y contrasena.
- [X] `AuthResponseDto` o mapper: token, usuario, permisos, aplicaciones habilitadas.
- [X] No devolver hash ni datos sensibles.

### 5.3 Servicio

- [X] Buscar usuario por `nombreUsuario` o `correo`.
- [X] Validar estado `ACTIVA`.
- [X] Comparar contrasena hasheada.
- [X] Firmar JWT con `sub`, `nombreUsuario`, `dependenciaId`, roles y permisos resumidos.
- [X] Devolver permisos por modulo para Gestion de Aulas.
- [X] Preparar respuesta para selector de aplicativos:
  - [X] puedeAccederAulas
  - [X] puedeAccederMonitores
  - [X] urlMonitores si aplica

### 5.4 Guards y decoradores

- [X] Crear `JwtAuthGuard`.
- [X] Crear `CurrentUser` decorator.
- [X] Crear `PermissionsGuard`.
- [X] Crear `RequirePermissions` decorator.
- [X] Permitir modo temporal sin permisos solo durante integracion inicial si el equipo lo necesita, pero documentarlo.

### 5.5 Endpoints

- [X] `POST /auth/login`
- [X] `GET /auth/me`
- [X] `POST /auth/logout` si se decide manejar lista de revocacion; si no, documentar logout frontend.

### 5.6 Pruebas

- [X] Unit tests de login exitoso.
- [X] Unit tests de password invalida.
- [X] E2E de ruta protegida con y sin token.

Criterio de cierre: frontend puede reemplazar `saveDemoSession` por token real.

---

## 6. Semana 2 - Auditoria transversal

Objetivo: registrar operaciones criticas sin duplicar codigo en cada modulo.

### 6.1 Alcance MVP

- [ ] Registrar cambios en usuarios, roles, permisos, aulas, horarios, prestamos, credenciales y multas.
- [X] Guardar usuarioId, entidad, entidadId, accion, datosPrevios y datosNuevos.
- [X] No registrar secretos en texto plano.

### 6.2 Implementacion

- [X] Completar `AuditoriaService`.
- [X] Crear metodo `registrar`.
- [X] Crear helper para sanitizar campos sensibles.
- [X] Definir acciones estandar: CREATE, UPDATE, DELETE, DISABLE, APPROVE, CANCEL, LOGIN.
- [ ] Integrar manualmente en servicios criticos durante MVP.

### 6.3 Endpoints

- [X] `GET /auditoria?entidad=&entidadId=&usuarioId=&desde=&hasta=`
- [X] Proteger solo para administradores.

### 6.4 Pruebas

- [X] Unit test de sanitizacion.
- [X] Unit test de registro.
- [ ] E2E de consulta protegida.

Criterio de cierre: operaciones criticas quedan trazables para la prueba piloto.

---

## 7. Semana 7 - Integracion con Gestion de Monitores

Objetivo: preparar comunicacion por API sin mezclar bases de datos.

### 7.1 Principios

- [X] Gestion de Aulas autentica y autoriza.
- [X] Gestion de Monitores conserva su propia API y base.
- [X] La comunicacion se hace por HTTP/API.
- [X] No crear migraciones para tablas internas de Monitores en este backend.
- [ ] Usar identificadores externos cuando se necesite relacion logica.

### 7.2 Cliente HTTP

- [X] Crear modulo `integraciones`.
- [X] Crear `MonitoresClientService`.
- [X] Leer `MONITORES_API_URL` desde config.
- [X] Definir timeouts y manejo de errores.
- [X] Crear DTOs de respuesta esperada, no usar `any`.

### 7.3 Endpoints puente

- [X] `GET /integraciones/monitores/estado`
- [X] `GET /integraciones/monitores/usuario/:usuarioExternoId` si se requiere.
- [X] Evitar endpoints que repliquen toda la API de Monitores sin necesidad.

### 7.4 Pruebas

- [X] Unit tests con HTTP mockeado.
- [X] E2E de estado con servicio mock si no existe API real disponible.

Criterio de cierre: el selector de aplicativos puede validar acceso sin acoplar bases.

---

## 8. Semana 8 - Integracion general y endurecimiento

Objetivo: preparar una version interna utilizable.

### 8.1 Checklist tecnico

- [ ] Todos los modulos funcionales importan `PrismaModule` correctamente.
- [ ] No quedan servicios productivos con respuestas `This action...`.
- [ ] No quedan DTOs vacios en modulos marcados como implementados.
- [ ] Todas las rutas protegidas tienen guard.
- [ ] CORS permite el frontend local.
- [ ] Health endpoint responde.
- [ ] Migraciones corren desde cero.
- [X] Seeds minimos crean permisos, roles y usuario administrador inicial.

### 8.2 Checklist de pruebas

- [ ] `npm test -- --runInBand`.
- [ ] `npm run test:e2e`.
- [X] `npx tsc --noEmit --incremental false`.
- [ ] Smoke manual:
  - login;
  - crear aula;
  - crear horario;
  - consultar disponibilidad;
  - crear prestamo;
  - consultar panel.

### 8.3 Documentacion

- [ ] Actualizar README del backend.
- [X] Documentar variables de entorno.
- [ ] Documentar flujo de migraciones.
- [ ] Documentar usuario admin inicial.
- [X] Documentar contratos minimos para frontend.

Criterio de cierre: los otros frentes pueden integrar sin depender de conocimiento informal.

---

## 9. Orden recomendado de entrega

1. Configuracion global y health.
2. PrismaModule y PrismaService.
3. Convenciones de errores, DTOs y pipes.
4. Dependencias, modulos, permisos y roles.
5. Usuarios.
6. Auth y guards.
7. Auditoria.
8. Cliente de integracion con Monitores.
9. Seeds, documentacion y pruebas generales.

Este orden reduce riesgo porque primero entrega las bases compartidas y despues habilita seguridad e integraciones.
