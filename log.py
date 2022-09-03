import re
from datetime import datetime
from colorama import init

import params

# fix colorama colors in windows console
init(convert=True)

log_filename = ''

def set_log_file(file_path, file_name):
    '''
    Establece la carpeta/nombre del archivo donde se guardarán los logs
    '''
    global log_filename
    log_filename = f'{file_path}/{file_name} - Log.txt'


def log(arg, _print=True):
    '''
    Print en consola que además guarda un archivo log si está activado
    '''

    if _print:
        print(arg)

    if params.use_log:
  
        with open(f"{log_filename}", "a", encoding="utf-8") as file:
            date = datetime.today().strftime('%Y-%m-%d %Hhs%Mm%Ss')
            if arg == '\n':
                file.write(arg)
            else:
                # ansi scape tor emove colorama colors
                arg = re.compile(
                    r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]').sub('', arg)
                file.write(f'{date} {arg}\n')


def log_params():
    '''
    Guarda parámetros de configuración el log sin printear en consola
    '''
    log('\n', False)
    log('Parámetros de búsqueda:', False)
    log(f'-> File output: ' + str(params.file_output), False)
    log(f'-> File input: {str(params.file_input)}', False)
    log(f'-> Join separator: {str(params.join_separator)}', False)
    log(f'-> Main search: {str(params.main_search)}', False)
    log(f'-> Secondary search: {str(params.secondary_search)}', False)
    log(f'-> Country filter: {str(params.country_filter)}', False)
    log(f'-> Min score relevance: {str(params.custom_filters)}', False)
    log(f'-> Type: {str(params.type)}', False)
    log(f'-> Use accent Variations: {str(params.use_accent_variations)}', False)
    log(f'-> Works columns to save: {str(params.works_columns_to_save)}', False)