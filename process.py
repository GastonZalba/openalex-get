import io
import os
import re
import json
import glob
import requests
import traceback
import pandas as pd
from datetime import datetime
from unidecode import unidecode
from colorama import init, Fore, Style
from timeit import default_timer as timer

# importamos los parámetros del script
from params import *

# fix colorama colors in windows console
init(convert=True)

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
res_works_no_country_output = []

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

file_to_continue = None

params_sheet = 'Params'

append_existing_results = False

# Almacena los id de authores ya encontrados (para prevenir duplicados)
author_ids = []

tmp_filename = "openalex_tmp.xlsx"


def init():

    on_error = False

    try:

        global start, tmp_filename, count_authors, elapsed_time, process_number, last_row, append_existing_results, file_to_continue

        # si existe un archivo temporario, lo removemos por las dudas
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)

        start = timer()

        log(f'{Fore.GREEN}--> PROCESO INICIADO <--{Style.RESET_ALL}')
           
        header = (file_input['header'] - 1) if file_input['header'] is not None else None

        # Abrimos la planilla de entrada
        df_input = pd.read_excel(
            io=file_input['name'], sheet_name=file_input['sheet_number'], engine='openpyxl', header=header)

        # 0 si se empieza un archivo nuevo
        init_row_in = 0

        file_to_continue = get_last_file()

        if file_to_continue != None:

            def get_continue_prompt():
                prompt = input(
                    '¿Querés continuar trabajando con el último archivo? (Y or N): ')

                if prompt.lower() != 'y' and prompt.lower() != 'n':
                    prompt = get_continue_prompt()

                return prompt

            # para evaluar si hay que continuar procesando el último archivo o hacer uno nuevo
            continue_prompt = get_continue_prompt()

            continue_from_last_file = True if continue_prompt.lower() == 'y' else False

            if continue_from_last_file == True:

                with open(file_to_continue, "rb") as f:
                    file_ = io.BytesIO(f.read())

                df_prev = pd.read_excel(
                    file_, sheet_name=params_sheet, engine='openpyxl')
                process_number = df_prev['Procesamiento número'].iloc[-1]

                # Establecemos el valor de comienzo del loop para que continúe desde el último elemento
                init_row_in = df_prev['Último elemento'].iloc[-1]
                append_existing_results = True

                log(
                    f'-> Procesamiento continúa desde archivo exitente, fila número {init_row_in}')

                df_prev = None

        def get_number_prompt():
            prompt = input('¿Cuántas filas querés buscar?: ')

            if not prompt.isdigit():
                prompt = get_number_prompt()

            return int(prompt)

        limit_results = get_number_prompt()
        print(f'-> Buscando {limit_results} filas')

        # loopeamos por cada fila de la planilla
        for i in range(init_row_in, len(df_input)):

            # si no hay límite establecido se loopean por todos los valores
            if i >= limit_results + init_row_in:
                break

            author = df_input.iloc[i][file_input['author_column_number']]

            log('\n')
            log(f'BÚSQUEDA NÚMERO {i + 1} - {author}')

            # Primero buscamos el nombre del autor en la api
            author_results = get_author_from_api(author)

            count_author_results = author_results['meta']['count']

            log(
                f'-> Autores matcheados para el autor {author}: {count_author_results}')

            # Si la búsqueda del autor no devuelve ninguna coincidencia guardamos el dato para mostrarlo luego
            # y continuamos con el siguiente autor
            if count_author_results == 0:
                works_count_1 = None
            else:
                works_count_1 = search_author(
                    author_results, main_search['limit_authors_results'], i, df_input)

            log(f'-> {works_count_1} works encontrados en primera instancia')

            # Si en una primera búsqueda no se encontró nada, hacemos una segunda más flexible
            if works_count_1 == None or works_count_1 <= secondary_search['min']:
                log(f'-> Realizando búsqueda ampliada... {author}')

                # Búsqueda secundaria
                author_results = get_author_from_api(
                    author, search_type='secondary')
                works_count_2 = search_author(
                    author_results, secondary_search['limit_authors_result'], i, df_input)

                log(f'-> {works_count_2} works encontrados en segunda instancia')

            if works_count_1 == None and works_count_2 == None:
                res_authors_not_found.append(author)
            else:
                count_authors += 1

            if works_count_1 == 0 and works_count_2 == 0:
                res_authors_no_works.append(author)

        log('\n')
        log(f'{Fore.GREEN}--> PROCESO TERMINADO EXITOSAMENTE <--{Style.RESET_ALL}')

    except Exception as error:
        log(f'{Fore.RED}{error}{Style.RESET_ALL}')
        log(f'{Fore.RED}{traceback.format_exc()}{Style.RESET_ALL}')
        on_error = True

    finally:

        df_input = None  # Limpiamos de la memoria el dataframe de entrada

        end = timer()
        elapsed_time = round(end - start)
        show_stats()
        write_results()

        if on_error == True:
            log(f'{Fore.RED}ATENCIÓN, hubo errores en el procesamiento{Style.RESET_ALL}')  # oh no


