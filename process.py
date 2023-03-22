import os
import traceback
import pandas as pd
from datetime import datetime
from colorama import Fore, Style
from timeit import default_timer as timer

# importamos los parámetros del script
from log import *

import params
import prompts
import api_requests
import helpers

stat_authors_found_count = 0
stat_authors_not_found_count = 0
stat_authors_no_works_count = 0
stat_works_count = 0

last_row = 1

# para saber cuánto tarda en hacerse el proceso
elapsed_time = 0
start_time = None
end_time = None

file_to_continue = None

append_existing_results = False

# Almacena los id de authores ya encontrados (para prevenir duplicados)
author_ids = []

params_sheet = params.file_output['params_sheet']
works_sheet = params.file_output['works_sheet']
works_no_country_sheet = params.file_output['works_no_country_sheet']
authors_no_works_sheet = params.file_output['authors_no_works_sheet']
authors_no_found_sheet = params.file_output['authors_no_found_sheet']
authors_count_works = params.file_output['authors_count_works_sheet']

# Identificador fecha/tiempo con la que se crearán los archivos
# base_time = datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss')

last_saved = 0

file_path = ''
file_name = ''

process_number = 0


def init():

    on_error = False

    try:

        global last_saved, start_time, stat_authors_found_count, elapsed_time, last_row, append_existing_results, file_to_continue, file_path, file_name, process_number

        df_input = None

        header = (params.file_input['header'] -
                  1) if params.file_input['header'] is not None else None

        # 0 si se empieza un archivo nuevo
        init_row_in = 0

        previous_exports = get_previous_exports()

        if len(previous_exports) > 1:

            # para evaluar si hay que continuar procesando el último archivo o hacer uno nuevo
            continue_prompt = prompts.get_continue_prompt()

            continue_from_last_file = True if continue_prompt.lower() == 'y' else False

            if continue_from_last_file == True:

                file_to_continue = prompts.select_export_prompt(
                    previous_exports)

                print(f'-> Abriendo procesamiento "{file_to_continue}"...')

                # Establecemos el valor de comienzo del loop para que continúe desde el último elemento
                init_row_in = get_last_row()
                append_existing_results = True

        if file_to_continue:
            file_name = file_to_continue
            file_path = f"{params.file_output['folder_name']}/{file_name}"

        else:
            file_name = prompts.add_id_prompt()
            file_path = f"{params.file_output['folder_name']}/{file_name}"

            # Si el archivo ya existe, cancelamos
            if os.path.exists(file_path):
                raise ValueError('Ya existe un procesamiento con ese nombre')

            # creamos carpeta donde almacenaremos este procesameinto
            os.makedirs(file_path)

        set_log_file(file_path, file_name)

        process_number = get_last_process_number() + 1

        log(f'-> Abriendo archivo {params.file_input["name"]}...')

        # Abrimos la planilla de entrada
        df_input = pd.read_excel(
            params.file_input['name'],
            sheet_name=params.file_input['sheet_number'],
            engine='openpyxl',
            header=header
        )

        print(f'{Fore.BLUE}- Uso de memoria: {helpers.usage()} -{Style.RESET_ALL}')

        if file_to_continue:
            log(
                f'-> El procesamiento continúa desde la fila número {init_row_in}')
            last_saved = init_row_in

        limit_results = prompts.get_number_prompt()

        start_time = timer()

        log(f'{Fore.GREEN}--> PROCESO INICIADO <--{Style.RESET_ALL}')

        print(f'-> Buscando {limit_results} filas')

        # loopeamos por cada fila de la planilla
        for i in range(init_row_in, len(df_input)):

            # si no hay límite establecido se loopean por todos los valores
            if i >= limit_results + init_row_in:
                break

            author = df_input.iloc[i][params.file_input['author_column_number']]

            log('\n')
            log(f'BÚSQUEDA NÚMERO {i + 1} - {author}')
            log(f'Realizando búsqueda principal... {author}')

            # Primero buscamos el nombre del autor en la api
            author_results = api_requests.get_author(author)

            count_author_results = author_results['meta']['count']

            works_count_1 = None
            works_count_2 = None
            works_list = []
            works_no_country_list = []

            # Si la búsqueda del autor no devuelve ninguna coincidencia guardamos el dato para mostrarlo luego
            # y continuamos con el siguiente autor
            if count_author_results == 0:
                works_count_1 = None
                log(f'{Fore.YELLOW}-> Autor {author} no fue encontrado en búsqueda principal{Style.RESET_ALL}')
            else:
                stat_authors_found_count += 1

                log(f'{Fore.GREEN}-> {count_author_results} autores devueltos por la API con {author}{Style.RESET_ALL}')

                search = search_author(
                    author,
                    author_results,
                    params.main_search['limit_authors_results'],
                    i,
                    df_input
                )

                works_count_1 = search['count']
                works_list.extend(search['works'])
                works_no_country_list.extend(search['works_no_country'])

                if works_count_1:
                    log(f'{Fore.GREEN}-> {works_count_1} trabajos encontrados en primera instancia{Style.RESET_ALL}')
                else:
                    log(f'{Fore.MAGENTA}-> Sin trabajos encontrados en primera instancia{Style.RESET_ALL}')

            # Si en una primera búsqueda no se encontró nada, hacemos una segunda más flexible
            if params.secondary_search['enabled']:
                if works_count_1 == None or works_count_1 <= params.secondary_search['min']:

                    log(f'Realizando búsqueda secundaria... {author}')

                    # Búsqueda secundaria
                    author_results = api_requests.get_author(
                        author, search_type='secondary')

                    count_author_results = author_results['meta']['count']

                    if count_author_results == 0:
                        works_count_2 = None
                        log(f'{Fore.YELLOW}-> Autor {author} no fue encontrado en búsqueda secundaria{Style.RESET_ALL}')
                    else:
                        log(f'{Fore.GREEN}-> {count_author_results} autores devueltos por la API con {author}{Style.RESET_ALL}')

                        search = search_author(
                            author,
                            author_results,
                            params.secondary_search['limit_authors_result'],
                            i,
                            df_input
                        )

                        works_count_2 = search['count']
                        works_list.extend(search['works'])
                        works_no_country_list.extend(
                            search['works_no_country'])

                        if works_count_2:
                            log(f'{Fore.GREEN}-> {works_count_2} trabajos encontrados en segunda instancia{Style.RESET_ALL}')
                        else:
                            log(f'{Fore.MAGENTA}-> Sin trabajos encontrados en segunda instancia{Style.RESET_ALL}')

                        c1 = 0 if works_count_1 == None else works_count_1
                        t = c1 + works_count_2

                        if t:
                            log(f'{Fore.GREEN}-> {c1 + works_count_2 } trabajos encontrados en total{Style.RESET_ALL}')

            if works_count_1 == None and works_count_2 == None:
                # Almacenamos los autores no encontrados
                add_author_not_found(author)
                log(f'{Fore.MAGENTA}-> Autor {author} no fue encontrado{Style.RESET_ALL}')

            results = {'(ID)': i+1}
            # Obtenemos las columnas presentes en el excel original
            for col in list(df_input.columns):
                results[col] = df_input[col][i]

            # Usamos '-' si esa búsqueda no se hizo
            # si se hizo pero no encontró resultados, dejamos el 0
            c1 = '-' if works_count_1 == None else works_count_1

            if params.secondary_search['enabled']:
                c2 = '-' if works_count_2 == None else works_count_2
                results['Búsqueda principal'] = c1
                results['Búsqueda secundaria'] = c2
                results['TOTAL'] = (0 if c1 == '-' else c1) + \
                    (0 if c2 == '-' else c2)
            else:
                results['TOTAL'] = c1

            # Diccionario donde almacenamos la cantidad de trabajos en cada autor
            add_authors_count_works(results)

            if works_count_1 == 0 and works_count_2 == 0:
                # Diccionario donde almacenamos los autores encontrados pero sin trabajos
                add_author_no_works(author)
                log(f'{Fore.MAGENTA}-> No se encontraron trabajos para autor {author}{Style.RESET_ALL}')
            else:
                # Una vez realizadas las dos búsquedas, guardamos al archivo
                add_work(works_list)

                if (len(works_no_country_list)):
                    add_works_no_country(works_no_country_list)

            last_saved = last_row

            log(f'{Fore.BLUE}- Uso de memoria: {helpers.usage()} -{Style.RESET_ALL}')
            log(f'{Fore.BLUE}- Peticiones a la API acumuladas: {api_requests.COUNT} -{Style.RESET_ALL}')

    except Exception as error:
        log(f'{Fore.RED}{error}{Style.RESET_ALL}')
        log(f'{Fore.RED}{traceback.format_exc()}{Style.RESET_ALL}')
        on_error = True

    finally:
        del df_input  # Limpiamos de la memoria el dataframe de entrada

        end_download = timer()
        elapsed_time = round(end_download - start_time)

        if file_name:
            log(f'\n-> Ejecución terminada "{file_name}"')
            update_params()
            show_stats()
            log_params()

        if on_error == True:
            # oh no
            log(f'\n{Fore.RED}ATENCIÓN, hubo errores en el procesamiento{Style.RESET_ALL}')

        log('\n')
        log(f'{Fore.GREEN}--> PROCESO TERMINADO <--{Style.RESET_ALL}')
        log('\n')


