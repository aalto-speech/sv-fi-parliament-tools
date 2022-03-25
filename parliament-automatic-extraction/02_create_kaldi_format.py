import pandas as pd
import os
import sys

# <mpid> = id of the mp, padded to 5 digits
# <recordid> = ID of the session, (number-year)
# <uttid> = (<mpid>-<recordid>-<start>-<end>) (start and end are formed by taking the position with two decimals and padding to length 8)

# segments format should be:
# <uttid> <recordid> start end (start and end are the untouched positions, directly converted to a string)
# 00118-081-2020-00142405-00142652 081-2020 1424.05 1426.52 (example row)

# utt2spk format should be:
# <uttid> <mpid>

# text format should be:
# <uttid> (line transcription)

# wav.scp format should be:
# <recordid> (filepath or position in archive)

def form_speaker_ids(df):
    speaker_ids = []
    for _, row in df.iterrows():
        speaker_id = str(int(row['mp_id'])).zfill(5)
        speaker_ids.append(speaker_id)
    return speaker_ids

def get_time_for_utt_id(time_as_seconds_str):
    return "{:.2f}".format(time_as_seconds_str).replace('.', '').zfill(8)

def create_utt_ids(df):
    utt_ids = []
    for _, row in df.iterrows():
        utt_id = '{mp_id}-{record_id}-{start}-{end}'.format(
            mp_id=row['speaker_id'],
            record_id=get_recording_id(row['filename']),
            start=get_time_for_utt_id(row['approximated_start_pos']),
            end=get_time_for_utt_id(row['approximated_end_pos'])
            )
        utt_ids.append(utt_id)
    return utt_ids

def get_recording_id(filename):
    return filename[filename.index('-') + 1:]

def get_session_year(session):
    return session[12:16]

def get_extended_filename(filename, data_folder):
    session_year = get_session_year(filename)
    return os.path.join(data_folder, session_year, filename + '.wav')

def write_wav_scp(df, data_folder, out_folder):
    with open(os.path.join(out_folder, 'wav.scp'), 'w') as f:
        for filename in sorted(df['filename'].unique()):
            recording_id = filename
            extended_filename = get_extended_filename(recording_id, data_folder)
            f.write(get_recording_id(filename) + ' ' + extended_filename + '\n')

def write_text(df, out_folder):
    with open(os.path.join(out_folder, 'text'), 'w') as f:
        for _, row in df.iterrows():
            f.write(row['utterance_id'] + ' ' + row['processed_text'] + '\n')

def float_to_str(f):
    return str(f)

def write_segments(df, out_folder):
    with open(os.path.join(out_folder, 'segments'), 'w') as f:
        for _, row in df.iterrows():
            recording_id = get_recording_id(row['filename'])
            start_pos_str = float_to_str(row['approximated_start_pos'])
            end_pos_str = float_to_str(row['approximated_end_pos'])
            f.write(' '.join([row['utterance_id'], recording_id, start_pos_str, end_pos_str]) + '\n')

def write_utt2spk(df, out_folder):
    with open(os.path.join(out_folder, 'utt2spk'), 'w') as f:
        for _, row in df.iterrows():
            f.write(row['utterance_id'] + ' ' + row['speaker_id'] + '\n')

def check_that_files_exist(df, data_folder):
    all_found = True
    for filename in df['filename'].unique():

        path = os.path.join(data_folder, get_session_year(filename), filename + '.wav')

        if not os.path.isfile(path):
            print('MISSING FILE: ', path)
            all_found = False
    return all_found

def write_reco2file_and_channel(df, data_folder, out_folder):
    with open(os.path.join(out_folder, 'reco2file_and_channel'), 'w') as f:
        for filename in sorted(df['filename'].unique()):
            recording_id = filename
            extended_filename = get_extended_filename(recording_id, data_folder)
            f.write(get_recording_id(filename) + ' ' + extended_filename +  ' A' + '\n')

def main():
    if len(sys.argv) != 2:
        print('usage: python 02_create_kaldi_format.py data_folder')
        #print('e.g.:  python 02_create_kaldi_format.py ')
        exit(1)
    data_folder = sys.argv[1]
    
    if (not os.path.exists('output')):
        os.mkdir('output')
    out_folder = os.path.join('output', '02')
    if not os.path.exists(out_folder):
        os.mkdir(out_folder)

    df = pd.read_csv(os.path.join('output', '01', 'parliament_sv-fi_approximated.csv'))
    # missing files 30.3.2021
    missing_files = ['session-013-2018', 'session-072-2020', 'session-074-2020', 'session-076-2020', 'session-129-2017']
    # drop speeches in missing files
    df = df[~df['filename'].isin(missing_files)]

    if not check_that_files_exist(df, data_folder): return

    print('Total speeches: ', df.shape[0])

    df['speaker_id'] = form_speaker_ids(df)
    df['utterance_id'] = create_utt_ids(df)
    #df = df.sort_values(by=['utterance_id'])
    print('Creating text')
    write_text(df, out_folder)
    print('Creating segments')
    write_segments(df, out_folder)
    print('Creating utt2spk')
    write_utt2spk(df, out_folder)
    print('Creating wav.scp')
    write_wav_scp(df, data_folder, out_folder)
    print('Creating reco2file_and_channel')
    write_reco2file_and_channel(df, data_folder, out_folder)

if __name__ == "__main__":
    main()