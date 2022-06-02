import io
import os
import re
import json
import requests
import traceback
import pandas as pd
from csv import writer
from unidecode import unidecode
from timeit import default_timer as timer
import time

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
PAGE = 'page'

count_request = 0

# lista final con todos los trabajos encontrados
res_works_output = []

# autores que no se encontraron en la api
res_authors_not_found = []

# autores de los cuales no se halló ningún trabajo
res_authors_no_works = []

res_authors_no_country_code = []

count_authors = 0

process_number = 0

elapsed_time = 0

last_row = 1

# para saber cuánto tarda en hacerse el proceso
start = None
end = None

params_sheet = 'Params'

append_existing_results = False

def init():

    try:

        global start, count_authors, elapsed_time, process_number, last_row, append_existing_results

        start = timer()

        print(f'--> PROCESO INICIADO <--')

        # Abirmos la planilla de entrada
        df = pd.read_excel(io=input_file_name, sheet_name=sheet_number, engine='openpyxl')
        
        # 0 si se empieza un archivo nuevo
        init_row_in = 0

        if continue_from_last_file == True:
            if os.path.exists(output_file_name + '.xlsx'):
                with open(output_file_name + '.xlsx', "rb") as f:
                    file_io_obj = io.BytesIO(f.read())

                df_prev = pd.read_excel(file_io_obj, sheet_name=params_sheet, engine='openpyxl')
                process_number = df_prev['Procesamiento número'].iloc[-1]

                # Establecemos el valor de comienzo del loop para que continúe desde el último elemento
                init_row_in = df_prev['Último elemento'].iloc[-1]
                append_existing_results = True
                print('Procesamiento se continúa desde el autor número', init_row_in )

        # loopeamos por cada fila de la planilla
        for i in range(init_row_in, len(df)):

            # si no hay límite establecido se loopean por todos los valores
            if i >= limit_results + init_row_in:
                break

            author = df.iloc[i][author_column_number]

            print('Búsqueda número', i + 1)

            print('Buscando...', author)

            # Primero buscamos el nombre del autor en la api
            author_results = get_author_from_api(author, search_number = 2)

            works_count = search_author(author_results, limit_authors_results, i, df)
    
            # Si en una primera búsqueda no se encontró nada, hacemos una segunda más flexible
            if works_count <= loose_search_min or works_count == None:
                print('Realizando búsqueda ampliada...', author)
                
                # loose search
                author_results = get_author_from_api(author, search_number = 2)
                works_count = search_author(author_results, limit_authors_result_loose, i, df)
                
            if works_count == None:
                res_authors_not_found.append(author)
            else:
                count_authors += 1

            if works_count == 0:
                res_authors_no_works.append(author)

        print(f'--> PROCESO TERMINADO EXITOSAMENTE <--')

    except Exception as error:
        print(error)
        print(traceback.format_exc())
        print('ATENCIÓN, hubo errores en el procesamiento')  # oh no

    finally:
        end = timer()
        elapsed_time = round(end - start)
        showStats()
        writeResults()


def showStats():
    '''
    Estadísticas a mostrar para cuando se termina de ejecutar todo el script
    '''
    print(f'Autores encontrados: {count_authors}')
    print(f'Trabajos encontrados: {len(res_works_output)}')
    print(f'Autores no encontrados: {len(res_authors_not_found)}')
    print(f'Autores sin trabajos: {len(res_authors_no_works)}')
    print(f'Peticiones a la API: {count_request}')
    print(f'Tiempo transcurrido (segundos): {elapsed_time}')


def writeResults():
    '''
    Guardamos los resultados en un archivo Excel
    '''

    def writeSheet(results, sheet_name, header=True, index=False):
        
        df = pd.DataFrame(results)

        # Si hay que continuar un archivo existente, agregamos las nuevas filas al final
        if append_existing_results:
            with open(output_file_name + '.xlsx', "rb") as f:
                file_io_obj = io.BytesIO(f.read())

            df_prev = pd.read_excel(file_io_obj, sheet_name=sheet_name, engine='openpyxl')
            df = pd.concat([df_prev, df], axis=0)

        df.to_excel(
            writer, sheet_name=sheet_name, header=header, index=index
        )

    tmp_filename = output_file_name + '_tmp' + '.xlsx'

    # Creamos archivo xls con resultados
    writer = pd.ExcelWriter(tmp_filename)
    
    print('Escribiendo archivo...')

    # Escribimos hojas
    writeSheet(res_works_output, 'Resultados')
    writeSheet({'Listado': res_authors_not_found}, 'Autores no encontrados')
    writeSheet({'Listado': res_authors_no_works}, 'Autores sin works')

    # Guardamos valores del procesamiento
    params = {
        'Procesamiento número': process_number + 1,
        'Autores encontrados': count_authors,
        'Trabajos encontrados': len(res_works_output),
        'Autores no encontrados': len(res_authors_not_found),
        'Peticiones a la API': count_request,
        'Tiempo transcurrido (segundos)': elapsed_time,
        'Fecha': time.strftime("%c"),
        'Último elemento': last_row
    }

    writeSheet(pd.DataFrame(params, index=[0]), params_sheet)

    # Guardamos xls
    writer.close()

    if append_existing_results:
        # Removemos archivo viejo
        os.remove(output_file_name + '.xlsx')

    # Renombramos temporal
    os.rename(tmp_filename, output_file_name + '.xlsx')

    print('--> Archivo creado con éxito <--')


