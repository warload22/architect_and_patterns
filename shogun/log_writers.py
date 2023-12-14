import os
import datetime
from settings import BASE_DIR, LOGS_DIR_NAME


class ConsoleWriter:

    @staticmethod
    def write(name, text):
        print(f'{name}\t\t{datetime.datetime.now()}\t\t{text}\n')


class FileWriter:

    @staticmethod
    def write(name, text):
        with open(os.path.join(BASE_DIR, LOGS_DIR_NAME, f'{name.replace(" ", "_")}_log.txt'), 'a') as f:
            f.writelines(f'{name}\t\t{datetime.datetime.now()}\t\t{text}\n')
