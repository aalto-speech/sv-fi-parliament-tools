#!/bin/bash
#SBATCH --time=04:00:00
#SBATCH --mem-per-cpu=4G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/prepare_dataset.%j.out

set -euo pipefail

#Begin Configuration
mfcc_config=conf/mfcc.conf
log_mfcc=logs/mfcc
log_cmvn=logs/cmvn
#End Configuration

. utils/parse_options.sh || exit 1;

if [ $# != 1 ]; then
   echo "usage: recipes/prepare_dataset.sh [options] <data-dir>"
   echo "   eg: recipes/prepare_dataset.sh data/01h"
   echo "   for options see the configuration header of this file."
   exit 1;
fi

datadir=$1

if [ ! -f ${datadir}/feats.scp ]; then
  steps/make_mfcc.sh --mfcc-config $mfcc_config --nj 1 $datadir $log_mfcc
fi

if [ ! -f ${datadir}/cmvn.scp ]; then
  steps/compute_cmvn_stats.sh $datadir $log_cmvn
fi

utils/fix_data_dir.sh $datadir
utils/validate_data_dir.sh --no-text $datadir