def get_last_file():
    '''
    Obtiene el último archivo creado para poder continuar la ejecución
    '''
    last_file = None

    # obtenemos todos los archivos creados
    list_of_files = glob.glob(
        f'{file_output["folder_name"]}/{file_output["name"]}*.xlsx')

    if len(list_of_files):
        # seleccionamos el archivo más nuevo
        last_file = max(list_of_files, key=os.path.getctime)

    return last_file


def show_stats():
    '''
    Estadísticas a mostrar para cuando se termina de ejecutar todo el script
    '''
    log(f'-----------------------------------')
    log(f'{Fore.GREEN}Autores encontrados: {count_authors}{Style.RESET_ALL}')
    log(f'{Fore.GREEN}Trabajos encontrados: {len(res_works_output)}{Style.RESET_ALL}')
    log(f'{Fore.YELLOW}Autores no encontrados: {len(res_authors_not_found)}{Style.RESET_ALL}')
    log(f'{Fore.YELLOW}Autores sin trabajos: {len(res_authors_no_works)}{Style.RESET_ALL}')
    log(f'Peticiones a la API: {count_request}')
    log(f'Tiempo transcurrido (segundos): {elapsed_time}')
    log(f'-----------------------------------')


def write_results():
    '''
    Guardamos los resultados en un archivo Excel
    '''
    def order_columns(df):
        '''
        Ordenamos las columnas para que aquellas que se crean dinámicamente desde arrays
        queden todas juntas
        '''
        cols = df.columns.tolist()

        new_order = []
        new_order_2 = []

        # Primero ordenamos los array dentro de cada columna
        for col in cols:
            # Buscamos aquellas columnas creadas desde un array
            match = re.findall('(\([0-9]*\))', str(col))
            if match:
                for m in match:
                    # Obtenemos el nombre original de esa columna y buscamos todas sus variantes
                    col_name_trim = col.split(m)[0].strip()
                    col_first_part = f'{col_name_trim} {m}'
                    for _col in cols:
                        if col_first_part in str(_col):
                            if _col in new_order:
                                continue
                            new_order.append(_col)
            else:
                if col in new_order:
                    continue
                new_order.append(col)

        # Por último juntamos todas las columnas que se llaman igual
        for col in new_order:
            if '(1)' in str(col):
                col_name_trim = col.split('(1)')[0].strip()
                for _col in new_order:
                    if col_name_trim in str(_col):
                        if _col in new_order_2:
                            continue
                        new_order_2.append(_col)
            else:
                if col in new_order_2:
                    continue
                new_order_2.append(col)

        df = df[new_order_2]
        return df

    def write_sheet(results, sheet_name, header=True, index=False):

        df = pd.DataFrame(results)

        # Si hay que continuar un archivo existente, agregamos las nuevas filas al final
        if append_existing_results:
            with open(file_to_continue, "rb") as f:
                file_io_obj = io.BytesIO(f.read())

            df_prev = pd.read_excel(
                file_io_obj, sheet_name=sheet_name, engine='openpyxl')
            df = pd.concat([df_prev, df], axis=0)

        df_prev = None
        df = order_columns(df)

        df.to_excel(
            writer, sheet_name=sheet_name, header=header, index=index
        )

        df = None

    # Creamos archivo xls con resultados
    writer = pd.ExcelWriter(tmp_filename)

    log('Escribiendo archivo...')

    # Escribimos hojas
    write_sheet(res_works_output, 'Works')
    write_sheet(res_works_no_country_output, 'Works sin coincidencia de país')
    write_sheet({'Listado': res_authors_not_found}, 'Autores no encontrados')
    write_sheet({'Listado': res_authors_no_works}, 'Autores sin works')

    # Guardamos valores del procesamiento
    params = {
        'Procesamiento número': process_number + 1,
        'Autores encontrados': count_authors,
        'Trabajos encontrados': len(res_works_output),
        'Autores no encontrados': len(res_authors_not_found),
        'Peticiones a la API': count_request,
        'Tiempo transcurrido (segundos)': elapsed_time,
        'Fecha': datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss'),
        'Último elemento': last_row
    }

    write_sheet(pd.DataFrame(params, index=[0]), params_sheet)

    # Guardamos xls
    writer.close()

    if append_existing_results:
        # Removemos archivo viejo
        os.remove(file_to_continue)

    # Renombramos temporal
    date = datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss')

    # creamos carpeta output si no existe
    if not os.path.exists(file_output['folder_name']):
        os.makedirs(file_output['folder_name'])

    file_name = f"{file_output['folder_name']}/{file_output['name']} ({date})"
    os.rename(tmp_filename, file_name + '.xlsx')

    log(f'{Fore.GREEN}--> Archivo creado {file_name} <--{Style.RESET_ALL}')

    if use_log:
        os.rename('log.txt', file_name + '_log.txt')


