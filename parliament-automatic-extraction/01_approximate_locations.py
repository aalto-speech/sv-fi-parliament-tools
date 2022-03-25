import sys
import json
import pandas as pd
import os
import re
from num2words import num2words
import numpy as np
import pytz
from datetime import datetime, timezone, timedelta

# Requires num2words library: https://github.com/savoirfairelinux/num2words

# Arguments:
# path_to_transcriptions - path to parliament transcriptions folder (refers to the one created by the fin-parliament-tools scripts)
# excluded_sessions - path to file with session ids to be excluded (for example the ones that were used for the first release)

# This script estimates the locations of the speeches in the audio based on the session start times and the speech start and end times
# This process can not be truly automatic as the assumption that the recording has started at the session start time does not always hold (sometimes the beginning of the session has been cut)
# For example, the difference between the session start time and the start time of the first speech is sometimes larger than the duration of the audio
# The used timezones vary (sometimes utc, sometimes Europe/Helsinki, it is not marked in the timestamp) (there seems to be a logic?)
# The script tries to infer the used timezones and detect the nonfunctional session start times

# TODO: automatically detect speeches with the wrong language label

def main(argv):
    if len(argv) < 2:
        print('usage: python 01_approximate_locations.py path_to_transcriptions excluded_sessions')
        exit(1)

    if (not os.path.exists('output')):
        os.mkdir('output')

    output_folder = os.path.join('output', '01')

    if not os.path.exists(output_folder):
        os.mkdir(output_folder)    

    print('reading files')
    df_all = get_sessions_as_df(argv[1])

    print('dropping speeches with null timestamps')
    start_len = df_all.shape[0]
    df_all.replace('', np.nan, inplace=True)
    df_all = df_all.dropna(subset=['start_time', 'end_time'])

    if start_len > df_all.shape[0]:
        print('dropped', str(start_len - df_all.shape[0]), 'speeches due to missing timestamps')
    else:
        print('no speeches dropped')

    df_all = fix_session_074_2020(df_all)
    
    df_swe = get_swedish_speeches(df_all)

    if (len(argv) > 2):
        df_swe = exclude_sessions(df_swe, argv[2])

    print('found', df_swe.shape[0], 'speeches')

    print('testing preprocessing')
    abnormal_words = check_for_abnormal_words(df_swe)
    if len(abnormal_words) > 0:
        print(len(abnormal_words), "word(s) can't be preprocessed")
        write_abnormal_words(abnormal_words, output_folder)
        print("you can ignore this or fix manually by editing manual replacements function (it's probably fine to ignore if there aren't too many)")
        cont = input("Continue (y/n): ").lower() == 'y'
        if not cont:
            exit(1)
    else:
        print('no abnormal words found, continuing')

    df_swe['processed_text'] = [preprocess_text(text) for text in df_swe['text']]
    df_swe['name'] = df_swe['firstname'] + df_swe['lastname']

    df_swe['session_begin_time_helsinki'] = get_session_begin_times_as_eu_helsinki(df_swe, 'session_begin_time')
    df_swe['start_time_helsinki'] = get_speech_times_as_eu_helsinki(df_swe, 'start_time')
    df_swe['end_time_helsinki'] = get_speech_times_as_eu_helsinki(df_swe, 'end_time')
    df_all['session_begin_time_helsinki'] = get_session_begin_times_as_eu_helsinki(df_all, 'session_begin_time')
    df_all['start_time_helsinki'] = get_speech_times_as_eu_helsinki(df_all, 'start_time')
    df_all['end_time_helsinki'] = get_speech_times_as_eu_helsinki(df_all, 'end_time')

    times_helsinki = get_first_timestamps_in_each_file(df_swe, df_all)
    times_helsinki['time_between_session_begin_and_first_speech'] = times_helsinki['first_start_time'] - times_helsinki['session_begin_time']

    problem_sessions = find_sessions_first_speech_starts_over_30_minutes_from_start(times_helsinki)

    if len(problem_sessions) > 0 and (not problem_sessions_fixed(problem_sessions) == len(problem_sessions)):
        print(len(problem_sessions) - problem_sessions_fixed(problem_sessions), 'problematic sessions found')
        print('these should be investigated manually')
        print('if the difference to the is around two hours, it is likely that a timestamp was misinterpreted (wrong timezone)')
        write_problem_sessions(problem_sessions, output_folder)
        exit(1)
    
    df_swe = replace_session_begin_time_timestamps(df_swe, session_begin_time_replacements)

    df_swe['approximated_start_pos'] = [time.total_seconds() - 30 for time in (df_swe['start_time_helsinki'] - df_swe['session_begin_time_helsinki'])]
    df_swe['approximated_end_pos'] = [time.total_seconds() + 30 for time in (df_swe['end_time_helsinki'] - df_swe['session_begin_time_helsinki'])]

    #df_swe['start_time_ts'] = [time.timestamp() for time in df_swe['start_time_helsinki']]

    # detect wrong language tags here

    df_swe.to_csv(os.path.join(output_folder, 'parliament_sv-fi_approximated.csv'), index=False)