def search_author(author_results, limit_authors_results, i, df):
    '''
    Devuelve la cantidad de trabajos encontrados del autor según los filtros establecidos
    '''
    count_author_results = author_results['meta']['count']

    print('-> Resultados', count_author_results)

    # Si la búsqueda del autor no devuelve ninguna coincidencia guardamos el dato para mostrarlo luego
    # y continuamos con el siguiente autor
    if count_author_results == 0:        
        return None

    # Revisamos que al menos una de las "variantes" encontradas del autor tenga un trabajo
    filtered_works_count = 0

    authors_variations = 0

    # Por cada autor encontrado buscamos sus trabajos
    for author_found in author_results['results']:
        valid_country = False

        if authors_variations >= limit_authors_results:
            break

        # Si está seteado el filtro, sólo nos quedamos con los autores de un determinado país
        if filter_country_code is not None:

            if author_found['last_known_institution'] is None:
                valid_country = None
            else:
                # Si el autor no es de este país, continuamos
                if author_found['last_known_institution']['country_code'] in filter_country_code:
                    valid_country = True

        author_name = author_found['display_name']
        relevance_score = author_found['relevance_score'] if 'relevance_score' in author_found else None
        
        # Si ya se encontró un author, nos ponemos más estrictos para incluir un segundo resultado
        if authors_variations > 0:
            
            if valid_country == False or valid_country == None:
                continue
            
            # if relevance_score is None or relevance_score < min_relevance_score:
            #     continue

        # la api devuelve una dirección url como id. Nosotros necesitamos solamente el número final (después del /)
        author_id = author_found['id'].rsplit('/', 1)[-1]

        works_results = get_works_from_api(author_id)
        count_works_results = works_results['meta']['count']
        
        # check country
        if valid_country == False or valid_country is None:
            for workFound in works_results['results']:
                try:
                    for autorship in workFound['authorships']:
                        for inst in autorship['institutions']:
                            # Si un autorship de un trabajo es coincidente, lo tomamos como válido
                            if inst['country_code'] in filter_country_code:
                                valid_country = True
                except Exception as error:
                    print(error)
                    pass
        
        if valid_country == False:
            continue
        
        if count_works_results != 0:
            filtered_works_count = count_works_results
        
        print('--> Autor encontrado', author_name,
                author_id, f'Score: {relevance_score}')

        authors_variations += 1

        for workFounds in works_results['results']:                                    
            results = {}
            
            last_row = i + 1
            results['(ID)'] = last_row

            # Obtenemos las columnas presentes en el excel original
            for col in list(df.columns):
                results[col] = df[col][i]

            results['Autor encontrado'] = author_name
            results['Autor encontrado id'] = author_id
            results['Código de país válido'] = valid_country

            results['relevance_score'] = relevance_score

            for column_to_save in works_columns_to_save:

                # chequeamos si la columna está seteada para hacer un join de valores
                j = column_to_save.split(':join')

                column_to_save = j[0]

                join = True if len(j) > 1 else False

                subcolumns_list = column_to_save.split('.')

                api_column_values = workFounds[subcolumns_list[0]]

                getValues(subcolumns_list,
                            api_column_values, results, join)

            res_works_output.append(results)

    return filtered_works_count
    

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


