FECHA: 16/05/2026
TURNO: 2 pm - 6 pm,
MONITOR: Jhojan Stiven Aragón Ramirez

AVANCES:
- Se hizo una copia de la base de datos.
- Se sacaron todos los monitores hasta el momento registrados.
- Se sacaron los horarios que se cargaron. 
- Se creo una base de datos nueva, para cargar todo de 0, de momento se comprobo que los registros, monitores y horarios sirven importandolos desde la parte grafica. 

FUNCIONA:
- Se crearon consultas SQL para sacar los datos de monitores y horarios. 

NO FUNCIONA:

- El módulo 1 aún no recopila toda la información requerida completamente.
- En el archivo .env se modificaron variables como el correo y la contraseña, para que al cargar los monitores no pudiera enviar correos, solo es descomentarlos.
- En el .env tambien se cambio la direccion de la base de datos, si se quiere ver la base de datos anterior, seria descomentar la monitores, y comentar monitoresv2

NO MODIFICAR:

- Lógica actual de emparejamiento, cálculo de horas e inconsistencias.

SIGUIENTE PASO:

- En la parte grafica hay un apartado en monitores que muestra los retardos y memorandos, depronto es redundante, por que hay un apartado especificamente para eso.
- Realizar pruebas finales para la primera entrega del lunes 18 de mayo.
- Realizar pruebas cargando todos los datos crudos. 