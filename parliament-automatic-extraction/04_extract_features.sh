#!/bin/bash
#SBATCH --time=08:00:00
#SBATCH --mem-per-cpu=2G
#SBATCH --cpus-per-task=10
#SBATCH --output=logs/04/extract_features.%j.out

# scripts 04 - 06 use kaldi and require that symbolic links to utils and steps are in the current location

set -eu

mkdir -p output
mkdir -p output/04

. path.sh

mfcc_config=conf/mfcc_hires.conf
log_mfcc=logs/04/mfcc
log_cmvn=logs/04/cmvn

dataset=output/02
out_folder=output/04

echo "copying data folder"

cp -a $dataset/. $out_folder/

echo "fix data folder"

utils/fix_data_dir.sh $out_folder

#echo "creating spk2utt"

#./utils/utt2spk_to_spk2utt.pl $out_folder

echo "extract mfcc features"

steps/make_mfcc.sh --mfcc-config $mfcc_config --nj 10 $out_folder $log_mfcc

echo "compute cmvn statistics"

steps/compute_cmvn_stats.sh $out_folder $log_cmvn

echo "fix data directory and validate"

utils/fix_data_dir.sh $out_folder
utils/validate_data_dir.sh --no-text $out_folder