def get_session_as_df(filepath):
    col_order = ['mp_id', 'firstname', 'lastname', 'party', 'language', 'session_begin_time', 'start_time', 'end_time', 'filename', 'text', 'title', 'type']

    session_name = filepath[filepath.index('session-'):-5]
    with open(filepath, encoding='utf-8') as f:
        session_json = json.load(f)
        session_begin_time = session_json['begin_time']
        subsections = session_json['subsections']
        if len(subsections) == 0: return None
        df = pd.DataFrame.from_dict(subsections[0]['statements'])
        del df['embedded_statement']
        df['filename'] = [session_name for i in range(df.shape[0])]
        df['session_begin_time'] = session_begin_time
        df = df[col_order]
        return df

def get_sessions_as_df(sessions_filepath):
    years = ['2015', '2016', '2017', '2018', '2019', '2020']
    
    trs_json = []
    for year in years:
        for (dirpath, dirnames, filenames) in os.walk(os.path.join(sessions_filepath, year)):
            for filename in filenames:
                if '.json' in filename:
                    trs_json.append(os.path.join(sessions_filepath, year, filename))
    df = pd.concat([get_session_as_df(path) for path in trs_json]).reset_index(drop=True)
    return df

def remove_brackets(text):
    return re.sub(r'\[.*\]', '', text)

def remove_parentheses(text):
    return re.sub(r'\(.*\)', '', text)

def remove_extra_spaces(text):
    return re.sub(r' {2,}', ' ', text)

def manual_replacements(text):
    text = text.replace('74e', 'sjuttiofjärde')
    return text

def write_numbers(text):
    return ' '.join([num2words(word, lang='sv') if word.isnumeric() else word for word in text.split()])

def preprocess_text(text):
    text = text.lower()
    text = remove_brackets(text)
    text = remove_parentheses(text)
    text = re.sub(r'[-—‑/]+', ' ', text)
    text = re.sub(r'["”\':\?\!]', '', text)
    text = re.sub(r'\.\.\.', '', text)
    text = re.sub(r'[\.,](?= |$)', '', text)
    text = re.sub(r'#ch_statement', '', text)
    
    #remove spaces between numbers
    text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)
    
    #decimal numbers
    text = re.sub(r'(?<=[0-9]),(?=[0-9])', ' komma ', text)
    
    #times
    text = re.sub(r'(?<=[0-9]).(?=[0-9])', ' ', text)
    
    text = text.replace('+', ' plus ')
    text = text.replace('§', 'paragraf')
    
    text = manual_replacements(text)
    
    text = remove_extra_spaces(text)
    
    text = write_numbers(text)
    
    text = text.strip()
    return text

def find_abnormal_words(text, abnormal_words):
    text = preprocess_text(text)
    for word in text.split():
        if not word.isalpha() and not word.isnumeric():
            abnormal_words.add(word)

def find_numbers(text, numbers):
    text = preprocess_text(text)
    for word in text.split():
        if len(word) == 0: continue
        if word.isnumeric():
            numbers.append(word)