def log(arg):
    '''
    Print que además crea un archivo log si está activado
    '''
    print(arg)

    if use_log == True:
        with open("log.txt", "a", encoding="utf-8") as file:
            date = datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss')
            if arg == '\n':
                file.write(arg)
            else:
                # ansi scape tor emove colorama colors
                arg = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]').sub('', arg)
                file.write(f'{date} {arg}\n')


def search_author(author_results, limit_authors_results, i, df):
    '''
    Devuelve la cantidad de trabajos encontrados del autor según los filtros establecidos
    '''
    global last_row, author_ids

    # Revisamos que al menos una de las "variantes" encontradas del autor tenga un trabajo
    filtered_works_count = 0

    total_works_count_from_author = 0

    authors_variations = 0

    # Por cada autor encontrado buscamos sus trabajos
    for author_found in author_results['results']:

        valid_country = False if country_filter['country_code'] is not None else True

        if authors_variations >= limit_authors_results:
            break

        # Si está seteado el filtro, sólo nos quedamos con los autores de un determinado país
        if country_filter['country_code'] is not None:

            if author_found['last_known_institution'] is None:
                valid_country = None
            else:
                # Si el autor no es de este país, continuamos
                if author_found['last_known_institution']['country_code'] in country_filter['country_code']:
                    valid_country = True

        author_name = author_found['display_name']
        relevance_score = author_found['relevance_score'] if 'relevance_score' in author_found else None

        if min_score_relevance is not None:
            if relevance_score is None or relevance_score < min_score_relevance:
                continue

        # la api devuelve una dirección url como id. Nosotros necesitamos solamente el número final (después del /)
        author_id = author_found['id'].rsplit('/', 1)[-1]

        # si este autor ya fue guardado lo salteamos
        if author_id in author_ids:
            continue

        author_ids.append(author_id)

        works_results = get_works_from_api(author_id)
        count_works_results = works_results['meta']['count']

        # check country
        if country_filter['country_code'] is not None:
            if valid_country == False or valid_country is None:
                for workFound in works_results['results']:
                    try:
                        for autorship in workFound['authorships']:
                            for inst in autorship['institutions']:
                                # Si un autorship de un trabajo es coincidente, lo tomamos como válido
                                if inst['country_code'] in country_filter['country_code']:
                                    valid_country = True
                    except Exception as error:
                        log(f'{Fore.YELLOW}{error}{Style.RESET_ALL}')
                        pass

            if valid_country == False:
                continue

            if country_filter['preserve_null'] != True:
                if valid_country == None:
                    continue

        if count_works_results != 0:
            filtered_works_count = count_works_results
            total_works_count_from_author += filtered_works_count

        log(f'---> {count_works_results} trabajos encontrados para autor {author_name} - {author_id} - Score: {relevance_score}')

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

            if isinstance(valid_country, bool):
                valid_country = 0 if valid_country == False else 1           

            results['Código de país válido'] = valid_country          
           
            results['relevance_score'] = relevance_score

            for column_to_save in works_columns_to_save:

                subcolumns_list = column_to_save.split('.')

                parse_column_values(subcolumns_list, workFounds, results)

            if valid_country == None:
                res_works_no_country_output.append(results)
            else:
                res_works_output.append(results)

    return total_works_count_from_author


def parse_column_values(cols, api_values, results, num='', name=''):
    '''
    Transforma los valores devueltos por la api según
    las columnas especificadas que dedan guardarse
    '''

    value = ''

    # cuando hay un array, agregamos el número identificador del elemento
    _num = f' ({num}) ' if num != '' else ' '

    col_name = f'{name}{_num}'

    value = api_values
    skip = False

    for i in range(len(cols)):
        try:

            if isinstance(value, list):
                join = True if len(cols[i].split(':join')) > 1 else False

                if join:
                    col = cols[i].split(':join')[0]
                    l = []
                    for a in value:
                        l.append(a[col])
                    value = ', '.join(str(v) for v in l)
                    break
                else:
                    skip = True
                    next_cols = cols[(i):]
                    next_cols = next_cols if isinstance(
                        next_cols, list) else [next_cols]

                    prev_cols = cols[:(i)]
                    prev_cols = prev_cols if isinstance(
                        prev_cols, list) else [prev_cols]

                    for i, val in enumerate(value):
                        col_ = f'{col_name}{".".join(prev_cols)}'
                        parse_column_values(
                            next_cols, val, results, num=i+1, name=col_)

                    break
            else:
                col = cols[i]
                # ingresamos a cada subatributo
                if col == '':
                    value = value
                else:
                    if col in value:
                        value = value[col]
                    else:
                        value = None
                        break

        except Exception as error:
            log(f'{Fore.YELLOW}Error: {error}{Style.RESET_ALL}')
            log(f'{Fore.RED}{traceback.format_exc()}{Style.RESET_ALL}')
            continue

    if skip != True:
        col_name += f'{".".join(cols)}'

        # Para prevenir que los booleanos a veces se guarden como "True" y otras como 1, pasamos todos a 1.
        # Este problema surge principalmente al mergear con un excel existente
        # El problema persiste incluso si se guarda como string "True" o "TRUE".
        if isinstance(value, bool):
            value = 0 if value == False else 1

        results[f'{col_name}'] = value


