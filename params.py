# Limitar cantidad de filas a evaluar
# Limitar a un número bajo en testeos
limit_results = 10

# Añadir correo para entrar en el "polite pool" de la api
email = 'gastonzalba@outlook.com'

# Configuración del Excel usado como input
input_file_name = 'input.xlsx'

# columna donde está guardado apellido y nombre de los autores (comienza en 0)
author_column_number = 0

# número de hoja donde se encuentran los nombres de los autores (comeinza en 0)
sheet_number = 1

output_file_name = 'openalex-results.xlsx'

# Poner `True` para utilizar solamente el primer nombre en la búsqueda en la API. Esto es útil
# porque de otro modo autores cargados sin el segundo nombre (o con una versión abreviada) no
# matchean la búsqueda.
only_use_first_name = True

# Filtramos los works que son journal-article
type = 'journal-article'

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
