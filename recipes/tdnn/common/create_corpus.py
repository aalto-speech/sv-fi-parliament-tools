import os
import sys

def main():
    if len(sys.argv) != 2:
        print('usage: python3 create_corpus.py data_folder')
        print('e.g.:  python3 create_corpus.py data/comb_stde_train')
        exit(1)
    
    data_folder = sys.argv[1]

    utts = []

    with open(os.path.join(data_folder, 'text')) as f:
        for line in f.readlines():
            words = [word for word in line.strip().split()[1:] if not word == '<UNK>']
            words.insert(0, '<s>')
            words.append('</s>')
            utts.append(' '.join(words))

    with open(os.path.join(data_folder, 'corpus'), 'w') as f:
        for utt in utts:
            f.write(utt + '\n')

if __name__ == "__main__":
    main()