import datetime
import logging
import os

import pystache

from live_betting.reporting.output_writer import write_textfile

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(process)d - %(levelname)s - %(name)s - %(message)s')
    start_time = datetime.datetime.now()

    arguments = {
        'document_type': 'ncccco'
    }

    with open('output_templates/index.html', encoding='utf-8') as template_file:
        template = template_file.read()

    rendered = pystache.render(template, arguments)
    rendered_path = os.path.join('output', 'index.html')
    write_textfile(rendered_path, rendered)

    end_time = datetime.datetime.now()
    logging.info(f"\nDuration: {(end_time - start_time)}")
