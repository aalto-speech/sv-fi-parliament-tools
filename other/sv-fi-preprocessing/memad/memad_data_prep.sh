#!/bin/bash
# modules needed: ffmpeg, anaconda3

set -euo pipefail

echo "$0 $@"  # Print the command line for logging

. utils/parse_options.sh || return;

if [ $# -ne 2 ]; then
   echo "usage: local/memad_data_prep.sh data_folder data_out"
   echo "e.g.:  local/memad_data_prep.sh memad/yle-sv-fi-test/data generated/data/memad"

   return;
fi

data_folder=$1
out_folder=$2

sv_fi_memad_files=( 
    "MEDIA_2014_00778322" 
    "MEDIA_2016_01097470" 
    "MEDIA_2016_01103644" 
    "MEDIA_2016_01171950" 
    "MEDIA_2017_01238080" 
    "MEDIA_2017_01245348" 
    "MEDIA_2017_01261730" 
    "MEDIA_2017_01317720" 
    "MEDIA_2017_01351191"
)

# Rip audio from videos
mkdir -p generated/data/memad

for file in ${sv_fi_memad_files[@]}
do
    ffmpeg -i $data_folder/$file.mp4 -map 0:a:0 -ac 1 -ar 16000 $out_folder/$file.wav
done

# Parse transcriptions

python3 local/memad_parse_transcriptions.py $data_folder $out_folder

# Process text
# python modules needed: num2words

python3 local/memad_process_text.py $out_folder

# create wav.scp, utt2spk, text, segments

python3 local/memad_create_kaldi_format.py $out_folder