def append_row_to_csv(data, sheet_name, index=False):
    df = pd.DataFrame(data)

    file = f'{file_path}/{file_name} - {sheet_name}.csv'

    if not os.path.exists(file):
        df.to_csv(
            file,
            mode='w',
            index=index,
            header=True,
            encoding='utf-8-sig'
        )
    else:
        df.to_csv(
            file,
            mode='a',
            index=index,
            header=False,
            encoding='utf-8-sig'
        )


def add_author_not_found(author):
    global stat_authors_not_found_count
    stat_authors_not_found_count += 1
    append_row_to_csv([{'Listado': author}], authors_no_found_sheet)


def add_authors_count_works(results):
    append_row_to_csv([results], authors_count_works)


def add_author_no_works(author):
    global stat_authors_no_works_count
    stat_authors_no_works_count += 1
    append_row_to_csv([{'Listado': author}], authors_no_works_sheet)


def add_work(list):
    global stat_works_count
    stat_works_count += len(list)
    append_row_to_csv(list, works_sheet)


def add_works_no_country(list):
    append_row_to_csv(list, works_no_country_sheet)


def update_params():

    [time, type] = helpers.seconds_to_minutes(elapsed_time)

    # Guardamos valores del procesamiento
    params = {
        'Procesamiento número': process_number,
        'Autores encontrados': stat_authors_found_count,
        'Trabajos encontrados': stat_works_count,
        'Autores no encontrados': stat_authors_not_found_count,
        'Peticiones a la API': api_requests.COUNT,
        'Tiempo transcurrido en la descarga': f'{time} {type}',
        'Fecha': datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss'),
        'Último elemento': last_saved
    }

    append_row_to_csv([params], params_sheet)