def get_author_from_api(author, search_type='main'):

    global count_request

    search = []

    def create_accent_variation(surname, name):

        if use_accent_variations == False:
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
            if has_accents(accented_strings):
                search_without_accents = remove_accents(accented_strings)
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

            if main_search['use_fullname'] == True:
                create_accent_variation(surname, names)

            if main_search['use_first_name_initial_second_name'] and second_name is not None:
                nn = f'{first_name} {second_name[0]}'
                create_accent_variation(surname, nn)

            if main_search['use_first_name_only'] and second_name is not None:
                # Sólo buscamos por apellido y primer nombre
                create_accent_variation(surname, first_name)

        else:

            if secondary_search['use_second_name_only'] == True and second_name is not None:
                # Sólo buscamos por apellido y segundo nombre
                create_accent_variation(surname, second_name)

            if secondary_search['use_initials_name_only'] == True:
                # Sólo buscamos por apellido e iniciales
                if second_name is not None:
                    nn = f'{first_name[0]} {second_name[0]}'
                    create_accent_variation(surname, nn)
                else:
                    create_accent_variation(surname, first_name[0])

            surname_list = surname.split(' ')

            if len(surname_list) > 1:
                if secondary_search['use_first_surname_only'] == True:

                    if secondary_search['use_fullname'] == True:
                        create_accent_variation(surname_list[0], names)

                    if secondary_search['use_first_name_initial_second_name'] == True and second_name is not None:
                        nn = f'{first_name} {second_name[0]}'
                        create_accent_variation(surname_list[0], nn)

                    if secondary_search['use_first_name_only'] == True and second_name is not None:
                        # Sólo buscamos por apellido y primer nombre
                        create_accent_variation(surname_list[0], first_name)

                if secondary_search['use_second_surname_only'] == True:

                    # Usamos la segunda palabra del apellido siempre y cuando no sea "de"
                    second_surname = surname_list[1] if surname_list[1].lower(
                    ) != 'de' else surname_list[2]

                    if secondary_search['use_fullname'] == True:
                        create_accent_variation(second_surname, names)

                    if secondary_search['use_first_name_initial_second_name'] == True and second_name is not None:
                        nn = f' {first_name} {second_name[0]}'
                        create_accent_variation(second_surname, nn)

                    if secondary_search['use_first_name_only'] == True and second_name is not None:
                        # Sólo buscamos por apellido y primer nombre
                        create_accent_variation(second_surname, first_name)

    params = {
        FILTER: 'display_name.search:' + '|'.join(search),
        MAILTO: email,
        PER_PAGE: PER_PAGE_VALUE
    }

    log(f'Parámetros de búsqueda: {params[FILTER]}')

    url = API_URL + '/authors'

    r = requests.get(
        url=url,
        params=params
    )

    data = r.json()

    count_request += 1

    return data


def get_works_from_api(author_id, page=1):

    global count_request, type

    search_filter = f'author.id:{author_id}'

    if type is not None:
        type = '|'.join(type) if isinstance(type, list) else type
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

    log(f'--> Buscando trabajos del autor {author_id}, página {page}...')

    if data['meta']['count'] > PER_PAGE_VALUE * page:
        new_page = get_works_from_api(author_id, page + 1)
        data['results'] = [*data['results'], *new_page['results']]

    return data


def remove_accents(input_str):
    '''
    Remueve tildes, manteniendo otros caracteres especiales como la "ñ"
    '''
    new = input_str.lower()
    new = re.sub(r'[àáâãäå]', 'a', new)
    new = re.sub(r'[èéêë]', 'e', new)
    new = re.sub(r'[ìíîï]', 'i', new)
    new = re.sub(r'[òóôõö]', 'o', new)
    new = re.sub(r'[ùúûü]', 'u', new)
    return new


def has_accents(s):
    '''
    Chequea si un string tiene tildes
    '''
    return re.search(r'[àáâãäåèéêëìíîïòóôõöùúûü]+', s, flags=re.IGNORECASE)


init()
