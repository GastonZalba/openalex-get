import os
import re
import json
import psutil
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

last_row = 1

# para saber cuánto tarda en hacerse el proceso
elapsed_time = 0
start_time = None
end_time = None

file_to_continue = None

append_existing_results = False

# Almacena los id de authores ya encontrados (para prevenir duplicados)
author_ids = []

params_sheet = file_output['params_sheet']
works_sheet = file_output['works_sheet']
works_no_country_sheet = file_output['works_no_country_sheet']
authors_no_works_sheet = file_output['authors_no_works_sheet']
authors_no_found_sheet = file_output['authors_no_found_sheet']

# Archivos y carpetas temporales
tmp_folder = '_tmp'
# Añadimos fecha al log temporal para evitar que se sobreescriba en futuras ejecuciones que terminen abruptamente
log_time = datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss')
tmp_log_filename = f'{tmp_folder}/log_tmp_{log_time}.txt'


def init():

    on_error = False

    try:

        global start_time, count_authors, elapsed_time, last_row, append_existing_results, file_to_continue, tmp_log_filename

        # creamos carpeta para almacenar temprarios
        if not os.path.exists(tmp_folder):
            os.makedirs(tmp_folder)

        log(f'{Fore.GREEN}--> PROCESO INICIADO <--{Style.RESET_ALL}')
        
        header = (file_input['header'] -
                  1) if file_input['header'] is not None else None

        log(f'-> Abriendo archivo {file_input["name"]}...')

        # Abrimos la planilla de entrada
        df_input = pd.read_excel(
            file_input['name'],
            sheet_name=file_input['sheet_number'],
            engine='openpyxl',
            header=header
        )

        log(f'{Fore.YELLOW}-> Uso de memoria: {usage()}{Style.RESET_ALL}')

        # 0 si se empieza un archivo nuevo
        init_row_in = 0

        previous_exports = get_previous_exports()

        if len(previous_exports) > 1:

            def get_continue_prompt():
                prompt = input(
                    '¿Querés continuar trabajando con un procesamiento previo? (Y or N): ')

                if prompt.lower() != 'y' and prompt.lower() != 'n':
                    prompt = get_continue_prompt()

                return prompt

            def select_export_prompt():

                print('/t')
                print('Procesamientos existentes:')

                for n, pe in enumerate(previous_exports):
                    print(f'-> {[n+1]} {pe}')
                    
                prompt = input(f'Selecciona el número de ejecución (1-{len(previous_exports)}): ')

                if int(prompt) > (len(previous_exports)) or int(prompt) < 1:
                    prompt = select_export_prompt()

                return previous_exports[int(prompt)-1]

            # para evaluar si hay que continuar procesando el último archivo o hacer uno nuevo
            continue_prompt = get_continue_prompt()

            continue_from_last_file = True if continue_prompt.lower() == 'y' else False

            if continue_from_last_file == True:

                file_to_continue = select_export_prompt()

                log(f'-> Abriendo archivo {file_to_continue}...')

                # Establecemos el valor de comienzo del loop para que continúe desde el último elemento
                init_row_in = get_last_row()
                append_existing_results = True

                log(
                    f'-> El procesamiento va continuar desde la fila número {init_row_in}')

        def get_number_prompt():
            prompt = input('¿Cuántas filas querés buscar?: ')

            if not prompt.isdigit():
                prompt = get_number_prompt()

            return int(prompt)

        start_time = timer()

        limit_results = get_number_prompt()
        print(f'-> Buscando {limit_results} filas')

        log(f'{Fore.YELLOW}-> Uso de memoria: {usage()}{Style.RESET_ALL}')

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

            log(f'{Fore.YELLOW}-> Uso de memoria: {usage()}{Style.RESET_ALL}')


    except Exception as error:
        log(f'{Fore.RED}{error}{Style.RESET_ALL}')
        log(f'{Fore.RED}{traceback.format_exc()}{Style.RESET_ALL}')
        on_error = True

    finally:

        del df_input  # Limpiamos de la memoria el dataframe de entrada

        end_download = timer()
        elapsed_time = round(end_download - start_time)
        show_stats()

        file_name = write_results()

        end_file = timer()
        [time, type] = seconds_to_minutes(round(end_file - end_download))
        log(f'--> Tiempo transcurrido en la escritura: {time} {type}')

        log_params()

        if on_error == True:
            # oh no
            log(f'\n{Fore.RED}ATENCIÓN, hubo errores en el procesamiento{Style.RESET_ALL}')
        
        log('\n')
        log(f'{Fore.GREEN}--> PROCESO TERMINADO EXITOSAMENTE <--{Style.RESET_ALL}')

        if use_log:
            os.rename(f'{tmp_log_filename}',
                      f'{file_output["folder_name"]}/{file_name}/{file_name} - Log.txt')


