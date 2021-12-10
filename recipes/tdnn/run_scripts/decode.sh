#!/bin/bash
#SBATCH --time=6:00:00
#SBATCH --mem-per-cpu=1G
#SBATCH --cpus-per-task=10
#SBATCH --output=logs/decode.%j.out

export LC_ALL=C
set -eu

# Begin configuration section.
skip_scoring=false
beam=18
iter=final
extra_flags=""
ivector_extractor=
graph=
force=false
nj=10
#decode_cmd="run.pl"

# End configuration options.

echo "$0 $@"  # Print the command line for logging

. utils/parse_options.sh || return;

# Data folder should have hires MFCCs, model should have graph

if [ $# -ne 3 ]; then
   echo "usage: run_scripts/decode.sh acoustic_model recog_lang data"
   echo "e.g.:  run_scripts/decode.sh exp/chain/model/comb_stde_tdnn_9_a models/word_400k data/memad_hires"
   echo "main options (for others, see top of script file)"
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

if [ -z "$ivector_extractor" ]; then
  echo "Using ivector extractor in default location"
  ivector_extractor=$am/ivecs/extractor
fi

if [ -z "$graph" ]; then
  echo "Using graph in default location"
  graph=$am/graph_$recog_lang_name
fi

ivector_out=generated/ivecs/${data_name}_${am_name}_${recog_lang_name}

# Adjust acoustic scale
decode_flags="--post-decode-acwt 10.0 --acwt 1.0"
if [ -f $am/decode_flags ]; then
	decode_flags="${decode_flags} $(cat $am/decode_flags)"
fi

if [ ! -f  $ivector_out/ivector_online.1.scp ]; then
	mkdir -p $ivector_out
  steps/online/nnet2/extract_ivectors.sh --nj 1 $data $recog_lang $ivector_extractor $ivector_out || exit 1;
fi

if [[ ! -f $am/decode_${data_name}_${recog_lang_name}/scoring_kaldi/best_wer || "$force" == true ]]; then
  steps/nnet3/decode.sh $extra_flags --cmd "run.pl" --iter $iter --beam $beam --lattice-beam 10.0 --skip-scoring $skip_scoring --nj $nj $decode_flags --scoring-opts "--min-lmwt 4 --max-lmwt 19" --online-ivector-dir $ivector_out $graph $data $am/decode_${data_name}_${recog_lang_name}
fi

if [[ ! -f $am/decode_${data_name}_${recog_lang_name}_rs/scoring_kaldi/best_wer || "$force" == true ]]; then
  steps/lmrescore_const_arpa.sh --scoring-opts "--min-lmwt 1 --max-lmwt 30" $recog_lang ${recog_lang}_big $data $am/decode_${data_name}_${recog_lang_name} $am/decode_${data_name}_${recog_lang_name}_rs
fi