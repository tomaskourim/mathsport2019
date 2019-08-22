import os


def write_file(path: str, binary: bool, data):
    output_directory = os.path.dirname(path)

    if not os.path.exists(output_directory):
        os.makedirs(output_directory, exist_ok=True)

    text_file = open(path, 'wb') if binary else open(path, 'w', encoding='utf-8')
    with text_file:
        text_file.write(data)


def write_textfile(path: str, data: str):
    write_file(path, False, data)
