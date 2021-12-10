#!/bin/bash
#SBATCH --time=2:00:00
#SBATCH --mem-per-cpu=1G
#SBATCH --output=logs/train_chain_prep.%j.out

echo "$0 $@"  # Print the command line for logging
export LC_ALL=C

set -euo pipefail
IFS=$'\n\t'

dataprep=

tree_numleaves=4000
leftmost_questions_truncate=-1

chunk_width=150
chunk_left_context=0
chunk_right_context=0
model_left_context=1
model_right_context=1
frames_overlap_per_eg=0
frames_per_iter=1500000
chain_lm_opts="--num-extra-lm-states=2000"

[ -f path.sh ] && . ./path.sh # source the path.
. parse_options.sh || exit 1;

if [ $# != 2 ]; then
   echo "usage: train_chain_prep.sh config_name stage"
   exit 1;
fi

. ./cmd.sh ## You'll want to change cmd.sh to something that will work on your system.
           ## This relates to the queue.

config_name=$1
stage=$2

# Reads DNN configuration
. definitions/chain/prep/$config_name

dir=exp/chain/prep/$config_name
dprep=exp/chain/dataprep/$dataprep
SDG_LOG_DIR=$dir/log

mkdir -p $dir/{log,egs,tree}

train_data_lores=$dprep/data/train_lores_comb
train_data=$dprep/data/train_comb
ali_dir=exp/chain/dataprep/$dataprep/ali

. definitions/chain/dataprep/$dataprep

if [ $stage -le 0 ]; then
  echo "stage 0"
  if [ ! -d $dir/lang ]; then
    cp -r $data_lang $dir/lang
  fi
fi

if [ $stage -le 1 ]; then
  echo "stage 1"
  steps/nnet3/chain/gen_topo.py $(cat $dir/lang/phones/silence.csl) \
                                $(cat $dir/lang/phones/nonsilence.csl) \
                                > $dir/lang/topo
fi

if [ $stage -le 2 ]; then
  echo "stage 2"
  steps/nnet3/chain/build_tree.sh --frame-subsampling-factor 3 \
    --context-opts "--context-width=2 --central-position=1" \
    --leftmost-questions-truncate $leftmost_questions_truncate \
    --cmd "slurm.pl --mem 16M" $tree_numleaves $train_data_lores $dir/lang $ali_dir $dir/tree
fi

if [ $stage -le 3 ]; then
  echo "stage 3"
  mkdir -p $dir/tdnn
  if [ ! -d $dir/egs ]; then
    ln -rs $dir/tdnn/egs $dir/egs
  fi
fi

num_targets=$(tree-info $dir/tree/tree |grep num-pdfs|awk '{print $2}')
feat_dim=$(feat-to-dim scp:$dprep/data/train_comb/feats.scp -)
ivec_dim=$(feat-to-dim scp:$dprep/ivec/ivectors_train/ivector_online.scp -)
learning_rate_factor=5

if [ $stage -le 4 ]; then
echo "stage 4"
cat <<EOF > $dir/config
dataprep=$dataprep
tree_numleaves=$tree_numleaves
leftmost_questions_truncate=$leftmost_questions_truncate
chunk_width=$chunk_width
chunk_left_context=$chunk_left_context
chunk_right_context=$chunk_right_context
model_left_context=$model_left_context
model_right_context=$model_right_context
frames_overlap_per_eg=$frames_overlap_per_eg
frames_per_iter=$frames_per_iter
chain_lm_opts="$chain_lm_opts"
num_targets=$num_targets
feat_dim=$feat_dim
ivec_dim=$ivec_dim
EOF
fi

if [ $stage -le 5 ]; then
echo "stage 5"
mkdir -p $dir/tdnn/configs
cat <<EOF > $dir/tdnn/configs/network.xconfig
  input dim=$ivec_dim name=ivector
  input dim=$feat_dim name=input
  # please note that it is important to have input layer with the name=input
  # as the layer immediately preceding the fixed-affine-layer to enable
  # the use of short notation for the descriptor
  fixed-affine-layer name=lda input=Append(-$model_left_context,0,$model_right_context,ReplaceIndex(ivector, t, 0)) affine-transform-file=$dir/tdnn/configs/lda.mat
  # the first splicing is moved before the lda layer, so no splicing here
  relu-renorm-layer name=tdnn1 dim=450
  ## adding the layers for chain branch
  relu-renorm-layer name=prefinal-chain input=tdnn1 dim=450 target-rms=0.5
  output-layer name=output include-log-softmax=false dim=$num_targets max-change=1.5
  # adding the layers for xent branch
  # This block prints the configs for a separate output that will be
  # trained with a cross-entropy objective in the 'chain' models... this
  # has the effect of regularizing the hidden parts of the model.  we use
  # 0.5 / args.xent_regularize as the learning rate factor- the factor of
  # 0.5 / args.xent_regularize is suitable as it means the xent
  # final-layer learns at a rate independent of the regularization
  # constant; and the 0.5 was tuned so as to make the relative progress
  # similar in the xent and regular final layers.
  relu-renorm-layer name=prefinal-xent input=tdnn1 dim=450 target-rms=0.5
  output-layer name=output-xent dim=$num_targets learning-rate-factor=$learning_rate_factor max-change=1.5
EOF
steps/nnet3/xconfig_to_configs.py --xconfig-file $dir/tdnn/configs/network.xconfig --config-dir $dir/tdnn/configs/
fi

if [ $stage -le 6 ]; then
echo "stage 6"
steps/nnet3/chain/train.py \
    --cmd "run.pl" \
    --feat.online-ivector-dir $dprep/ivec/ivectors_train \
    --feat.cmvn-opts "--norm-means=false --norm-vars=false" \
    --chain.lm-opts="$chain_lm_opts" \
    --egs.opts "--frames-overlap-per-eg $frames_overlap_per_eg" \
    --egs.chunk-width $chunk_width \
    --egs.chunk-right-context $chunk_right_context \
    --egs.chunk-left-context $chunk_left_context \
    --egs.cmd "slurm.pl --mem 16M --time 01:30:00" \
    --trainer.frames-per-iter $frames_per_iter \
    --cleanup.remove-egs false \
    --feat-dir $train_data \
    --tree-dir $dir/tree \
    --lat-dir $dprep/lats \
    --dir $dir/tdnn \
    --stage -100 \
    --exit-stage 0
fi