#!/usr/bin/env bash

# Expects to be run with Kaldi utils folder
export PATH="$PWD/utils:$PWD:$PATH"

# Used with Kaldi commit 5968b4c, anaconda used for pandas and numpy
module load kaldi-2020 anaconda

export LC_ALL=C