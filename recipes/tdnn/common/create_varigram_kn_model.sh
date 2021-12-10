#!/bin/bash
#SBATCH --time=01:00:00
#SBATCH --mem-per-cpu=4G
#SBATCH --output=logs/create_varigram_kn_model.%j.out
set -eu

module load variKN 
. ./cmd.sh

maxorder=10 #-n --norder
cutoffs="0 0 1" #-O --cutoffs
scale=0.001 #-D --dscale
prune_scale= #-E --dscale2
extra_args="--clear_history --3nzer --arpa" #-C -3 -a

data="$1"
#devdata="$2"

out=models/arpa/comb_stde_train
mkdir $out

echo "Training VariKN N-gram model"

if [ -z "$prune_scale" ]; then
  prune_scale=$(echo "$scale * 2" | bc) # 2 x scale is the recommendation
fi

#Sentence boundary tags:
train_data_str="cat data/comb_stde_train/corpus |"
#dev_data_str="$devdata | sed -e 's:^:<s> :' -e 's:$: </s>:' |"

varigram_kn \
  --cutoffs="$cutoffs" \
  --dscale=$scale \
  --dscale2=$prune_scale \
  --norder=$maxorder \
  $extra_args \
  "$train_data_str" $out/varikn.lm.gz

# --opti "$dev_data_str" \
# --dscale2=$prune_scale \

# utils/format_lm.sh data/comb_stde_lang models/arpa/comb_stde_train/varikn.lm.gz data/comb_stde_lang/local/lexiconp.txt data/comb_stde_g