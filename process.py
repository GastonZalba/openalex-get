import re
import sys
import json
import requests
import traceback
import pandas as pd
from csv import writer
from unidecode import unidecode
from timeit import default_timer as timer

from params import *

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

# API URL y ENDPOINTS
API_URL = 'https://api.openalex.org'

# Parámetros de la API #
PER_PAGE = 'per-page'
PER_PAGE_VALUE = 200  # 200 resultados por página es el límite de la api
SEARCH = 'search'
MAILTO = 'mailto'
FILTER = 'filter'

count_request = 0

# lista final con todos los trabajos encontrados
res_works_output = []

# autores que no se encontraron en la api
res_authors_not_found = []

# autores de los cuales no se halló ningún trabajo
res_authors_no_works = []

count_authors = 0

# para saber cuánto tarda en hacerse el proceso
start = None
end = None

def init():

    try:

        global start, count_authors

        start = timer()
        
        print(f'--> PROCESO INICIADO <--')

        # Abirmos la planilla de entrada
        df = pd.read_excel(io=input_file_name, sheet_name=sheet_number)

        # loopeamos por cada fila de la planilla
        for i in range(0, len(df)):

            # si no hay límite establecido se loopean por todos los valores
            if i >= limit_results:
                break

            author = df.iloc[i][author_column_number]

            print('Búsqueda número', i + 1)

            print('Buscando...', author)

            # Primero buscamos el nombre del autor en la api
            author_results = getAuthor(author)

            count_author_results = author_results['meta']['count']

            print('-> Resultados', count_author_results)

            # Si la búsqueda del autor no devuelve ninguna coincidencia guardamos el dato para mostrarlo luego
            # y continuamos con el siguiente autor
            if count_author_results == 0:
                res_authors_not_found.append(author)
                continue
            
            count_authors += 1

            # Revisamos que al menos una de las "variantes" encontradas del autor tenga un trabajo
            has_works = False

            # Por cada autor encontrado buscamos sus trabajos
            for authorFound in author_results['results']:
                author_name = authorFound['display_name']
                relevance_score = authorFound['relevance_score'] if 'relevance_score' in authorFound else None

                score = checkScore(author, author_name)

                # la api devuelve una dirección url como id. Nosotros necesitamos solamente el número final (después del /)
                author_id = authorFound['id'].rsplit('/', 1)[-1]

                print('--> Autor encontrado', author_name, author_id, f'Score: {score}')
                
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

                    results['relevance_score'] = relevance_score

                    results['Score'] = score

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
            
        print(f'--> PROCESO TERMINADO EXITOSAMENTE <--')

    except Exception as error:
        print(error)
        print(traceback.format_exc())
        print('ATENCIÓN, hubo errores en el procesamiento')  # oh no

    finally:
        showStats()
        writeResults()

# Estadísticas a mostrar para cuando se termina de ejecutar todo el script
def showStats():
    end = timer()
    print(f'Autores encontrados: {count_authors}')
    print(f'Trabajos encontrados: {len(res_works_output)}')
    print(f'Autores no encontrados: {len(res_authors_not_found)}')
    print(f'Se realizaron {count_request} peticiones a la API')
    print(f'Tiempo transcurrido: {round(end - start)} segundos')


def writeResults():

    # Creamos archivo xls con resultados
    writer = pd.ExcelWriter(output_file_name)

    # Escribimos hojas
    pd.DataFrame(res_works_output).to_excel(
        writer, sheet_name='Resultados', header=True, index=False)
    pd.DataFrame(res_authors_not_found).to_excel(
        writer, sheet_name='Autores no encontrados', header=True, index=False)
    pd.DataFrame(res_authors_no_works).to_excel(
        writer, sheet_name='Autores sin works', header=True, index=False)
    
    # Guardamos xls
    writer.save()