def open_file_from_sheet(file, sheet):
    '''
    Devuelve
    '''
    file = f"{params.file_output['folder_name']}/{file}/{file} - {sheet}.csv"
    return pd.read_csv(file, engine='python')


def get_previous_exports():
    '''
    Obtiene anteriores exportaciones para poder continuar la ejecución
    '''
    list_of_exports = []

    if os.path.exists(params.file_output["folder_name"]):
        # obtenemos todos los exports creados
        # la última creación la descartamos porque es la actual
        list_of_exports = os.listdir(params.file_output["folder_name"])

    return list_of_exports


def get_last_row():
    '''
    Buscamos el valor de comienzo del loop para que continúe desde el último elemento
    '''
    if not file_to_continue:
        return 0

    df = open_file_from_sheet(file_to_continue, params_sheet)
    return df['Último elemento'].iloc[-1]


def get_last_process_number():
    '''
    Buscamos el valor del último procesamiento
    '''

    if not file_to_continue:
        return 0

    df = open_file_from_sheet(file_to_continue, params_sheet)
    return df['Procesamiento número'].iloc[-1]


def show_stats():
    '''
    Estadísticas a mostrar para cuando se termina de ejecutar todo el script
    '''
    log(f'-----------------------------------')
    log(f'{Fore.GREEN}Autores encontrados: {stat_authors_found_count}{Style.RESET_ALL}')
    log(f'{Fore.GREEN}Trabajos encontrados: {stat_works_count}{Style.RESET_ALL}')
    log(f'{Fore.YELLOW}Autores no encontrados: {stat_authors_not_found_count}{Style.RESET_ALL}')
    log(f'{Fore.YELLOW}Autores sin trabajos: {stat_authors_no_works_count}{Style.RESET_ALL}')
    log(f'Peticiones a la API: {api_requests.COUNT}')
    [time, type] = helpers.seconds_to_minutes(elapsed_time)
    log(f'Tiempo transcurrido en la descarga: {time} {type}')
    log(f'-----------------------------------')


