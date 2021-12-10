#!/bin/bash
#SBATCH --time=6:00:00
#SBATCH --mem-per-cpu=2G
#SBATCH --cpus-per-task=5
#SBATCH --output=logs/decode_gmm.%j.out

export LC_ALL=C
set -eu

echo "$0 $@"  # Print the command line for logging

. utils/parse_options.sh || return;

# Data folder should have hires MFCCs, model should have graph

if [ $# -ne 3 ]; then
   echo "usage: run_scripts/decode_gmm.sh acoustic_model recog_lang data"
   echo "e.g.:  run_scripts/decode_gmm.sh exp/comb_stde2_tri3 models/word_400k data/2015-2020kevat_sv-fi_dev"
   exit 1;
fi

echo "$0 $@"  # Print the command line for logging

. ./path.sh

am=$1
recog_lang=$2
data=$3

am_name=${am##*/}
recog_lang_name=${recog_lang##*/}
data_name=${data##*/}
graph=$am/graph_$recog_lang_name

if [ ! -f $graph ]; then
  utils/mkgraph.sh $recog_lang $am $am/graph_$recog_lang_name
fi

if [[ ! -f $am/decode_${data_name}_${recog_lang_name}/scoring_kaldi/best_wer || "$force" == true ]]; then
  steps/decode_fmllr.sh --cmd "run.pl" --nj 5 $graph $data $am/decode_${data_name}_${recog_lang_name}
fi

if [[ ! -f $am/decode_${data_name}_${recog_lang_name}_rs/scoring_kaldi/best_wer || "$force" == true ]]; then
  steps/lmrescore_const_arpa.sh --scoring-opts "--min-lmwt 1 --max-lmwt 30" $recog_lang ${recog_lang}_big $data $am/decode_${data_name}_${recog_lang_name} $am/decode_${data_name}_${recog_lang_name}_rs
fi