# chequeo customizado para ver si el author tiene que ver con el matcheo
def checkScore(author, author_api):
    
    # removemos tildes y mayúsculas
    author_api_nomalized = unidecode(author_api.lower())
    author_api_nomalized = author_api_nomalized.replace('and ', '').replace('.', '').replace('-', '')

    # removemos mayúsculas
    author_normalized = unidecode(author.lower())
    s = author_normalized.split(',')

    surname = s[0]
    names = s[1].strip().split(' ')
    first_name = names[0]
    second_name = f' {names[1]}' if len(names) > 1 else ''
    initial_second_name = f' {second_name[1]}' if second_name != '' else ''

    val = 0

    skip = False

    # si el nombre aparece completo y en el orden exacto
    if (f'{first_name}{second_name} {surname}' in author_api_nomalized):
        val = 100
        skip = True

    # si el nombre aparece en el orden exacto, pero abreviado el segundo nombre
    elif (f'{first_name}{initial_second_name} {surname}' in author_api_nomalized):
        val = 95
        skip = True

    # si está presente el apellido, el primer nombre y el segundo, match casi perfecto
    elif (surname in author_api_nomalized) \
        and (first_name in author_api_nomalized) \
        and (second_name in author_api_nomalized):
        val = 90

    # si está presente el apellido, primer nombre e inicial del segundo, math bastante bueno
    elif (surname in author_api_nomalized) \
        and (first_name in author_api_nomalized) \
        and (f'{initial_second_name} ' in author_api_nomalized):
        val = 70

    else:
        matchs = 0
        for words in author_normalized.split(' '):
            for wordsApi in author_api_nomalized.split(' '):
                match = similarity(words, wordsApi)
                if (match > 70):
                    matchs += 1
                    continue

        if matchs == len(author_normalized.split(' ')):
            val = 70
        else:
            #apellido y nombres completos (sin segundo nombre)
            if (surname in author_api_nomalized) \
            and (first_name in author_api_nomalized):
                val = 40


    if not skip:
        # si a la api le sobran palabras, lo tomamos como un mal indicio
        if len(author_api_nomalized.split(' ')) > len(author_normalized.split(' ')):
            val = val - 50

        # si a la api le faltan palabras, probablemente sea el segundo nombre, no es tan grave
        if len(author_api_nomalized.split(' ')) < len(author_normalized.split(' ')):
            val = val - 20

        # chequeamos si el segundo nombre devuelto por la api existe en el nombre original
        second_name = author_api_nomalized.split(' ')[1]
        m = False
        # y si lo que está puesto como segundo nombre es una abreviatura, chequeamos que exista como tal
        second_name = second_name if len(second_name) > 1 else f' {second_name}'
        for wordsApi in author_normalized.split(' '):
            match = similarity(second_name, wordsApi)
            if (match > 70):
                m = True
                break
        
        if m == False:
            val = val - 70

    return val if val > 0 else 0

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

    if use_accent_variation == True:
        for surname_acc in surnames_variation_list:
            surname_with_accents = surname_acc[0]
            surname_no_accents = surname_acc[1]

            if surname_no_accents in surname:
                surname = names.replace(surname_with_accents, surname_no_accents)

        # Buscamos cada uno de los nombres del autor en el listado de nombres con acentos
        for nombre in names_variation_list:
            name_with_accents = nombre[0]
            name_no_accents = nombre[1]

            # Si hay un matcheo, hacemos reemplazo del nombre poniendo la versión con tildes
            if name_no_accents in names:
                names = names.replace(name_with_accents, name_no_accents)

    # si está activado para que solo se use el primer nombre
    if use_second_name:
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
        # sólo un autor por petición y del tipo especificado en params.py
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

def similarity(s1, s2):
     return 2. * len(longest_common_substring(s1, s2)) / (len(s1) + len(s2)) * 100

def longest_common_substring(s1, s2):
    m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
    longest, x_longest = 0, 0
    for x in range(1, 1 + len(s1)):
        for y in range(1, 1 + len(s2)):
            if s1[x - 1] == s2[y - 1]:
                m[x][y] = m[x - 1][y - 1] + 1
                if m[x][y] > longest:
                    longest = m[x][y]
                    x_longest = x
            else:
                m[x][y] = 0
    return s1[x_longest - longest: x_longest]



init()
