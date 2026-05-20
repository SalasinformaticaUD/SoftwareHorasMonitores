FECHA: 20/05/2026
TURNO: 12 pm - 4 pm,
MONITOR: David Felipe Ariza Ariza

AVANCES:
- Correcciones visuales
- En el archivo .env se modificaron variables como el correo y la contraseña, para que al cargar los monitores no pudiera enviar correos, solo es descomentarlos.
- En el .env tambien se cambio la direccion de la base de datos, si se quiere ver la base de datos anterior, seria descomentar la monitores, y comentar monitoresv2
- Dentro del modulo de monitores se puso en negrilla los campos necesarios para la carga masiva
- Dentro del modulo de memorando se cambió el nombre del encargado
- Al tercer memorando se envia un correo con un texto diferente para cercarse al almacen, verificar texto en apps/reports linea 546
- Se agregó en la linea del tiempo el color de no aplica horas extra
- Se mejoró visualmente el apartado de inconsistencias eliminando dia anterior y dia despues
- Al invalidar una inconsistencia se crea una anotacion automaticamente solo anotar de 0 horas, y al crear la anotacion manual se elimina del historial la inconsistencia, se añadió un buscador en las anotaciones para filtrar por monitor, tipo y accion, y al eliminar una accion asociada a una inconsistencia esta vuelve al modulo de inconsistencias con estado pendiente
- Se crearon modales de alerta al realizar acciones, ejemplo, al crear una anotacion, o al importar los registros

FUNCIONA:
- Logica de las invalidacion y anotacion de inconsistencias

NO FUNCIONA:


NO MODIFICAR:

- Lógica actual de emparejamiento, cálculo de horas e inconsistencias.
- Logica y diseño linea del tiempo
- Logica de las inconsistencias y anotaciones

SIGUIENTE PASO:
- Verificar modales de las acciones
- Investigar requisitos de implementacion del modulo 5