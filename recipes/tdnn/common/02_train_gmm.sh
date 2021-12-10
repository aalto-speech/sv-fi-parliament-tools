#!/bin/bash
#SBATCH --time=16:00:00
#SBATCH --mem-per-cpu=8G
#SBATCH --output=logs/train_gmm.%j.out

echo "$0 $@"  # Print the command line for logging
export LC_ALL=C
set -eu

min_seg_len=1.55

# Pre-requisites:
# - Data folder has mfcc (lowres) and cmvn (stage 01)
# - A configuration for the GMM models
# - A language model (G.fst) and an evaluation set for evaluation

[ -f path.sh ] && . ./path.sh # source the path.

#Begin Configuration
log_mfcc=logs/mfcc
log_cmvn=logs/cmvn
nj=20
stage=0
dev_data=
#End Configuration

. parse_options.sh || exit 1;

if [ $# != 2 ]; then
   echo "usage: train_am.sh prefix gmm_conf"
   exit 1;
fi

# prefix refers to the data name, it is assumed there is a folder named {$prefix}_train in ./data
prefix=${1}_
prefi=$1
gmm_conf=$2

train_cmd="slurm.pl --mem 16M --time 01:30:00"
decode_cmd="slurm.pl --mem 2G --time 01:30:00"

recog_lang=data/word_400k
rl_name=word_400k

function error_exit {
    echo "$1" >&2
    exit "${2:-1}"
}

if [ $stage -le 0 ]; then
    if [ -d data/${prefix}lang ]; then
        echo "data/${prefix}lang already exists"
        exit 0
    fi

    if [ ! -f data/${prefix}train/vocab ]; then
        echo "Vocabulary missing, creating vocabulary"
        python common/create_vocab.py data/${prefix}train
    fi
    common/make_dict.sh data/${prefix}train/vocab data/${prefix}dict
    utils/prepare_lang.sh --position-dependent-phones true data/${prefix}dict "<UNK>" data/${prefix}lang/local data/${prefix}lang
fi

# Load GMM configuration, sets the number of leaves and the number of gaussians for different models, sets gmm_conf_name
. $gmm_conf

if [ $stage -le 1 ]; then
    if [ -d data/${prefix}train_10kshort ]; then
        echo "data/${prefix}train_10kshort already exists"
        exit 0
    fi

    # Make short dir
    if [[ $(wc -l < data/${prefix}train/utt2spk) -gt 10000 ]]; then
        utils/subset_data_dir.sh --shortest data/${prefix}train ${sub_size:-10000} data/${prefix}train_10kshort
    else
        ln -rs data/${prefix}train data/${prefix}train_10kshort
    fi
fi

mono_gmm=exp/${prefix}mono
tri1_gmm=exp/${prefix}tri1$gmm_conf_name
tri2_gmm=exp/${prefix}tri2$gmm_conf_name
tri3_gmm=exp/${prefix}tri3$gmm_conf_name

if [ $stage -le 2 ]; then
    if [ ! -f $mono_gmm/final.mdl ]; then
        steps/train_mono.sh --boost-silence 1.25 --nj 10 --cmd "$train_cmd" data/${prefix}train_10kshort data/${prefix}lang $mono_gmm
    
        utils/mkgraph.sh $recog_lang $mono_gmm $mono_gmm/graph_$rl_name
        steps/decode.sh --cmd "$decode_cmd" --nj 10 $mono_gmm/graph_$rl_name data/$dev_data $mono_gmm/decode_$dev_data

        steps/align_si.sh --boost-silence 1.25 --nj $nj --cmd "$train_cmd" data/${prefix}train data/${prefix}lang $mono_gmm ${mono_gmm}_ali
    fi
fi

if [ $stage -le 3 ]; then
    steps/train_deltas.sh --boost-silence 1.25 --cmd "$train_cmd" $tri1_leaves $tri1_gauss data/${prefix}train data/${prefix}lang ${mono_gmm}_ali $tri1_gmm
    
    utils/mkgraph.sh $recog_lang $tri1_gmm $tri1_gmm/graph_$rl_name
    steps/decode.sh --cmd "$decode_cmd" --nj 10 $tri1_gmm/graph_$rl_name data/$dev_data $tri1_gmm/decode_$dev_data

    steps/align_si.sh --nj $nj --cmd "$train_cmd" data/${prefix}train data/${prefix}lang $tri1_gmm ${tri1_gmm}_ali
fi

if [ $stage -le 4 ]; then
    steps/train_lda_mllt.sh --cmd "$train_cmd" --splice-opts "--left-context=3 --right-context=3" $tri2_leaves $tri2_gauss data/${prefix}train data/${prefix}lang ${tri1_gmm}_ali $tri2_gmm
    
    utils/mkgraph.sh $recog_lang $tri2_gmm $tri2_gmm/graph_$rl_name
    steps/decode.sh --cmd "$decode_cmd" --nj 10 $tri2_gmm/graph_$rl_name data/$dev_data $tri2_gmm/decode_$dev_data
    
    steps/align_si.sh  --nj $nj --cmd "$train_cmd"  data/${prefix}train data/${prefix}lang $tri2_gmm ${tri2_gmm}_ali
fi

if [ $stage -le 5 ]; then
    steps/train_sat.sh --cmd "$train_cmd" $tri3_leaves $tri3_gauss data/${prefix}train data/${prefix}lang ${tri2_gmm}_ali $tri3_gmm
    
    utils/mkgraph.sh $recog_lang $tri3_gmm $tri3_gmm/graph_$rl_name
    steps/decode_fmllr.sh --cmd "$decode_cmd" --nj 10 $tri3_gmm/graph_$rl_name data/$dev_data $tri3_gmm/decode_$dev_data
fi

