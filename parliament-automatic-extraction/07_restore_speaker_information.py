import sys
import os
from distutils.dir_util import copy_tree

# The kaldi extraction scripts removes speaker information in the dataset by changing the speaker tags
# This script restores the original speaker tags

def main(argv):

    if (not os.path.exists('output')):
        os.mkdir('output')

    output_folder = os.path.join('output', '07')

    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    copy_tree('output/06', "output/07")
    os.remove('output/07/spk2utt')
    os.remove('output/07/utt2spk')

    new_rows = []
    with open(os.path.join('output', '06', 'utt2spk')) as f:
        for line in f.readlines():
            line_p = line.strip().split()
            utt_id = line_p[0]
            spk_id = line_p[1]
            spk_id = spk_id[0:5]
            new_rows.append('{uid} {sid}\n'.format(uid=utt_id, sid=spk_id))
    
    with open(os.path.join('output', '07', 'utt2spk'), 'w') as f:
        for line in new_rows:
            f.write(line)


if __name__ == "__main__":
    main(sys.argv)