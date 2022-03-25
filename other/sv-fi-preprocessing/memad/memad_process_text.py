import pandas as pd
import string
import re
import os
import sys
from num2words import num2words

memad_non_alphanumeric = ".:?,+-'()%"
memad_remove = ":?+'()"
decimal_number = re.compile(r'[0-9]+\.[0-9]+')
decimal_number_comma = re.compile(r'[0-9]+\,[0-9]+')

def remove_non_alphanumeric(text):
    text_p = text
    for c in memad_remove:
        text_p = text_p.replace(c, '')
    
    return text_p

def is_decimal_number(word):
    return re.search(decimal_number, word)

def is_decimal_number_with_comma(word):
    return re.search(decimal_number_comma, word)

def is_number(word):
    return is_decimal_number(word) or word.isnumeric()

def process_periods(word):
    if '.' in word:
        if word.index('.') == len(word) - 1:
            return word.replace('.', '')
        elif is_decimal_number(word):
            return word
        else:
            return word.replace('.', ' ')
    else:
        return word

def process_commas(word):
    if ',' in word:
        if word.index(',') == len(word) - 1:
            return word.replace(',', '')
        elif is_decimal_number_with_comma(word):
            return word.replace(',', '.')
        else:
            return word.replace(',', ' ')
    return word

def number_to_year(word):
    #This dataset only contains these years
    if word[0:2] == '18':
        return 'artonhundra' + num2words(word[2:], lang='sv')
    if word[0:2] == '19':
        return 'nittonhundra' + num2words(word[2:], lang='sv')
    if word[0:2] == '20':
        return 'tjugohundra' + num2words(word[2:], lang='sv')

def process_text(df):
    processed_text = []
    for text in df['text']:
        text_p = text.lower()
        text_p = remove_non_alphanumeric(text_p)
        text_p = text_p.replace('%', ' procent')
        text_p = text_p.replace('-', ' ')
        text_p = text_p.replace('+', 'plus')
        words = text_p.split()
        new_words = []
        for word in words:
            if word in string.whitespace:
                continue
            word = process_periods(word)
            word = process_commas(word)
            if is_decimal_number(word):
                word = num2words(word, lang='sv')
            elif is_number(word) and not len(word) == 4:
                word = num2words(word, lang='sv')
            elif is_number(word):
                if int(word) > 1800 and int(word) < 2050:
                    word = number_to_year(word)
                else:
                    word = num2words(word, lang='sv')
            word = word.strip()
            if len(word) == 0:
                continue
            new_words.append(word)
        processed_text.append(' '.join(new_words))
    return processed_text

def main():
    if len(sys.argv) != 2:
        print('usage: python3 memad_process_text.py data_folder')
        print('e.g.:  python3 memad_process_text.py generated/data/memad')
        exit(1)

    data_folder = sys.argv[1]
    df = pd.read_csv(os.path.join(data_folder, 'memad_sv_fi_transcriptions.csv'))
    processed_text = process_text(df)
    del df['text']
    df['processed_text'] = processed_text
    df.to_csv(os.path.join(data_folder, 'memad_sv_fi_transcriptions_processed.csv'), index=False)

if __name__ == "__main__":
    main()