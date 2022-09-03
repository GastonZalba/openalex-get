import requests
import json
from unidecode import unidecode

from log import log

import params
import helpers

# API URL y ENDPOINTS
API_URL = 'https://api.openalex.org'

# Parámetros de la API #
PER_PAGE = 'per-page'

# 200 resultados por página es el límite de la api, pero en algunas peticiones esto rompe y el servidor no responde
# ej.: https://api.openalex.org/works?filter=author.id:A2162365789,type:journal-article&page=1&per-page=200
PER_PAGE_WORKS_VALUE = 20

PER_PAGE_AUTHORS_VALUE = 100
LIMIT_AUTHORS_PAGES = 20

SEARCH = 'search'
MAILTO = 'mailto'
FILTER = 'filter'
PAGE = 'page'

names_variation_list = []

# abrimos el listado de nombres sin acentos
f = open('nombres-acento.json', encoding="utf8")
data_names_accents = json.load(f)
# Por cada nombre, creamos su versión sin tildes y guardamos ambas en una lista
for i in data_names_accents:
    names_variation_list.append([i, unidecode(i)])

surnames_variation_list = []
f = open('apellidos-acento.json', encoding="utf8")
data_surnames_accents = json.load(f)

# Por cada nombre, creamos su versión sin tildes y guardamos ambas en una lista
for i in data_surnames_accents:
    surnames_variation_list.append([i, unidecode(i)])

COUNT = 0