def search_author(author_original_name, author_results, limit_authors_results, i, df):
    '''
    Devuelve la cantidad de trabajos encontrados del autor según los filtros establecidos
    '''
    global last_row, author_ids

    # Revisamos que al menos una de las "variantes" encontradas del autor tenga un trabajo
    filtered_works_count = 0

    total_works_count_from_author = 0

    authors_variations = 0

    results_list = []

    results_list_no_country = []

    # Por cada autor encontrado buscamos sus trabajos
    for author_found in author_results['results']:

        if authors_variations >= limit_authors_results:
            break

        # la api devuelve una dirección url como id. Nosotros necesitamos solamente el número final (después del /)
        author_id = author_found['id'].rsplit('/', 1)[-1]
        author_api_name = author_found['display_name']

        # si este autor ya fue guardado porque matcheó una búsqueda anterior, lo salteamos
        if author_id in author_ids:
            log(f'-> {author_id} - {author_api_name} ya estaba analizado en búsqueda previa, salteado')
            continue

        author_ids.append(author_id)

        if params.custom_filters['discard_extra_words']:

            # si no matchea esta comprobación, seguimos con el siguiente autor
            is_valid = check_invalid_api_words_and_initials(
                author_original_name, author_api_name)

            if not is_valid:
                log(f'{Fore.YELLOW}--> (X) {author_id} descartado: "{author_api_name}" y "{author_original_name}" no son coincidentes{Style.RESET_ALL}')
                continue
            else:
                log(f'--> {author_id} válido: "{author_api_name}" y "{author_original_name}" son coincidentes')

        relevance_score = author_found['relevance_score'] if 'relevance_score' in author_found else None

        if params.custom_filters['min_score_relevance'] is not None:
            if relevance_score is None or relevance_score < params.custom_filters['min_score_relevance']:
                log(f'{Fore.YELLOW}--> Autor {author_api_name} - {author_id} - Score: {relevance_score} decartado: el score no alcanza el mínimo{Style.RESET_ALL}')
                continue

        works_results = api_requests.get_works(author_id)
        count_works_results = works_results['meta']['count']

        # En algunos casos los trabajos devueltos para un autor son 0
        if count_works_results == 0:
            log(f'{Fore.YELLOW}---> (X) {author_id} descartado: no tiene trabajos{Style.RESET_ALL}')
            # skip author
            continue

        # check country
        if params.country_filter['country_code'] is not None:
            valid_country_count = 0
            country_is_null = True
            for work_found in works_results['results']:
                try:
                    valid_country = False
                    for autorship in work_found['authorships']:
                        for inst in autorship['institutions']:

                            if inst['country_code']:
                                # Si llega hasta acá, significa que tiene la data de intituciones/país cargada
                                country_is_null = False

                            # Si un autorship de un trabajo es coincidente, lo tomamos como válido
                            if inst['country_code'] in params.country_filter['country_code']:
                                valid_country = True
                                continue

                        if valid_country == True:
                            break

                    if valid_country == True:
                        # Sumamos un match por cada trabajo que tiene una institución
                        # que matchea con el país buscado
                        valid_country_count += 1

                except Exception:
                    # Capturamos error porque a veces la api no devuelve algunos de los campos
                    # que hay que consultar
                    pass

            if params.country_filter['preserve_null'] != True and country_is_null == True:
                log(f'{Fore.YELLOW}---> (X) {author_id} descartado: no tiene información de país{Style.RESET_ALL}')
                # skip author
                continue

            if params.country_filter['match_percentage'] and country_is_null == False:
                percentage_matched = round(
                    (valid_country_count / count_works_results * 100), 2)

                if (percentage_matched < params.country_filter['match_percentage']):
                    log(f'{Fore.YELLOW}---> (X) {author_id} descartado: baja coincidencia de país ({percentage_matched}%){Style.RESET_ALL}')
                    continue

                log(f'---> {author_id} válido: porcentaje suficiente de concidencia de país ({percentage_matched}%)')

        log(f'{Fore.GREEN}---> {count_works_results} trabajos hallados para autor {author_api_name} - {author_id} - Score: {relevance_score}{Style.RESET_ALL}')

        if count_works_results != 0:
            filtered_works_count = count_works_results
            total_works_count_from_author += filtered_works_count

        authors_variations += 1

        for work_founds in works_results['results']:
            results = {}

            last_row = i + 1
            results['(ID)'] = last_row

            # Obtenemos las columnas presentes en el excel original
            for col in list(df.columns):
                results[col] = df[col][i]

            results['Autor encontrado'] = author_api_name
            results['Autor encontrado id'] = author_id

            results['relevance_score'] = relevance_score

            for column_to_save in params.works_columns_to_save:

                subcolumns_list = column_to_save.split('.')

                parse_column_values(subcolumns_list, work_founds, results)

            if country_is_null and params.country_filter['preserve_null']:
                results_list_no_country.append(results)
            else:
                results_list.append(results)

    return {
        'count': total_works_count_from_author,
        'works': results_list,
        'works_no_country': results_list_no_country
    }


