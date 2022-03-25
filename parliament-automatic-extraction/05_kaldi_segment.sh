#!/bin/bash
#SBATCH --time=12:00:00
#SBATCH --mem-per-cpu=4G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/05/kaldi_segment.%j.out

set -eu

mkdir -p tmp
mkdir -p output
mkdir -p output/05

# Path to acoustic model folder
am=$1
# Path to language model folder
lm=$2
# Path to i-vector extractor
extractor=$3
# Path to generated features (MFCC, cmvn)
data=output/04

./local/segment_and_decode_nnet3.sh --extractor $extractor --nj 1 $am $lm $data output/05 tmp

utils/fix_data_dir.sh output/05
utils/validate_data_dir.sh output/05