def get_rows_containing_text(df, language, text):
    indices = []
    for i, row in df.iterrows():
        if not row['language'] == language: continue
        if text in row['text']:
            indices.append(i)
    return df.iloc[indices]

def check_for_abnormal_words(df):
    abnormal_words = set()
    for text in df[df['language'] == 'sv']['text']:
        find_abnormal_words(text, abnormal_words)
    return abnormal_words

def write_abnormal_words(abnormal_words, output_folder):
    output_file = os.path.join(output_folder, 'abnormal_words.txt')
    with open(output_file, 'w') as f:
        for word in abnormal_words:
            f.write(word + '\n')
    print('abnormal words written to {out}'.format(out=output_file))

def get_swedish_speeches(df):
    return df[df['language'] == 'sv'].copy()

def exclude_sessions(df, excluded_sessions):
    # FIX THIS
    return df

def get_first_timestamps_in_each_file(df1, df2):
    filenames = []
    session_begin_times = []
    first_start_times = []
    first_end_times = []
    for filename in df1['filename'].unique():
        for i, row in df2[df2['filename'] == filename].iterrows():
            if row['filename'] == filename and (not pd.isnull(row['start_time_helsinki'])) and (not pd.isnull(row['end_time_helsinki'])):
                filenames.append(filename)
                session_begin_times.append(row['session_begin_time_helsinki'])
                first_start_times.append(row['start_time_helsinki'])
                first_end_times.append(row['end_time_helsinki'])
                break
    return pd.DataFrame(data=np.stack([filenames, session_begin_times, first_start_times, first_end_times]).T, columns=['filename', 'session_begin_time', 'first_start_time', 'first_end_time'])

files_with_utc_times = [
    'session-005-2020',
    'session-006-2018',
    'session-009-2020',
    'session-016-2019',
    'session-018-2018',
    'session-018-2019',
    'session-021-2020',
    'session-027-2020',
    'session-033-2020',
    'session-036-2018',
    'session-040-2018',
    'session-040-2020',
    'session-041-2020',
    'session-043-2020',
    'session-047-2019',
    'session-057-2020',
    'session-064-2020',
    'session-065-2018',
    'session-072-2020',
    'session-076-2020',
    'session-083-2019',
    'session-085-2018',
    'session-087-2018',
    'session-093-2018',
    'session-101-2018',
    'session-105-2018',
    'session-109-2018',
    'session-113-2018',
    'session-117-2018',
    'session-125-2018',
    'session-131-2018',
    'session-146-2018',
    'session-178-2018',
    
    'session-078-2020',
    'session-083-2020',
    'session-084-2020',
    'session-097-2020',
    'session-100-2020',
    'session-103-2020',
    'session-079-2020',
    'session-080-2020',
    'session-108-2020',
    'session-109-2020',
    'session-112-2020',
    'session-113-2020',
    'session-120-2020',
    'session-126-2020',
    'session-128-2020',
    'session-133-2020',
    'session-134-2020',
    'session-138-2020',
    'session-142-2020',
    'session-146-2020',
    'session-155-2020',

]

def time_as_helsinki_time(time, pattern):
    tz_helsinki = pytz.timezone("Europe/Helsinki")
    session_time = datetime.strptime(time, pattern)
    session_time = tz_helsinki.localize(session_time, is_dst=None)
    return session_time

def utc_time_to_helsinki_time(time, pattern):
    dt = datetime.strptime(time, pattern)
    dt = pytz.timezone('UTC').localize(dt)
    return dt.astimezone(pytz.timezone("Europe/Helsinki"))

time1 = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-5][0-9]:[0-5][0-9]')
time1decimal = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-5][0-9]:[0-5][0-9]\.[0-9]*')
time2 = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-5][0-9]:[0-5][0-9]')

#time1 are times like 2017-02-07 14:04:05.137 (utc time)
#time2 are times like 2019-05-07T14:00:00

