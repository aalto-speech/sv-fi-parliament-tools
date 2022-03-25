#!/bin/bash
#SBATCH --time=24:00:00
#SBATCH --mem-per-cpu=4G
#SBATCH --output=logs/06/kaldi_clean.%j.out

set -eu

mkdir -p tmp2
mkdir -p output
mkdir -p output/06

# Path to acoustic model folder
am=$1
# Path to language model folder
lm=$2
# Path to i-vector extractor
extractor=$3
# Path to segmented data
data=output/05

./local/clean_and_segment_data_nnet3.sh --extractor $extractor $data $lm $am tmp2 output/06

utils/fix_data_dir.sh output/06
utils/validate_data_dir.sh output/06