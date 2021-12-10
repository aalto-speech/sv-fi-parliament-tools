import os
import sys

def main():
    if len(sys.argv) != 2:
        print('usage: python3 create_vocab.py data_folder')
        print('e.g.:  python3 create_vocab.py data/comb_stde_train')
        exit(1)
    
    data_folder = sys.argv[1]

    words = set()

    with open(os.path.join(data_folder, 'text')) as f:
        for line in f.readlines():
            for word in line.strip().split()[1:]:
                words.add(word)

    words = sorted(list(words))

    with open(os.path.join(data_folder, 'vocab'), 'w') as f:
        for word in words:
            f.write(word + '\n')

if __name__ == "__main__":
    main()