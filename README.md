# openalex-get
Script configurable para extrar datos de [openalex.org](https://openalex.org/rest-api) desde una planilla excel con un listado de autores.

## Anexo metodológico. Detalles del desarrollo del script
- Ver información completa en el [release](https://github.com/GastonZalba/openalex-get/releases/tag/v1.0.0).

## Requerimientos para instalar
- Python. [Descargar](https://www.python.org/downloads/) e instalar en el sistema si hace falta.
- [virtualenv](https://virtualenv.pypa.io/en/latest/). Ejecutar `pip install virtualenv` desde consola.
- Posicionado en la carpeta del proyecto:
    - crear entorno virtual usando virtualenv con el comando `python -m venv .venv`
    - cargar el entorno creado ejecutando `.venv\Scripts\activate`. Si tira error de ejecución de scripts en Windows, modificar [ExecutionPolicy](https://www.alexmedina.net/habilitar-la-ejecucion-de-scripts-para-powershell/) y volver a intentarlo
 - una vez cargado el entorno, ejecutar `pip install -r requirements.txt` para instalar las dependencias


## Limitaciones (05/2022)
- Principalmente por errores en los datos devueltos por openalex: se han visto casos de nombres de autores con errores de tipeo, incompletos, o abreviados de diferentes maneras, o incluso dos autores ingresados como uno solo. Algunos de estos errores pueden potencialmente hacer que las peticiones no devuelvan resultados si se busca el nombre completo de cada autor.

- La API no normaliza valores con y sin tilde, por lo que una búsqueda con "José" no matchea con "Jose", y a la inversa. Para mitigar esto se utiliza el archivo "nombres-acento.json" y "apellidos-acento.json" que tienen un listado de nombres frecuentes que llevan tilde. Al hacer cada búsqueda, si el nombre del autor en el excel de entrada -sin tilde- matchea alguno de esos nombres, se reemplaza la palabra por su versión con tilde. Posteriormente se hace una búsqueda doble (en un solo request) de cada autor: con y sin tilde.

- Existen autores que están cargados con nombre completo, otros sólo con el primer nombre, sólo con el segundo, o sólo apellido e iniciales, o sólo el primer apellido, etc. Por esta razón, cada petición que se hace tiene todas estas variaciones incorporadas (sumadas a la versión con/sin tilde). Por ejemplo, la búsqueda principal de `VILA, Alejandro Jose`, sería `Vilá Alejandro José|vila alejandro jose|Vilá Alejandro J|vila alejandro j|Vilá Alejandro|vila alejandro`. Para activar/desactivar cada una de estas variaciones, modificar el archivo [params.py](params.py).

- Para autores que pueden estar cargados bajo un pseudónimo, ingresar los nombres posibles en la columna del archivo input, separados con un '|'. Ejemplo: `GOLDSCHVARTZ, Adriana Julieta | MARSHALL, Adriana`. En estos casos se buscarán ambas variaciones del mismo autor.

- Se recomienda usar un páginado que tenga poca cantidad de elementos

- El código escribe en los csv de salida a medida que cada autor es descargado y validado. Cuando los valores a guardar son parte de una lista (o array), o una lista dentro de otra lista, el script guardará todos esos valores en una misma columna, separando cada uno ellos con lo establecido en la variable `list_column_separator` (por defecto '|'). A medida que se desciende de nivel por cada una de estas iteraciones en diferentes niveles se agrega un caracter extra ('||', '|||', etc.). Esto posibilita recontruir luego el encolumnado múltiple/original sin importar cuántas listas hay contenidas dentro de una misma celda. Cabe aclarar que el script no crea automáticamente esta separación automática de columnas porque de otro modo no se podría ir escribiendo línea por línea, sino que habría que hacerlo al final una vez que se sepan la cantidad de columnas -y su respectivo nombre-, demandado una gran cantidad de memoria ram y largos tiempos de escritura al finalizar el proceso cuando se buscan listado muy grandes.

## Uso
- Crear una planilla de Excel (nombre por defecto input `input.xlsx`) y colocarla en la raíz del directorio. 
- Poner en la primer columna el apellido y nombre de los autores a buscar. `Ej: Sánchez, José Carlos` (respetar la coma luego del apellido, las mayúsculas no importan).
- Idealmente los nombres deberían contener los tildes (ver las limitaciones de la api sobre el tema).
- Si el archivo de entrada tiene más columnas con información, éstas serán agregadas en el mismo orden en el archivo de salida (en estos casos es recomendable utilizar cabeceras en el archivo de entrada para distinguir cada una de las columnas)
- Configurar el archivo [params.py](params.py) para setear las columnas a guardar, archivo de entrada (`input.xlsx` por defecto), número de hoja, cabecera, correo electrónico, salida (`openalex-results.xlsx`), etc. Ver sección [Parámetros de búsqueda](#parámetros-de-búsqueda)
- Cargar entorno ejecutando `.venv\Scripts\activate`
- Ejecutar `python process.py`
- Establecer por consola una identificación del procesamiento y la cantidad de filas a evaluar en la ejecución
- Si en una primera instancia no se buscan todas las filas existentes en el archivo de entrada, se puede retomar el trabajo en la ejecución siguiente estableciendo por consola que se desea retomar el trabajo

## Parámetros de búsqueda

### Columnas a guardar
Modificar la variable `works_columns_to_save` del archivo [params.py](params.py) con las columnas deseadas.

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
    'authorships.author.id',

    // Número total de elementos encontrados en el array
    'authorships.author:count',

    // Ejemplo para guardar atributos en 3 niveles de profundidad, 
    // y siendo uno de los de mayor jerarquía un array
    'authorships.institutions.country_code',
]
```