def open_file_from_sheet(sheet):
    '''
    Devuelve
    '''
    global file_to_continue
    file = f"{file_output['folder_name']}/{file_to_continue}/{file_to_continue} - {sheet}.csv"
    return pd.read_csv(file, engine='python')

def get_previous_exports():
    '''
    Obtiene anteriores exportaciones para poder continuar la ejecución
    '''
    # obtenemos todos los exports creados
    list_of_exports = os.listdir(file_output["folder_name"])

    return list_of_exports


def get_last_row():
    '''
    Buscamos el valor de comienzo del loop para que continúe desde el último elemento
    '''
    if not file_to_continue:
        return 0

    df = open_file_from_sheet(params_sheet)
    
    return df['Último elemento'].iloc[-1]


def get_last_process_number():
    '''
    Buscamos el valor del último procesamiento
    '''

    if not file_to_continue:
        return 0

    df = open_file_from_sheet(params_sheet)

    return df['Procesamiento número'].iloc[-1]

def log_params():
    '''
    Guarda parámetros de configuración el log sin printear en consola
    '''
    log('\n', False)
    log('Parámetros de búsqueda:', False)
    log(f'-> File output: ' + str(file_output), False)
    log(f'-> File input: {str(file_input)}', False)
    log(f'-> Join separator: {str(join_separator)}', False)
    log(f'-> Main search: {str(main_search)}', False)
    log(f'-> Secondary search: {str(secondary_search)}', False)
    log(f'-> Country filter: {str(country_filter)}', False)
    log(f'-> Min score relevance: {str(min_score_relevance)}', False)
    log(f'-> Type: {str(type)}', False)
    log(f'-> Use accent Variations: {str(use_accent_variations)}', False)
    log(f'-> Works columns to save: {str(works_columns_to_save)}', False)

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
    [time, type] = seconds_to_minutes(elapsed_time)
    log(f'Tiempo transcurrido en la descarga {time} {type}')
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
            sheet = open_file_from_sheet(sheet_name)
            df = pd.concat([sheet, df], axis=0)

        df = order_columns(df)

        df.to_csv(
            f'{file_path}/{file_name} - {sheet_name}.csv',
            header=header,
            index=index,
            encoding='utf-8-sig'
        )

        del df
    try:

        date = datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss')

        file_name = f"{file_output['name']} ({date})"
        file_path = f"{file_output['folder_name']}/{file_name}"

        # creamos carpeta output
        os.makedirs(file_path)

        log('Escribiendo archivo...')

        # Escribimos hojas
        log(f'-> Escribiendo hoja "{works_sheet}"...')
        write_sheet(res_works_output, works_sheet)

        log(f'-> Escribiendo hoja "{works_no_country_sheet}"...')
        write_sheet(res_works_no_country_output,
                    works_no_country_sheet)

        log(f'-> Escribiendo hoja "{authors_no_found_sheet}"...')
        write_sheet({'Listado': res_authors_not_found},
                    authors_no_found_sheet)

        log(f'-> Escribiendo hoja "{authors_no_works_sheet}"...')
        write_sheet({'Listado': res_authors_no_works}, authors_no_works_sheet)

        [time, type] = seconds_to_minutes(elapsed_time)

        # Guardamos valores del procesamiento
        params = {
            'Procesamiento número': get_last_process_number() + 1,
            'Autores encontrados': count_authors,
            'Trabajos encontrados': len(res_works_output),
            'Autores no encontrados': len(res_authors_not_found),
            'Peticiones a la API': count_request,
            'Tiempo transcurrido en la descarga': f'{time} {type}',
            'Fecha': datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss'),
            'Último elemento': last_row
        }

        log(f'-> Escribiendo hoja "{params_sheet}"...')
        write_sheet(pd.DataFrame(params, index=[0]), params_sheet)

        log(f'{Fore.GREEN}--> Export finalizado "{file_name}" <--{Style.RESET_ALL}')

    except Exception as error:
        log(f'{Fore.RED}{error}{Style.RESET_ALL}')
        log(f'{Fore.RED}{traceback.format_exc()}{Style.RESET_ALL}')

    finally:
        return file_name



def log(arg, _print = True):
    '''
    Print que además crea un archivo log si está activado
    '''
    
    if _print:
        print(arg)

    if use_log == True:
        with open(f"{tmp_log_filename}", "a", encoding="utf-8") as file:
            date = datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss')
            if arg == '\n':
                file.write(arg)
            else:
                # ansi scape tor emove colorama colors
                arg = re.compile(
                    r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]').sub('', arg)
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
                        # print(f'{Fore.YELLOW}{error}{Style.RESET_ALL}')
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
                    value = join_separator.join(str(v) for v in l)
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


def seconds_to_minutes(sec):
    min = sec / 60

    if (min) > 2:
        return [round(min,2), 'minutos']
    else:
        return [round(sec), 'segundos']


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


def usage():
    process = psutil.Process(os.getpid())
    return str(round(process.memory_info()[0] / float(2 ** 20), 2)) + ' MB'


init()
