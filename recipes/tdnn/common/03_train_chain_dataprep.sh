#!/bin/bash
#SBATCH --time=16:00:00
#SBATCH --mem-per-cpu=8G
#SBATCH --output=logs/train_chain_dataprep.%j.out

echo "$0 $@"  # Print the command line for logging
export LC_ALL=C
set -euo pipefail
IFS=$'\n\t'

#Begin Configuration
train_set=
gmm=
data_lang=

speed_perturb=true
vol_perturb=true
mfcc_conf=mfcc_hires
min_seg_len=1.55
ivec_dim=512
#End Configuration

[ -f path.sh ] && . ./path.sh # source the path.
#. parse_options.sh || exit 1;

if [ $# != 3 ]; then
   echo "usage: train_chain_dataprep.sh config_name dataprep_conf stage"
   exit 1;
fi

. ./cmd.sh ## You'll want to change cmd.sh to something that will work on your system.
           ## This relates to the queue.

config_name=$1
dataprep_conf=$2 # definitions/chain/dataprep/$config_name
stage=$3

. $dataprep_conf

dir=exp/chain/dataprep/$config_name
SDG_LOG_DIR=$dir/log
mkdir -p $dir/{data,ali,lats}
data=$dir/data

mkdir -p $data/orig

if [ $stage -le 0 ]; then
   echo "stage 0"
   
   if [ ! -f $data/orig/train ]; then
      ln -rs $train_set $data/orig/train;
   fi

   if [ ! -f $data/orig/train/utt2dur ]; then
      utils/data/get_utt2dur.sh $data/orig/train
   fi

fi

if [ $stage -le 1 ]; then
   echo "stage 1"
   if [ $speed_perturb ]; then
      utils/data/perturb_data_dir_speed_3way.sh $data/orig/train $data/train
   else
      utils/copy_data_dir.sh $data/orig/train $data/train
   fi

   if [ $vol_perturb ]; then
      utils/data/perturb_data_dir_volume.sh $data/train
   fi

   utils/copy_data_dir.sh $data/train $data/train_lores
   utils/validate_data_dir.sh --no-feats $data/train
fi

if [ $stage -le 2 ]; then
   echo "stage 2"
   numjobs=$(( $(wc -l < $data/orig/train/spk2utt) / 10 ))
   steps/make_mfcc.sh --cmd "slurm.pl --mem 4G --time 04:30:00" --nj ${numjobs} $data/train_lores
   steps/compute_cmvn_stats.sh $data/train_lores
   utils/fix_data_dir.sh $data/train_lores
   utils/validate_data_dir.sh $data/train_lores
fi

if [ $stage -le 3 ]; then
   echo "stage 3" 
   numjobs=$(( $(wc -l < $data/orig/train/spk2utt) / 3 ))
   steps/make_mfcc.sh --mfcc-config conf/${mfcc_conf}.conf --cmd "slurm.pl --mem 4G --time 06:30:00" --nj ${numjobs} $data/train
   steps/compute_cmvn_stats.sh $data/train
   utils/fix_data_dir.sh $data/train
   utils/validate_data_dir.sh $data/train
fi

if [ $stage -le 4 ]; then
   echo "stage 4"
   utils/data/combine_short_segments.sh $data/train $min_seg_len $data/train_comb
   steps/compute_cmvn_stats.sh $data/train_comb
   utils/validate_data_dir.sh --no-wav $data/train_comb

   utils/data/combine_short_segments.sh $data/train_lores $min_seg_len $data/train_lores_comb
   steps/compute_cmvn_stats.sh $data/train_lores_comb
   utils/validate_data_dir.sh --no-wav $data/train_lores_comb
fi

numjobs=50 #$(wc -l < $data/orig/train/spk2utt)
if [ $stage -le 5 ]; then
   echo "stage 5"
   steps/align_fmllr.sh --nj $numjobs --cmd "slurm.pl --mem 128M --time 04:30:00" $data/train_lores_comb $data_lang $gmm $dir/ali
   steps/align_fmllr_lats.sh --nj $(($numjobs*2)) --cmd "slurm.pl --mem 128M --time 04:30:00" $data/train_lores_comb $data_lang $gmm $dir/lats
fi

if [ $ivec_dim -le 0 ]; then
   exit 0
fi

ivec=$dir/ivec
if [ $stage -le 6 ]; then
   echo "stage 6"
   mkdir -p $ivec/data
   utils/data/modify_speaker_info.sh --utts-per-spk-max 2 $data/train_comb $ivec/data/train_comb_max2
   
   utils/data/subset_data_dir.sh --utt-list $data/orig/train/feats.scp $data/train $ivec/data/train
   if [ $(wc -l < $data/orig/train/feats.scp) != $(wc -l < $ivec/data/train/feats.scp) ]; then
      echo "error in ivector training feats"
      exit 1
   fi
fi

if [ $stage -le 7 ]; then
   echo "stage 7"
   mkdir -p $ivec/in_ali
   #numjobs=$(wc -l < $data/orig/train/spk2utt)
   numjobs=20
   steps/align_fmllr.sh --nj $numjobs --cmd "slurm.pl --mem 128M --time 01:30:00" $data/orig/train $data_lang $gmm $ivec/in_ali
fi

numjobs=20
if [ $stage -le 8 ]; then
   echo "stage 8"
   mkdir -p $ivec/tri5
   steps/train_lda_mllt.sh --cmd "$train_cmd" --num-iters 7 --mllt-iters "2 4 6" \
                           --splice-opts "--left-context=3 --right-context=3" \
                           3000 10000 $ivec/data/train $data_lang \
                           $ivec/in_ali $ivec/tri5
fi

if [ $stage -le 9 ]; then
   echo "stage 9"
   mkdir -p $ivec/diag_ubm
   steps/online/nnet2/train_diag_ubm.sh --cmd "slurm.pl --mem 16M --time 01:30:00" --nj $numjobs \
      --num-frames 700000 --num-threads 1 $ivec/data/train $ivec_dim $ivec/tri5 $ivec/diag_ubm
fi

if [ $stage -le 10 ]; then
   echo "stage 10"
   steps/online/nnet2/train_ivector_extractor.sh --cmd "slurm.pl --mem 16M --time 01:30:00" --nj $numjobs --num_threads 1 --num_processes 1 $ivec/data/train $ivec/diag_ubm $ivec/extractor
fi

if [ $stage -le 11 ]; then
   echo "stage 11"
   steps/online/nnet2/extract_ivectors_online.sh --cmd "slurm.pl --mem 16M --time 01:30:00" --nj $numjobs \
      $ivec/data/train_comb_max2 $ivec/extractor \
      $ivec/ivectors_train
fi