def parse_column_values(cols, api_values, results, name='', arrnum=1):
    '''
    Transforma los valores devueltos por la api según
    las columnas especificadas que dedan guardarse

    @todo debería ser más prolija esta función. Por otro lado, 
    la recursión hace que sea poco clara y difícil de mantener/debuggear
    '''

    value = ''

    def create_list_separator(num):
        # cuando se procesan arrays, agregamos un separador según el número de array examinado
        return f' {(num*params.list_column_separator) + params.list_column_separator } ' if arrnum != 0 else ''

    col_name = f'{name}'

    value = api_values
    skip = False

    for i in range(len(cols)):
        try:

            # si el valor es un array, evaluamos si el usuario quiere hacer un join de los valores,
            # o mantenerlos separados en dsitintas columnas
            if isinstance(value, list):
                join = True if len(cols[i].split(':join')) > 1 else False
                count = True if len(cols[i].split(':count')) > 1 else False

                # jutamos todos los valores en una misma celda
                if join:
                    col = cols[i].split(':join')[0]
                    l = []
                    for a in value:
                        l.append(a[col])
                    value = ', '.join(str(v) for v in l)
                    break
                elif count:
                    col = cols[i].split(':count')[0]
                    l = []
                    for a in value:
                        l.append(a[col])
                    value = len(l)
                    break
                else:
                    skip = True
                    next_cols = cols[(i):]
                    next_cols = next_cols if isinstance(
                        next_cols, list) else [next_cols]

                    prev_cols = cols[:(i)]
                    prev_cols = prev_cols if isinstance(
                        prev_cols, list) else [prev_cols]

                    name = f'{col_name}{".".join(prev_cols)}'

                    # si hay más columnas para iterar en profundidad, llamamos a la función recursivamente
                    if len(next_cols) > 1:
                        name = f'{name}{create_list_separator(arrnum)}'
                        for u, val in enumerate(value):
                            parse_column_values(
                                next_cols, val, results, name=name, arrnum=arrnum+1)
                    else:
                        # estamos en la iteración de la última columna, entonces guardamos
                        __col = next_cols[0]
                        l = []
                        for a in value:
                            if __col in a:
                                l.append(a[__col])
                            else:
                                l.append('')

                        value = create_list_separator(
                            arrnum).join(str(v) for v in l)

                        col_name = f'{name}{create_list_separator(arrnum)}{__col}'

                        # si ya existía esta columna, agregamos los valores al final
                        if col_name in results:
                            results[col_name] = results[col_name] + \
                                create_list_separator(arrnum-1) + value
                        else:
                            results[col_name] = value
                    break
            else:
                col = cols[i]
                # por cada iteración, ingresamos a cada subatributo hasta agotar las columnas
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


def check_invalid_api_words_and_initials(author, author_api):
    '''
    Chequeo customizado para ver si el author devuelto por la api le sobran palabras extras (nombre o apellido)
    Esto es útil para descartar falsos positivos que son devueltos con un leevador Score relevance a pesar de tener nombres distintos
    '''
    # removemos tildes y mayúsculas
    author_api_normalized = helpers.remove_accents(author_api.lower())
    author_api_normalized = author_api_normalized.replace('and ', '').replace(
        ' de ', ' ').replace('.', ' ').replace(',', '').replace('-', ' ').replace('  ', ' ')

    initials_list = []

    # removemos mayúsculas
    author_normalized = helpers.remove_accents(author.lower()).replace(
        '-', ' ').replace(',', '').split(' ')

    is_valid = True

    for author_api_word in author_api_normalized.split(' '):
        # si es una inicial, la agregamos a una lista para compararla luego con todas las palabras que no matchean nada
        if len(author_api_word) == 1:
            initials_list.append(author_api_word)
        else:
            # si una palabra (apellido nombre) es devuelto por la api y no existe en el nombre original,
            # lo descartamos y no seguimos con la comprobación
            if author_api_word not in author_normalized:
                is_valid = False
                break
            else:
                # como ya matcheo esta palabra, la removemos de la comprobación futura de iniciales
                author_normalized.remove(author_api_word)

    # si hasta acá es válido el matcheo, chequeamos iniciales con el resto de las palabras
    # no matcheadas (y si es que existen iniciales)
    if is_valid and len(initials_list):
        valid_initial = True
        for initial in initials_list:
            v = False
            for author_normalized_word in author_normalized:
                if initial == author_normalized_word[0]:
                    v = True
                    break
            if v == False:
                valid_initial = False
                break

        if not valid_initial:
            is_valid = False

    return is_valid


if __name__ == '__main__':
    init()
