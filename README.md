# openalex-get
Script configurable para extrar datos de [openalex.org](https://openalex.org/rest-api) desde una planilla excel con un listado de autores.

## Requerimientos para instalar
- Python. [Descargar](https://www.python.org/downloads/) e instalar en el sistema si hace falta.
- [virtualenv](https://virtualenv.pypa.io/en/latest/). Ejecutar `pip install virtualenv` desde consola.
- Posicionado en la carpeta del proyecto:
    - crear entorno virtual usando virtualenv con el comando `python -m venv .venv`
    - cargar el entorno creado ejecutando `.venv\Scripts\activate`. Si tira error de ejecución de scripts en Windows, modificar [ExecutionPolicy](https://www.alexmedina.net/habilitar-la-ejecucion-de-scripts-para-powershell/) y volver a intentarlo
 - una vez cargado el entorno, ejecutar `pip install -r requirements.txt` para instalar las dependencias

## Uso
- Cargar en una planilla de Excel, en una sola columna, el apellido y nombre de los autores a buscar. `Ej: Sánchez, José Carlos` (respetar la coma luego del apellido, las mayúsculas no importan).
- Idealmente los nombres deberían contener los tildes (ver debajo las limitaciones de la api sobre el tema).
- Si el archivo de entrada tiene más columnas con información, éstas serán agregadas en el mismo orden en el archivo de salida.
- Configurar el archivo `params.py` para setear las columnas a guardar, archivo de entrada (`input.xlsx` por defecto), salida (`openalex-results.xlsx`), etc. Ver sección [Parámetros de búsqueda](#parámetros-de-búsqueda)
- Cargar entorno ejecutando `.venv\Scripts\activate`
- Ejecutar `python process.py`
- Establecer por consola si se debe continuar un archivo existente (si hay), y la cantidad de filas a evaluar

## Parámetros de búsqueda

### Columnas a guardar
Modificar la variable `works_columns_to_save` del archivo `params.py` con las columnas deseadas.

Cada "." supone guardar el campo que está dentro de otro de mayor jerarquía.
Cuando el campo que se quiere guardar es una lista/array de valores, se puede agregar `:join` para guardar todos los resultados separados por comas en una sola celda. De otro modo se guardará cada uno en una columna nueva, identificado cada iteración con (1), (2), etc.
```js
works_columns_to_save = [

    // Para guardar campos básicos de texto
    'id', 
    'is_paratext',

    // Campos dentro de otro de mayor jerarquía, separados por un "."
    'host_venue.url',
    'host_venue.is_oa',

    // Join a partir de un array de elementos. 
    // En este caso la lista de elementos se guarda en una sola celda, separados por coma
    'concepts.display_name:join',    

    // En los casos que se desean guardar atributos que pertenecen a un array de una categoría superior,
    // el script crea automáticamente una columna nueva por cada iteración.
    // Ej.: alternate_host_venues (1) display_name'
    // Ej.: alternate_host_venues (1) type'
    'alternate_host_venues.display_name',
    'alternate_host_venues.type',

    // Ejemplo para guardar atributos en 3 niveles de profundidad
    'authorships.author.display_name',
    'authorships.institutions.country_code',
]
```

### Limitaciones (05/2022)
- Principalmente por errores en los datos devueltos por openalex: se han visto casos de nombres de autores con errores de tipeo, incompletos, o abreviados de diferentes maneras, o incluso dos autores ingresados como uno solo. Algunos de estos errores pueden potencialmente hacer que las peticiones no devuelvan resultados si se busca el nombre completo de cada autor. Para minimizar esto, se elimina el segundo nombre en las búsquedas desde el script, que es donde hay mayores inconsistencias en los valores cargados (esto se puede desactivar poniendo como `False` la variable `only_use_first_name`).

- La API no normaliza valores con y sin tilde, por lo que una búsqueda con "José" no matchea con "Jose", y a la inversa. Para mitigar esto se utiliza el archivo "nombres-acento.json" que tiene un listado de nombres frecuentes que llevan tilde. Al hacer cada búsqueda, si el nombre del autor en el excel de entrada -sin tilde- matchea alguno de esos nombres, se reemplaza la palabra por su versión con tilde. Posteriormente se hace una búsqueda doble (en un solo request) de cada autor: con y sin tilde.

## TODO
- Actualizar README
- Ordenar columnas