def get_author(author, search_type='main', page=1):

    global COUNT

    search = []

    def create_accent_variation(surname, name):

        if params.use_accent_variations == False:
            search.append(f'{surname} {name}')
        else:

            # separamos el string en palabras
            accented_strings = []

            for original_surname in surname.split(' '):

                modified_string = original_surname

                # reemplazamos apellidos
                for s in surnames_variation_list:
                    surname_with_accents = s[0]
                    surname_no_accents = s[1]

                    if surname_no_accents.lower() == original_surname.lower():
                        modified_string = surname_with_accents

                accented_strings.append(modified_string)

            for original_name in name.split(' '):

                modified_string = original_name

                # Buscamos cada uno de los nombres del autor en el listado de nombres con acentos
                for n in names_variation_list:
                    name_with_accents = n[0]
                    name_no_accents = n[1]

                    # Si hay un matcheo, hacemos reemplazo del nombre poniendo la versión con tildes
                    if name_no_accents.lower() == original_name.lower():
                        modified_string = name_with_accents

                accented_strings.append(modified_string)

            accented_strings = ' '.join(accented_strings)

            search.append(accented_strings)

            # Si tiene acentos el nombre, los removemos y lo añadimos a la búsqueda como alternativa
            if helpers.has_accents(accented_strings):
                search_without_accents = helpers.remove_accents(accented_strings)
                search.append(search_without_accents)

    variations = author.split('|')

    for variation in variations:

        # separamos en la coma que está luego del apellido
        a = variation.strip().split(',')

        # obtenemos sólo el apellido
        surname = a[0]

        # removemos espacios vacíos
        names = a[1].strip()

        # separamos en espacios para obtener primer y segundo nombre
        names_list = names.split(' ')
        first_name = names_list[0]
        second_name = names_list[1] if len(names_list) > 1 else None

        if search_type == 'main':

            if params.main_search['use_fullname'] == True:
                create_accent_variation(surname, names)

            if params.main_search['use_first_name_initial_second_name'] and second_name is not None:
                nn = f'{first_name} {second_name[0]}'
                create_accent_variation(surname, nn)

            if params.main_search['use_first_name_only'] and second_name is not None:
                # Sólo buscamos por apellido y primer nombre
                create_accent_variation(surname, first_name)

        else:

            if params.secondary_search['use_second_name_only'] == True and second_name is not None:
                # Sólo buscamos por apellido y segundo nombre
                create_accent_variation(surname, second_name)

            if params.secondary_search['use_initials_name_only'] == True:
                # Sólo buscamos por apellido e iniciales
                if second_name is not None:
                    nn = f'{first_name[0]} {second_name[0]}'
                    create_accent_variation(surname, nn)
                else:
                    create_accent_variation(surname, first_name[0])

            surname_list = surname.split(' ')

            if len(surname_list) > 1:
                if params.secondary_search['use_first_surname_only'] == True:

                    if params.secondary_search['use_fullname'] == True:
                        create_accent_variation(surname_list[0], names)

                    if params.secondary_search['use_first_name_initial_second_name'] == True and second_name is not None:
                        nn = f'{first_name} {second_name[0]}'
                        create_accent_variation(surname_list[0], nn)

                    if params.secondary_search['use_first_name_only'] == True and second_name is not None:
                        # Sólo buscamos por apellido y primer nombre
                        create_accent_variation(surname_list[0], first_name)

                if params.secondary_search['use_second_surname_only'] == True:

                    # Usamos la segunda palabra del apellido siempre y cuando no sea "de"
                    second_surname = surname_list[1] if surname_list[1].lower(
                    ) != 'de' else surname_list[2]

                    if params.secondary_search['use_fullname'] == True:
                        create_accent_variation(second_surname, names)

                    if params.secondary_search['use_first_name_initial_second_name'] == True and second_name is not None:
                        nn = f' {first_name} {second_name[0]}'
                        create_accent_variation(second_surname, nn)

                    if params.secondary_search['use_first_name_only'] == True and second_name is not None:
                        # Sólo buscamos por apellido y primer nombre
                        create_accent_variation(second_surname, first_name)

    params_obj = {
        FILTER: 'display_name.search:' + '|'.join(search),
        MAILTO: params.email,
        PAGE: page,
        PER_PAGE: PER_PAGE_AUTHORS_VALUE
    }

    if page == 1:
        log(f'> Parámetros de búsqueda: {params_obj[FILTER]}')

    url = API_URL + '/authors'

    r = requests.get(
        url=url,
        params=params_obj
    )

    COUNT += 1

    try:
        data = r.json()
    except Exception:
        raise ValueError('La API devolvió una respuesta inválida')

    # Limitamos el pedido para no descargar cientos y cientos de páginas
    # la api los devuelve en orden de relevancia (tentativo) y en las primeras páginas
    # ya debeían estar los matcheos que buscamos
    if page <= LIMIT_AUTHORS_PAGES:        

        log(f'-> Buscando autor {author}, página {page}...')

        # si los resultados superan lo 10000, ya no se puede acceder mediante paginado
        # y no existe el campo meta
        if 'meta' in data:
            if data['meta']['count'] > PER_PAGE_WORKS_VALUE * page:
                new_page = get_author(author, search_type, page + 1)
                if 'results' in new_page:
                    data['results'] = [*data['results'], *new_page['results']]

    return data


def get_works(author_id, page=1):

    global COUNT

    search_filter = f'author.id:{author_id}'

    type = params.type

    if type is not None:
        type = '|'.join(type) if isinstance(type, list) else type
        search_filter += f',type:{type}'

    params_obj = {
        # sólo un autor por petición y del tipo especificado en params.py
        FILTER: search_filter,
        MAILTO: params.email,
        PAGE: page,
        PER_PAGE: PER_PAGE_WORKS_VALUE,
    }

    url = API_URL + '/works'

    r = requests.get(
        url=url,
        params=params_obj
    )

    COUNT += 1

    try:
        data = r.json()
    except Exception:
        raise ValueError('La API devolvió una respuesta inválida')

    log(f'---> Buscando trabajos del autor {author_id}, página {page}...')

    if data['meta']['count'] > PER_PAGE_WORKS_VALUE * page:
        new_page = get_works(author_id, page + 1)
        data['results'] = [*data['results'], *new_page['results']]

    return data
