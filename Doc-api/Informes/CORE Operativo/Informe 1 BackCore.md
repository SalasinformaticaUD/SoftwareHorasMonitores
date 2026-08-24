# Informe 1 - Backend

FECHA: 18/08/2026  
TURNO: 6:00 a. m. - 10:00 a. m.  
MONITOR: Ivan Felipe Prado Blanco

## AVANCES:

* Se revisó el documento de análisis y especificación de requisitos del Sistema de Gestión Operativa de las Aulas de Software.
* Se estructuró la base de datos inicial de Gestión de Aulas en `Backend/prisma/schema.prisma`.
* Se incluyeron entidades generales para usuarios, roles, permisos, aulas, horarios, asistencias, software, préstamos, audiovisuales, multas, observaciones, tareas, limpieza, credenciales y auditoría.
* Se creó una segunda base de datos independiente para Gestión de Monitores en `Backend/monitores/prisma/schema.prisma`.
* La base de Monitores contiene las entidades `Monitor`, `VinculacionMonitor`, `RegistroHora` y `NovedadHora`.
* Se dejó definida la relación lógica entre ambas bases mediante `usuarioExternoId`, sin llaves foráneas ni acceso directo entre bases de datos.
* Se crearon las carpetas para migraciones, datos iniciales y documentación de cada base de datos.

## FUNCIONA:

* Estructura conceptual de las dos bases de datos separadas.
* División de entidades por dominios funcionales.
* Documentación inicial de las decisiones de cada base de datos.

## NO FUNCIONA:

* No se han creado ni aplicado migraciones; las tablas aún no existen físicamente en PostgreSQL.
* No se han implementado endpoints, autenticación, servicios ni lógica de negocio.
* No se han definido los contratos de comunicación entre la API de Gestión de Aulas y la API de Monitores.

## NO MODIFICAR:

* No conectar directamente la base de datos de Gestión de Aulas con la base de datos de Monitores.
* No almacenar usuarios, contraseñas, roles ni permisos en la base de datos de Monitores; estos datos pertenecen a Gestión de Aulas.
* No crear una tabla permanente para la disponibilidad de aulas, ya que debe calcularse con horarios, asistencias, préstamos y tareas.

## SIGUIENTE PASO:

* Confirmar los atributos, relaciones, estados e índices de las entidades antes de generar las migraciones.
* Crear las migraciones y los datos iniciales de cada base de datos.
* Definir los contratos de la API de Gestión de Aulas y la API de Monitores.
* Implementar la autenticación centralizada desde Gestión de Aulas.



Estado: Revision, algunas cosas que no se debieron hacer, como crar una bd para monitores, debido a que esta ya existe y aca no toca nada de eso, como dice el documento. Arreglar esa parte, quitar lo de monitores, crear la bd en postgres ( pgadmin ) y conectarla de una vez. Y no era con Next para el back, sino nestjs. 
