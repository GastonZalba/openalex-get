# Añadir correo para entrar en el "polite pool" de la api
email = 'gastonzalba@outlook.com'

file_input = {
    # Configuración del Excel usado como input
    "name": 'input.xlsx',

    # columna donde está guardado apellido y nombre de los autores (comienza en 0)
    "author_column_number": 0,

    # número de hoja donde se encuentran los nombres de los autores (comienza en 0)
    "sheet_number": 1
}

file_output = {
    # carpeta donde se guardan los resultados
    "folder_name": 'results',

    # nombre del archivo (se agregará automáticamente la fecha de creación)
    "name": 'openalex-results'
}

main_search = {
    "limit_authors_results": 2,  # Cantidad de variaciones a guardar
    "use_fullname": True, # Buscar con el nombre completo
    "use_first_name_initial_second_name": True, # Buscar con el primer nombre y la inicial del segundo
    "use_first_name_only": True # Buscar solo con el primer nombre    
}

# Búsqueda que se realiza si la primera no devuelve X cantidad de resultados
secondary_search = {
    "min": 10,  # Cantidad de works hallados en la búsqueda principal hasta la cual se realiza la búsueda secundaria
    "limit_authors_result": 1,  # Cantidad de variaciones a guardar
    "use_fullname": True, # Buscar con el nombre completo
    "use_first_name_initial_second_name": True, # Buscar con el primer nombre y la inicial del segundo
    "use_first_name_only": True, # Buscar solo con el primer nombre    
    "use_initials_name_only": True,  # Para autores que firman solo con las iniciales
    "use_second_name_only": True,  # Buscar sólo el segundo nombre
    "use_first_surname_only": True,  # Buscar sólo el primer apellido (solo se aplica a apellidos dobles)
    "use_second_surname_only": True  # Buscar sólo el segundo apellido (solo se aplica a apellidos dobles)
}

# Si se habilita, resultados que estén por debajo de este valor no serán tomados en cuenta
# y también se descartarán aquellos valores que no contengan ningún valor
# Ej: `500`. `None` para deshabilitar
min_score_relevance = None

country_filter = {
    # Primero se revisa el campo last_known_institution https://docs.openalex.org/about-the-data/author#last_known_institution
    # y luego el valor de todos los trabajos encontrados de ese autor 
    # Ej.: ['AR', 'CA']. `None` para deshabilitar
    "country_code": ['AR'],

    # Para descartar o mantener los valores vacíos
    # En caso de que se preserven, estos se crearán en una hoja separada
    # `True` or `False`
    "preserve_null": True
}

# Filtramos los works que son journal-article
# Ej.: `['journal-article', 'null']`. `None` para deshabilitar
type = ['journal-article', 'null']

# True para agregar tildes a través del matcheo comparativo con las listas
use_accent_variations = True

# Columnas a guardar
# Cada "." supone guardar el campo que está dentro de otro de mayor jerarquía.
# Cuando el campo que se quiere guardar es una lista/array de valores, se puede agregar `:join` para guardar
# todos los resultados en una sola celda, separados por coma. De otro modo se guardará cada uno 
# en una columna nueva, identificado cada iteración con (1), (2), etc.
works_columns_to_save = [

    'id',
    'doi',
    'title',

    # 'display_name',

    'publication_year',
    'publication_date',

    'ids.openalex',
    'ids.doi',
    'ids.mag',
    'ids.pmid',
    'ids.pmcid',

    'host_venue.url',
    'host_venue.is_oa',
    'host_venue.version',
    'host_venue.license',

    'type',

    'open_access.is_oa',
    'open_access.oa_status',
    'open_access.oa_url',

    'cited_by_count',

    'biblio.volume',
    'biblio.issue',
    'biblio.first_page',
    'biblio.last_page',

    'is_retracted',
    'is_paratext',

    'concepts.display_name:join',

    'alternate_host_venues.display_name',
    'alternate_host_venues.type',
    'alternate_host_venues.url',
    'alternate_host_venues.is_oa',
    'alternate_host_venues.version',
    'alternate_host_venues.license',

    # 'referenced_works',
    # 'related_works',
    # 'abstract_inverted_index',
    # 'cited_by_api_url',
    # 'counts_by_years',

    'updated_date',

    'authorships.author.display_name',
    'authorships.institutions.country_code',
]

# Para crear archivo txt donde se guardan todos los mensajes producidos por el script
# Útil para debuggear código
# `True` o `False`
use_log = True