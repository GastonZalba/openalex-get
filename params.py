# Si está en False, el xls anterior se borra y se comienza uno nuevo.
# Si está en True se continúa desde donde se dejó
continue_from_last_file = True

# Limitar cantidad de filas a evaluar
# Limitar a un número bajo en testeos
limit_results = 200

# None para no usar este filtro
# Primero se revisa el campo last_known_institution https://docs.openalex.org/about-the-data/author#last_known_institution
# El valor debe ser una lista, y se puede incluir más de un valor
filter_country_code = ['AR']

# Límite para devolver cantidad de autores matcheados
limit_authors_results = 2

min_relevance_score = 50

# Añadir correo para entrar en el "polite pool" de la api
email = 'tatoz12@hotmail.com'

# Configuración del Excel usado como input
input_file_name = 'input.xlsx'

# columna donde está guardado apellido y nombre de los autores (comienza en 0)
author_column_number = 0

# número de hoja donde se encuentran los nombres de los autores (comeinza en 0)
sheet_number = 1

output_file_name = 'openalex-results'

use_first_name_only = True

use_first_name_initial_second_name = True

use_fullname = True

# Filtramos los works que son journal-article
type = 'journal-article'

# True para agregar tildes a través del matcheo comparativo con las listas
use_accent_variation = True

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
