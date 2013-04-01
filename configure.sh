#!/bin/bash

arch=32
if [[ $arch -eq 'x86_64' ]]; then
    arch=64
fi

ln -sf lib/MP-1.0-Linux$arch/turkish.fst turkish.fst
ln -sf lib/MP-1.0-Linux$arch/TurkishMorphology.so TurkishMorphology.so

ln -sf lib/Rovereto-Twitter-Tokenizer/tokenizer.py tokenizer.py
ln -sf lib/Rovereto-Twitter-Tokenizer/aux.py aux.py

ln -sf lib/turkish-deasciifier/turkish turkish

# require python >= 2.7
# require easy_install
# require virtualenv
# require virtualenvwrapper

# mkvirtualenv twitter (if doesn't exist; else workon twitter)
#### use pip to install required packages
#### deactivate

mkdir -p captures/timelines