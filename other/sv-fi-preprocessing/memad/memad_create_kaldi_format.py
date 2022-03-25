import pandas as pd
import os
import sys

def remove_special_characters(name):
    name = name.replace('ä', 'a')
    name = name.replace('ö', 'o')
    name = name.replace('å', 'a')
    name = name.replace('é', 'e')
    return name

def remove_prefix(speaker):
    return speaker[speaker.index('_') + 1:]

def create_speaker_id(speaker):
    speaker_id = remove_prefix(speaker)
    
    speaker_id = speaker_id.replace('_', '')
    speaker_id = speaker_id.replace('-', '')
    speaker_id = speaker_id.lower()
    speaker_id = remove_special_characters(speaker_id)
    
    return speaker_id

def is_unknown_speaker(speaker):
    return speaker.isnumeric() or 'ihminen' in speaker

def make_ids_for_unknown_speakers(df):
    unknown_speakers = {}
    unknown_i = 0
    for _, filename in enumerate(df['filename'].unique()):
        unknown_speakers[filename] = {}
        for speaker in df[df['filename'] == filename]['speaker'].unique():
            if is_unknown_speaker(remove_prefix(speaker)):
                unknown_speakers[filename][speaker] = 'speaker' + str(unknown_i)
                unknown_i += 1
    return unknown_speakers

def form_speaker_ids(df, unknown_speakers):
    speaker_ids = []
    for _, row in df.iterrows():
        filename = row['filename']
        speaker = row['speaker']
        
        if speaker in unknown_speakers[filename]:
            speaker_ids.append(unknown_speakers[filename][speaker])
        else:
            speaker_ids.append(create_speaker_id(speaker))
    return speaker_ids

def create_utt_ids(df):
    utt_ids = []
    for _, row in df.iterrows():
        utt_ids.append(row['speaker_id'] + '-' + str(row['id']).zfill(4))
    return utt_ids

def get_timestamp_as_seconds(time):
    times = time.split(':')
    hours = int(times[0])
    minutes = int(times[1])
    seconds = float(times[2])
    return 3600 * hours + 60 * minutes + seconds

def get_recording_id(row):
    return row['filename']

def get_extended_filename(filename, out_folder):
    return os.path.join(out_folder, filename + '.wav')

def write_wav_scp(df, out_folder):
    with open(os.path.join(out_folder, 'wav.scp'), 'w') as f:
        for filename in sorted(df['filename'].unique()):
            recording_id = filename
            extended_filename = get_extended_filename(recording_id, out_folder)
            f.write(recording_id + ' ' + extended_filename + '\n')

def write_text(df, out_folder):
    with open(os.path.join(out_folder, 'text'), 'w') as f:
        for _, row in df.iterrows():
            f.write(row['utterance_id'] + ' ' + row['processed_text'] + '\n')

def write_segments(df, out_folder):
    with open(os.path.join(out_folder, 'segments'), 'w') as f:
        for _, row in df.iterrows():
            recording_id = get_recording_id(row)
            start_pos_str = str(get_timestamp_as_seconds(row['start_pos']))
            end_pos_str = str(get_timestamp_as_seconds(row['end_pos']))
            f.write(' '.join([row['utterance_id'], recording_id, start_pos_str, end_pos_str]) + '\n')

def write_utt2spk(df, out_folder):
    with open(os.path.join(out_folder, 'utt2spk'), 'w') as f:
        for _, row in df.iterrows():
            f.write(row['utterance_id'] + ' ' + row['speaker_id'] + '\n')

def main():
    if len(sys.argv) != 2:
        print('usage: python3 memad_create_kaldi_format.py data_folder')
        print('e.g.:  python3 memad_create_kaldi_format.py generated/data/memad')
        exit(1)
    data_folder = sys.argv[1]
    df = pd.read_csv(os.path.join(data_folder, 'memad_sv_fi_transcriptions_processed.csv'))

    # delete utterances of length 0
    df = df[df['start_pos'] != df['end_pos']]

    df['speaker_id'] = form_speaker_ids(df, make_ids_for_unknown_speakers(df))
    df['utterance_id'] = create_utt_ids(df)
    df = df.sort_values(by=['utterance_id'])
    write_text(df, data_folder)
    write_segments(df, data_folder)
    write_utt2spk(df, data_folder)
    write_wav_scp(df, data_folder)

if __name__ == "__main__":
    main()