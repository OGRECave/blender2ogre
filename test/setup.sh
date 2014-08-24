
NAME=`uname -s`

if [ $NAME == "Darwin" ]; then
    curl -o test/blender/blender2.71.zip\
        "http://ftp.halifax.rwth-aachen.de/blender/release/Blender2.71/blender-2.71-OSX_10.6-j2k-fix-x86_64.zip"
    mkdir -p test/blender/2.71
    unzip -d test/blender/2.71 test/blender/blender2.71.zip
fi

