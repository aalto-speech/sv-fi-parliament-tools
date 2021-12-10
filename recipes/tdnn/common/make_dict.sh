#!/bin/bash

set -eu

export LC_ALL=C

# Begin configuration section.
# End configuration options.

echo "$0 $@"  # Print the command line for logging

[ -f path.sh ] && . ./path.sh # source the path.
. parse_options.sh || exit 1;

if [ $# != 2 ]; then
   echo "usage: common/make_dict.sh vocab dir_out"
   echo "e.g.:  common/make_dict.sh data/train/vocab data/dict"
   echo "main options (for others, see top of script file)"
   exit 1;
fi

vocab=$1
outdir=$2

tmpdir=$(mktemp -d)
echo "Tmpdir: ${tmpdir}"
cat data/lexicon/lexicon.txt definitions/dict_prep/lex | common/filter_lex.py - ${vocab} ${tmpdir}/found.lex ${tmpdir}/oov

if [ -f local/make_dict.py ]; then
mv $tmpdir/oov $tmpdir/oov2
cat $tmpdir/found.lex <(local/make_dict.py < $tmpdir/oov2) | common/filter_lex.py - ${vocab} $tmpdir/found2.lex $tmpdir/oov
mv $tmpdir/found2.lex $tmpdir/found.lex
fi

echo "$(wc -l ${tmpdir}/oov) pronunciations are missing, estimating them with phonetisaurus"
cat ${tmpdir}/oov
touch ${tmpdir}/oov.lex
if [[ $(wc -l < $tmpdir/oov) > 0 ]]; then
phonetisaurus-g2pfst --print_scores=false --model=data/lexicon/g2p_wfsa --wordlist=${tmpdir}/oov | sed "s/\t$/\tSPN/" > ${tmpdir}/oov.lex
fi
mkdir -p ${outdir}
cat ${tmpdir}/found.lex ${tmpdir}/oov.lex definitions/dict_prep/lex | sort -u > ${outdir}/lexicon.txt
rm -f ${outdir}/lexiconp.txt
echo "SIL" > ${tmpdir}/silence_phones.txt
cut -f2 definitions/dict_prep/lex >> ${tmpdir}/silence_phones.txt
sort -u < ${tmpdir}/silence_phones.txt > ${outdir}/silence_phones.txt

echo "SIL" > ${outdir}/optional_silence.txt

cut -f2- < ${outdir}/lexicon.txt | tr ' ' '\n' | sed 's/^[ \t]*//;s/[ \t]*$//' | sed '/^$/d' | sort -u | grep -v -F -f ${outdir}/silence_phones.txt > ${outdir}/nonsilence_phones.txt

rm -Rf ${tmpdir}