def get_session_begin_times_as_eu_helsinki(df, col):
    session_begin_times = []
    for i, row in df.iterrows():
        pattern = None
        time = row[col]
        if re.match(time2, time):
            pattern = '%Y-%m-%dT%H:%M:%S'
        elif re.match(time1decimal, time):
            pattern = '%Y-%m-%d %H:%M:%S.%f'
        elif re.match(time1, time):
            pattern = '%Y-%m-%d %H:%M:%S'
        if pattern == None:
            session_begin_times.append(None)
        elif row['filename'] in files_with_utc_times:
            session_begin_times.append(utc_time_to_helsinki_time(time, pattern))
        else:
            session_begin_times.append(time_as_helsinki_time(time, pattern))
    return session_begin_times

def get_speech_times_as_eu_helsinki(df, col):
    speech_begin_times = []
    for i, row in df.iterrows():
        pattern = None
        time = row[col]
        if re.match(time2, time):
            pattern = '%Y-%m-%dT%H:%M:%S'
        elif re.match(time1decimal, time):
            #raise Exception('Unexpected time format')
            pattern = '%Y-%m-%d %H:%M:%S.%f'
        elif re.match(time1, time):
            #raise Exception('Unexpected time format')
            pattern = '%Y-%m-%d %H:%M:%S'
        if pattern == None and len(time) == 0:
            speech_begin_times.append(None)
        elif pattern == None:
            raise Exception('Unexpected time format')
        else:
            speech_begin_times.append(time_as_helsinki_time(time, pattern))
    return speech_begin_times

def find_sessions_first_speech_starts_over_30_minutes_from_start(times_helsinki):
    problem_sessions = []
    for i, row in times_helsinki.iterrows():
        if row['time_between_session_begin_and_first_speech'].total_seconds() > (3600 / 2):
            problem_sessions.append({
                'name': row['filename'],
                'hours_to_first_speech': (round(row['time_between_session_begin_and_first_speech'].total_seconds() / 3600, 2))
            })
    return problem_sessions

# session-074-2020 speeches in the beginning of have been cut from the audio
# 
# dfg

def fix_session_074_2020(df):
    
    # delete them from the transcriptions
    
    speeches_to_remove = [
        '2020-05-19T17:16:41',
        '2020-05-19T17:18:48',
        '2020-05-19T17:20:01',
        '2020-05-19T17:21:03',
        '2020-05-19T17:21:18',
        '2020-05-19T17:23:06',
        '2020-05-19T17:24:35',
        '2020-05-19T17:26:16'
    ]

    delete_locs = []
    for i in df.index:
        if not df.loc[i]['filename'] == 'session-074-2020': continue
        if df.loc[i].start_time in speeches_to_remove:
            delete_locs.append(i)

    if len(delete_locs) > 0:
        return df.drop(delete_locs, axis=0)
    return df

def write_problem_sessions(problem_sessions, output_folder):
    output_file = os.path.join(output_folder, 'problem_sessions.txt')
    with open(output_file, 'w') as f:
        for session in problem_sessions:
            if session['name'] in session_begin_time_replacements: continue
            f.write(session['name'] + ';' + str(session['hours_to_first_speech']) + '\n')
    print('problem sessions written to {out}, format: session_name;hours_until_first_speech'.format(out=output_file))

# session-074-2020 has speeches cut from the beginning 

session_begin_time_replacements = {
    'session-132-2016': time_as_helsinki_time('2016-12-13T14:53:21', '%Y-%m-%dT%H:%M:%S') - timedelta(seconds=3660),
    'session-067-2020': time_as_helsinki_time('2020-05-06T16:05:35', '%Y-%m-%dT%H:%M:%S') - timedelta(seconds=8435),
    'session-074-2020': time_as_helsinki_time('2020-05-19T14:01:14', '%Y-%m-%dT%H:%M:%S') - timedelta(seconds=975)
}

def problem_sessions_fixed(problem_sessions):
    fixed = 0
    for session in problem_sessions:
        if session['name'] in session_begin_time_replacements.keys():
            fixed += 1
    return fixed

def replace_session_begin_time_timestamps(df, replacements):
    df = df.copy()
    for index in df.index:
        if df.loc[index, 'filename'] in replacements.keys():
            df.loc[index, 'session_begin_time_helsinki'] = replacements[df.loc[index, 'filename']]
    return df

if __name__ == "__main__":
    main(sys.argv)
