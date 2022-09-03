
import os
import re
import psutil

def has_accents(s):
    '''
    Chequea si un string tiene tildes
    '''
    return re.search(r'[àáâãäåèéêëìíîïòóôõöùúûü]+', s, flags=re.IGNORECASE)


def seconds_to_minutes(sec):
    '''
    Convierte minutos a segundos según el tamaño del número para facilitar lectura
    '''
    min = sec / 60

    if (min) > 2:
        return [round(min, 2), 'minutos']
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


def usage():
    '''
    Devuelve la cantidad de RAM usada por el script
    '''
    process = psutil.Process(os.getpid())
    return str(round(process.memory_info()[0] / float(2 ** 20), 2)) + ' MB'