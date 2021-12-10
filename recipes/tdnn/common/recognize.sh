#!/bin/bash
export LC_ALL=C

# Begin configuration section.
skip_scoring=false
beam=18
iter=final
extra_flags=""
ivector_extractor=

# End configuration options.

echo "$0 $@"  # Print the command line for logging

. utils/parse_options.sh || return;

if [ $# -ne 5 ]; then
   echo "usage: local/recognize.sh acoustic_model graph lexicon data_folder experiment_name"
   echo "e.g.:  local/recognize.sh exp/chain/model/comb_stde_tdnn_9_a models/word_400k generated/data/memad memad"
   echo "main options (for others, see top of script file)"

   return;
fi
. ./path.sh
. ./cmd.sh ## You'll want to change cmd.sh to something that will work on your system.
           ## This relates to the queue.

am=$1
graph=$2
lex=$3
data_folder=$4
experiment_name=$5
nj=1

#graph_name=graph_$(basename $lex)

if [ ! -f $am/$graph_name ]; then
  echo "graph missing, generating with given lexicon..."
  ret=$(sbatch -t 01:00:00 --mem-per-cpu 1G utils/mkgraph.sh --self-loop-scale 1.0 $lex $am $am/$graph_name)
  exit
fi
exit

ivector_out=generated/ivecs/$experiment_name/

# Should have wav.scp at this point
utils/utt2spk_to_spk2utt.pl $data_folder/utt2spk > $data_folder/spk2utt 

# Adjust acoustic scale
decode_flags="--post-decode-acwt 10.0 --acwt 1.0"
if [ -f $am/decode_flags ]; then
	decode_flags="${decode_flags} $(cat $am/decode_flags)"
fi

if [ ! -f generated/feats/$experiment_name/feats.scp ]; then
  mkdir -p generated/feats/$experiment_name
  local/prepare_dataset.sh $data_folder generated/feats/$experiment_name 
fi

#ivector_cmd missing
if [ ! -f  ${ivector_out}/ivector_online.1.scp ]; then
	mkdir -p ${ivector_out}
  steps/online/nnet2/extract_ivectors.sh --nj 1 generated/feats/$experiment_name \
	 	${lex} ${ivector_extractor} ${ivector_out} || exit 1;
fi

#--cmd "${decode_cmd}"
if [ ! -f generated/decoding_results/$experiment_name/wer_15_0.0 ]; then 
  steps/nnet3/decode.sh $extra_flags --cmd "run.pl" --iter $iter --beam $beam --lattice-beam 10.0 --skip-scoring $skip_scoring --nj $nj $decode_flags --scoring-opts "--min-lmwt 4 --max-lmwt 19" --online-ivector-dir "${ivector_out}" ${lm} generated/feats/$experiment_name ${am}/decode_$experiment_name
fi

./steps/get_ctm.sh --cmd ${train_cmd} generated/feats/$experiment_name ${lm} ${am}/decode_$experiment_name
