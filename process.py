import re
import sys
import json
import requests
import traceback
from params import *
from unidecode import unidecode
import pandas as pd
from csv import writer

names_variation_list = []
# abrimos el listado de nombres sin acentos
f = open('nombres-acento.json', encoding="utf8")
data = json.load(f)
# Por cada nombre, creamos su versión sin tildes y guardamos ambas en una lista
for i in data:
    names_variation_list.append([i, unidecode(i)])

# API URL y ENDPOINTS
API_URL = 'https://api.openalex.org'

# Parámetros de la API #
PER_PAGE = 'per-page'
PER_PAGE_VALUE = 200  # 200 resultados por página es el límite de la api
SEARCH = 'search'
MAILTO = 'mailto'
FILTER = 'filter'

count_request = 0

def init():

    try:
        # Abirmos la planilla de entrada
        df = pd.read_excel(io=input_file_name, sheet_name=sheet_number)

        # lista final con todos los trabajos encontrados
        res_works_output = []

        # autores que no se encontraron en la api
        res_authors_not_found = []

        # autores de los cuales no se halló ningún trabajo
        res_authors_no_works = []

        # loopeamos por cada fila de la planilla
        for i in range(0, len(df)):

            # si no hay límite establecido se loopean por todos los valores
            if i >= limit_results:
                break

            author = df.iloc[i][author_column_number]
            print('Search number', i)

            print('Searching', author)

            # Primero buscamos el nombre del autor en la api
            author_results = getAuthor(author)

            count_author_results = author_results['meta']['count']

            print('-> Results', count_author_results)

            # Si la búsqueda del autor no devuelve ninguna coincidencia guardamos el dato para mostrarlo luego
            # y continuamos con el siguiente autor
            if count_author_results == 0:
                res_authors_not_found.append(author)
                continue

            # Revisamos que al menos una de las "variantes" encontradas del autor tenga un trabajo
            has_works = False

            # Por cada autor encontrado buscamos sus trabajos
            for authorFound in author_results['results']:

                # la api devuelve una dirección url como id. Nosotros necesitamos solamente el número final (después del /)
                author_id = authorFound['id'].rsplit('/', 1)[-1]
                author_name = authorFound['display_name']

                print('--> Matched author', author_name, author_id)
                works_results = getWorks(author_id)
                count_works_results = works_results['meta']['count']

                if count_works_results != 0:
                    has_works = True

                for workFound in works_results['results']:
                    results = {}

                    results['(ID)'] = i + 2

                    # Obtenemos las columnas presentes en el excel original
                    for col in list(df.columns):
                        results[col] = df[col][i]

                    results['Autor encontrado'] = author_name

                    for column_to_save in works_columns_to_save:

                        # chequeamos si la columna está seteada para hacerun join de valores
                        j = column_to_save.split(':join')
                        
                        column_to_save = j[0]

                        join = True if len(j) > 1 else False

                        subcolumns_list = column_to_save.split('.')

                        api_column_values = workFound[subcolumns_list[0]]

                        getValues(subcolumns_list, api_column_values, results, join)

                    res_works_output.append(results)

            if has_works == 0:
                res_authors_no_works.append(author)

        # Creamos archivo xls conr esultados
        writer = pd.ExcelWriter(output_file_name)

        # Escribimos hojas
        pd.DataFrame(res_works_output).to_excel(
            writer, sheet_name='Resultados', header=True, index=False)
        pd.DataFrame(res_authors_not_found).to_excel(
            writer, sheet_name='Autores no encontrados', header=True, index=False)
        pd.DataFrame(res_authors_no_works).to_excel(
            writer, sheet_name='Autores sin works', header=True, index=False)

        print(f'Realizados {count_request} requests a la API')

        # Guardamos xls
        writer.save()

    except Exception as error:
        print(error)
        print(traceback.format_exc())
        sys.exit('ATENCIÓN, hubo errores en el procesamiento')  # oh no


def getValues(cols, api_columns_values, results, join=False, num=''):

    name = ''

    if join == True:

        # por si acaso, revisamos que el valor devuelto por la api sea efectivamente un array
        api_columns_values = api_columns_values if isinstance(
            api_columns_values, list) else [api_columns_values]

        l = []

        for a in api_columns_values:

            name = cols[0].upper()

            if len(cols) == 3:
                name += f' {cols[1]}.{cols[2]}'
                # chequeamos que existan la columnas
                if (cols[1] in a):
                    l.append(a[cols[1]][cols[2]])
            elif len(cols) == 2:
                name += f' {cols[1]}'
                # chequeamos que exista la columna
                if (cols[1] in a):
                    l.append(a[cols[1]])
            else:
                l.append(a)
        
        results[f'{name}'] = ', '.join(str(v) for v in l)

    else:
        if isinstance(api_columns_values, list):
            for i, val in enumerate(api_columns_values):
                getValues(cols, val, results, join=False, num=i+1)

        else:
            
            value = ''
            name += cols[0].upper()

            # cuando hay un array, agregamos el número identificador del elemento
            _num = f' ({num}) ' if num != '' else ' '

            if len(cols) == 3:
                # chequeamos que existan la columnas
                if (cols[1] in api_columns_values):
                    name += f' {cols[1]}{_num}{cols[2]}'
                    parent = api_columns_values[cols[1]]

                    # Si es una lista, loopeamos esos elementos
                    if isinstance(parent, list):
                        for i, val in enumerate(parent):
                            value = parent[i][cols[2]]
                            results[f'{name} ({i+1})'] = value
                        return
                    else:
                        value = parent[cols[2]]
            elif len(cols) == 2:
                name += f'{_num}{cols[1]}'
                # chequeamos que exista la columna
                if (cols[1] in api_columns_values):
                    value = api_columns_values[cols[1]]
            else:
                value = api_columns_values

            results[f'{name}'] = value


def getAuthor(author):

    global count_request

    # separamos en la coma que está luego del apellido
    a = author.split(',')

    # obtenemosm sólo el apellido
    surname = a[0]

    # removemos espacios vacíos
    names = a[1].strip()

    # Buscamos cada uno de los nombres del autor en el listado de nombres con acentos
    for nombre in names_variation_list:
        name_with_accents = nombre[0]
        name_no_accents = nombre[1]

        # Si hay un matcheo, hacemos reemplazo del nombre poniendo la versión con tildes
        if name_no_accents in names:
            names = names.replace(name_with_accents, name_no_accents)

    # si está activado para que solo se use el primer nombre
    if only_use_first_name:
        # separamos en espacios para obtener primer y segundo nombre
        names = names.split(' ')

        first_name = names[0]
        # Sólo buscamos por apellido y primer nombre
        search = f'{surname} {first_name}'

    else:
        search = f'{surname} {names}'

    # Si tiene acentos el nombre, los removemos y lo añadimos a la búsqueda como alternativa
    if re.match('^[a-zA-Z]+$', search):
        search_without_accents = unidecode(search)
        search += f'|{search_without_accents}'

    params = {
        SEARCH: search,
        MAILTO: email,
        PER_PAGE: PER_PAGE_VALUE
    }

    url = API_URL + '/authors'

    r = requests.get(
        url=url,
        params=params
    )

    data = r.json()
    
    count_request += 1

    return data


def getWorks(author_id):
    
    global count_request

    params = {
        # only one author per request and only journal-article type
        FILTER: f'author.id:{author_id},type:{type}',
        MAILTO: email,
        PER_PAGE: PER_PAGE_VALUE,
    }

    url = API_URL + '/works'

    r = requests.get(
        url=url,
        params=params
    )

    data = r.json()

    count_request += 1

    return data


init()