def get_author_from_api(author, search_number = 1):

    global count_request

    search = []

    def createAccentVariation(string_to_search):
        def has_accents(s):
            """Check if the characters in string s are in ASCII, U+0-U+7F."""
            return re.search(r'[àáâãäåèéêëìíîïòóôõöùúûü]+', s, flags=re.IGNORECASE)

        if use_accent_variations == True:
            
            # separamos el string en palabras
            strings = string_to_search.split(' ')
            
            accented_strings = []

            for original_string in strings: 
                
                modified_string = original_string

                # reemplazamos apellidos
                for s in surnames_variation_list:
                    surname_with_accents = s[0]
                    surname_no_accents = s[1]

                    if surname_no_accents.lower() == original_string.lower():
                        modified_string = surname_with_accents

                # Buscamos cada uno de los nombres del autor en el listado de nombres con acentos
                for n in names_variation_list:
                    name_with_accents = n[0]
                    name_no_accents = n[1]

                    # Si hay un matcheo, hacemos reemplazo del nombre poniendo la versión con tildes
                    if name_no_accents.lower() == original_string.lower():
                        modified_string = name_with_accents

                accented_strings.append(modified_string)
            
            accented_strings = ' '.join(accented_strings)

            search.append(accented_strings)

            # Si tiene acentos el nombre, los removemos y lo añadimos a la búsqueda como alternativa
            if has_accents(accented_strings):
                search_without_accents = remove_accents(accented_strings)
                search.append(search_without_accents)

        else:
            search.append(string_to_search)

    variations = author.split('//')

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

        if search_number == 1:

            if use_fullname:
                ss = f'{surname} {names}'
                createAccentVariation(ss)
        
            if use_first_name_initial_second_name and second_name is not None:
                ss = f'{surname} {first_name} {second_name[0]}'
                createAccentVariation(ss)

            if use_first_name_only and second_name is not None:
                # Sólo buscamos por apellido y primer nombre
                ss = f'{surname} {first_name}'
                createAccentVariation(ss)
            
        else:

            if use_second_name_only and second_name is not None:
                # Sólo buscamos por apellido y segundo nombre
                ss = f'{surname} {second_name}'
                createAccentVariation(ss)
            
            if use_initials_name_only:
                # Sólo buscamos por apellido e iniciales
                if second_name is not None:
                    ss = f'{surname} {first_name[0]} {second_name[0]}'
                    createAccentVariation(ss)
                else:
                    ss = f'{surname} {first_name[0]}'
                    createAccentVariation(ss)

            surname_list = surname.split(' ')
            
            if len(surname_list) > 1:
                if use_first_surname_only:

                    if use_fullname:
                        ss = f'{surname_list[0]} {names}'
                        createAccentVariation(ss)
                
                    if use_first_name_initial_second_name and second_name is not None:
                        ss = f'{surname_list[0]} {first_name} {second_name[0]}'
                        createAccentVariation(ss)

                    if use_first_name_only and second_name is not None:
                        # Sólo buscamos por apellido y primer nombre
                        ss = f'{surname_list[0]} {first_name}'
                        createAccentVariation(ss)

                if use_second_surname_only:
                    
                    # Usamos la segunda palabra del apellido siempre y cuando no sea "de"
                    second_surname = surname_list[1] if surname_list[1].lower() != 'de' else surname_list[2]

                    if use_fullname:
                        ss = f'{second_surname} {names}'
                        createAccentVariation(ss)
                
                    if use_first_name_initial_second_name and second_name is not None:
                        ss = f'{second_surname} {first_name} {second_name[0]}'
                        createAccentVariation(ss)

                    if use_first_name_only and second_name is not None:
                        # Sólo buscamos por apellido y primer nombre
                        ss = f'{second_surname} {first_name}'
                        createAccentVariation(ss)

    params = {
        FILTER: 'display_name.search:' + '|'.join(search),
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


def get_works_from_api(author_id, page = 1):

    global count_request

    search_filter = f'author.id:{author_id}'

    if type is not None:
        search_filter += f',type:{type}'

    params = {
        # sólo un autor por petición y del tipo especificado en params.py
        FILTER: search_filter,
        MAILTO: email,
        PAGE: page,
        PER_PAGE: PER_PAGE_VALUE,
    }

    url = API_URL + '/works'

    r = requests.get(
        url=url,
        params=params
    )

    data = r.json()

    count_request += 1

    print(f'Obteniendo trabajos del autor {author_id}, página', page)

    if data['meta']['count'] > PER_PAGE_VALUE * page:        
        new_page = get_works_from_api(author_id, page + 1)    
        data['results'] = [*data['results'], *new_page['results']]

    return data

def remove_accents(input_str):
    new = input_str.lower()
    new = re.sub(r'[àáâãäå]', 'a', new)
    new = re.sub(r'[èéêë]', 'e', new)
    new = re.sub(r'[ìíîï]', 'i', new)
    new = re.sub(r'[òóôõö]', 'o', new)
    new = re.sub(r'[ùúûü]', 'u', new)
    return new

init()
