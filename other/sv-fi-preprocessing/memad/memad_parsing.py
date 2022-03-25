import string
import re
import os

time_pattern = re.compile(r'\[<[0-9]?[0-9]?:[0-5][0-9]:[0-5][0-9]\.[0-9]>\]')
speaker_pattern = re.compile(r'\[<puhuja_.*>\]')

class Token():
    def __init__(self, string, line):
        self.str = string
        self.line = line

class Utterance:
    def __init__(self, speaker, text, start_pos, end_pos, utt_id, filename):
        self.speaker = speaker
        self.text = text
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.id = utt_id
        self.filename = filename
        
    def to_dict(self):
        return {
            'speaker': self.speaker,
            'text': self.text,
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'id': self.id,
            'filename': self.filename
        }

def split_line(line):
    parts = []
    i = 0
    while i < len(line):
        c = line[i]
        if c in string.whitespace or c == '\n':
            i += 1
            continue
        elif c == '[':
            c_i = line[i:].index(']')
            parts.append(line[i:i + c_i + 1])
            i = i + c_i + 1
        else:
            c_i = line[i:].index('[')
            parts.append(line[i:i + c_i].strip())
            i = i + c_i
    return parts

def parse_transcription(data_folder, transcription_name, tokens):
    with open(os.path.join(data_folder, transcription_name + '.txt'), 'r', encoding='utf-8') as f:
        line_number = 0
        while True:
            line = f.readline()
            if not line:
                break
            for token in split_line(line):
                tokens[transcription_name].append(Token(token, line_number))
            line_number += 1

def get_tokens(data_folder, transcriptions):
    tokens = {}
    for name in transcriptions:
        tokens[name] = []
    for name in transcriptions:
        parse_transcription(data_folder, name, tokens)
    return tokens

def get_utts(tokens, transcriptions):
    utts = {}
    utt_id = 0
    for name in transcriptions:
        transcription_utts = gather_utts(tokens, name, utt_id)
        utt_id += len(transcription_utts)
        utts[name] = transcription_utts
    return utts

def is_time_token(string):
    return re.search(time_pattern, string)

def is_speaker_token(string):
    return re.search(speaker_pattern, string) and not 'nonspeech' in string
    
def is_special_token(string):
    return 'nonspeech' in string or 'päällekkäistä' in string or 'epäselvää' in string

def get_text(string):
    if not string[0] == '[': return string
    return string[2:-2]

def gather_utts(tokens, transcription, utt_id_start = 0):
    utts = []
    last_time = None
    last_utt = None
    last_speaker = None
    utterance_id = utt_id_start
    for token in tokens[transcription]:
        if is_special_token(token.str): continue
        if is_time_token(token.str):
            new_time = token
            if last_time != None and last_utt != None:
                if last_utt.line != last_speaker.line and last_speaker.line != new_time.line:
                    raise Exception('Speaker, utterance and end time should be from the same line in the original file',)
                utts.append(Utterance(get_text(last_speaker.str), last_utt.str, get_text(last_time.str), get_text(new_time.str), utterance_id, transcription.split('.')[0]))
                last_utt = None
                utterance_id += 1
            last_time = new_time
        elif is_speaker_token(token.str):
            last_speaker = token
        else:
            if '[' in token.str:
                raise Exception('Found token in erroneous format: ', token.str)
            last_utt = token
    return utts

def search_for_errors(tokens, transcriptions):
    for name in transcriptions:
        print('Errors found in: ', name)
        for i, token in enumerate(tokens[name]):
            if is_special_token(token.str): continue
            if not is_time_token(token.str) and not is_speaker_token(token.str):
                if '[' in token.str or ']' in token.str:
                    print(token.str, i)
        print()
