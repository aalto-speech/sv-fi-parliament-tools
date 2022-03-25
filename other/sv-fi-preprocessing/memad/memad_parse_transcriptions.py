#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import os
import sys
from memad_parsing import get_tokens, get_utts

transcriptions = [
    'MEDIA_2014_00778322.transcription',
    'MEDIA_2016_01097470.transcription',
    'MEDIA_2016_01103644.transcription',
    'MEDIA_2016_01171950.transcription',
    'MEDIA_2017_01238080.transcription',
    'MEDIA_2017_01245348.transcription',
    'MEDIA_2017_01261730.transcription',
    'MEDIA_2017_01317720.transcription',
    'MEDIA_2017_01351191.transcription',
]

def repair_data(token_list):
    #Manually repair data that doesn't adhere to the format'

    assert token_list['MEDIA_2014_00778322.transcription'][165].str == '[<puhuja_MarkoKulpakko]'
    assert token_list['MEDIA_2014_00778322.transcription'][201].str == '[<puhuja-MiapetraKumpulaNatri>]'
    assert token_list['MEDIA_2014_00778322.transcription'][753].str == '[0:41:13.9>]'
    assert token_list['MEDIA_2014_00778322.transcription'][829].str == '[puhuja_NilsTorvalds>]'
    assert token_list['MEDIA_2014_00778322.transcription'][933].str == '[<0:52:25.3 >]'
    assert token_list['MEDIA_2014_00778322.transcription'][1107].str == '[puhuja_IngemoLindroos>]'

    token_list['MEDIA_2014_00778322.transcription'][165].str = '[<puhuja_MarkoKulpakko>]'
    token_list['MEDIA_2014_00778322.transcription'][201].str = '[<puhuja_MiapetraKumpulaNatri>]'
    token_list['MEDIA_2014_00778322.transcription'][753].str = '[<0:41:13.9>]'
    token_list['MEDIA_2014_00778322.transcription'][829].str = '[<puhuja_NilsTorvalds>]'
    token_list['MEDIA_2014_00778322.transcription'][933].str = '[<0:52:25.3>]'
    token_list['MEDIA_2014_00778322.transcription'][1107].str = '[<puhuja_IngemoLindroos>]'

    assert token_list['MEDIA_2017_01351191.transcription'][300].str == '[<11:39.5>]'
    token_list['MEDIA_2017_01351191.transcription'][300].str = '[<0:11:39.5>]'

def main():
    if len(sys.argv) != 3:
        print('usage: python3 memad_parse_transcriptions.py data_folder out_folder')
        print('e.g.:  python3 memad_parse_transcriptions.py memad/yle-sv-fi-test-data generated/data/memad')
        exit(1)

    data_folder = sys.argv[1]
    out_folder = sys.argv[2]

    tokens = get_tokens(data_folder, transcriptions)
    repair_data(tokens)
    utts = get_utts(tokens, transcriptions)

    transcription_dfs = [pd.DataFrame.from_records([utt.to_dict() for utt in utts[name]]) for name in transcriptions]
    for i in range(len(transcription_dfs)):
        transcription_dfs[i] = transcription_dfs[i][['id', 'speaker', 'start_pos', 'end_pos', 'filename', 'text']]
    df_cat = pd.concat(transcription_dfs)
    out_filepath = os.path.join(out_folder, 'memad_sv_fi_transcriptions.csv')
    df_cat.to_csv(out_filepath, index=False)
    print('Wrote transcriptions to file ', out_filepath)


if __name__ == "__main__":
    main()