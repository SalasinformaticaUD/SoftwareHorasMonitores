FECHA: 19/05/2026
TURNO: 6 am - 10 am,
MONITOR: David Felipe Ariza Ariza

AVANCES:
- Correcciones visuales
- Revision de modulos
    - Modulo 1 completo
    - Modulo 2 completo
    - Modulo 3 (Lo que se revisó) completo
    - Modulo 4 completo
    - Modulo 5 por realizar
- En el archivo .env se modificaron variables como el correo y la contraseña, para que al cargar los monitores no pudiera enviar correos, solo es descomentarlos.
- En el .env tambien se cambio la direccion de la base de datos, si se quiere ver la base de datos anterior, seria descomentar la monitores, y comentar monitoresv2

FUNCIONA:


NO FUNCIONA:


NO MODIFICAR:

- Lógica actual de emparejamiento, cálculo de horas e inconsistencias.
- Logica y diseño linea del tiempo

SIGUIENTE PASO:

- Correcciones de la revision de los modulos
    - Dentro del modulo de monitores, poner en negrilla los campos necesarios para la carga masiva, especificar las opciones validas para proyecto curricular y department, lo mismo para el modulo de horarios CHECK
    - Dentro del modulo de memorando cambiar el nombre de Jaime por Edilberto Suárez Torres CHECK
    - Al tercer memorando enviar correo sobre acercarse al almacen para revisar CHECK, revisar texto
    - Agregar en la linea del tiempo el color de no aplica horas extra junto con los demas CHECK
    - Mejorar visualmente el apartado de inconsistencias eliminando dia anterior y dia despues CHECK
    - Eliminar la inconsistencia del historial al crear la anotacion CHECK al invalidar la inconsistencia se crea una anotacion automaticamente de 0 horas, y al crear la anotacion manual se elimina del historial la inconsistencia, se añadió un buscador en las anotaciones para filtrar por monitor, tipo y accion
    - Poner modales de alerta al realizar acciones, ejemplo, al crear una anotacion, o al importar los registros, a todas esas acciones añadir modales

- Investigar requisitos de implementacion del modulo 5