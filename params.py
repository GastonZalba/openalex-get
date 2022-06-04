# Añadir correo para entrar en el "polite pool" de la api
email = 'gastonzalba@outlook.com'

file_input = {
    # Configuración del Excel usado como input
    "name": 'input.xlsx',

    # columna donde está guardado apellido y nombre de los autores (comienza en 0)
    "author_column_number": 0,

    # número de hoja donde se encuentran los nombres de los autores (comeinza en 0)
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
    "use_first_name_only": True,
    "use_first_name_initial_second_name": True,
    "use_fullname": True
}

# Búsqueda que se realiza si la primera no devuelve X cantidad de resultados
secondary_search = {
    "min": 10,  # Cantidad a partir de la cual se realiza una busqueda ampliada
    "limit_authors_result": 1,  # Cantidad de variaciones a guardar
    "use_first_name_only": True,
    "use_first_name_initial_second_name": True,
    "use_fullname": True,
    "use_initials_name_only": True,  # Para autores que firman solo con las iniciales
    "use_second_name_only": True,  # Para autores que sólo usan su segundo nombre
    "use_first_surname_only": True,  # Sólo se aplica a apellidos dobles
    "use_second_surname_only": True  # Sólo se aplica a apellidos dobles
}

# Usar None para deshabilitar este filtrado
# Si se habilita, resultados que estén por debajo de eeste valor no serán tomados en cuenta
min_score_relevance = None

# None para no usar este filtro
# Primero se revisa el campo last_known_institution https://docs.openalex.org/about-the-data/author#last_known_institution
# El valor debe ser una lista, y se puede incluir más de un valor
filter_country_code = ['AR']

# Filtramos los works que son journal-article
# `None` para no usar filtro por tipo de publicación
type = ['journal-article', 'null']

# True para agregar tildes a través del matcheo comparativo con las listas
use_accent_variations = True

# Columnas que serán guardadas
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

    # 'referenced_works'
    # 'related_works'
    # 'abstract_inverted_index'
    # 'cited_by_api_url'
    # 'counts_by_years'

    'updated_date',

    'authorships.author.display_name',
    'authorships.institutions.country_code',
]

# Para crear archivo txt donde se guardan todos los mensajes producidos por el script
# Útil para debuggear código
use_log = True