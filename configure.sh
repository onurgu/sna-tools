

ARCH=`uname -m`

arch=32
if [[ $ARCH -eq 'x86_64' ]]; then
    arch=64
fi

ln -sf MP-1.0-Linux$arch/turkish.fst turkish.fst
ln -sf MP-1.0-Linux$arch/TurkishMorphology.so TurkishMorphology.so