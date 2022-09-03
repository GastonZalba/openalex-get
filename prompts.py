def get_number_prompt():
    prompt = input('¿Cuántas filas querés buscar?: ')

    if not prompt.isdigit():
        prompt = get_number_prompt()

    return int(prompt)


def add_id_prompt():
    prompt = input(
        'Escriba una identificación para este procesamiento: ')

    if not prompt:
        prompt = add_id_prompt()

    return prompt


def get_continue_prompt():
    prompt = input(
        '¿Querés continuar trabajando con un procesamiento previo? (Y or N): ')

    if prompt.lower() != 'y' and prompt.lower() != 'n':
        prompt = get_continue_prompt()

    return prompt


def select_export_prompt(previous_exports):

    print('/t')
    print('Procesamientos existentes:')

    for n, pe in enumerate(previous_exports):
        print(f'-> {[n+1]} {pe}')

    prompt = input(
        f'Selecciona el número de ejecución (1-{len(previous_exports)}) a continuar: ')

    if int(prompt) > (len(previous_exports)) or int(prompt) < 1:
        prompt = select_export_prompt()

    return previous_exports[int(prompt)-1]