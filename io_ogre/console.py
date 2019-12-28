import bpy
import sys
import os
import re
from os.path import join, split

def export(object_names):
    for name in object_names:
        index = bpy.data.objects.find(name)
        if index != -1:
            obj = bpy.data.objects[index]
            obj.data.update()
            obj.data.calc_loop_triangles()
            export_mesh(obj, '/tmp')


if __name__ == "__main__":
    idx = sys.argv.index('--')
    argv = sys.argv[idx+2:]
    path = sys.argv[idx+1]

    # cut off file name
    io_ogre = os.path.split(__file__)[0]
    # cut off io_ogre dir
    io_ogre = os.path.split(io_ogre)[0]
    sys.path.append(io_ogre)

    os.makedirs(path, exist_ok=True, mode=0o775)

    from io_ogre import config
    from io_ogre.ogre.scene import dot_scene
    from io_ogre.ogre.mesh  import dot_mesh
    from io_ogre.ogre.skeleton import dot_skeleton

    match = re.compile("scene (.*)").match(argv[0])
    if match:
        scene_name = match.group(1)
        dot_scene(path, scene_name=scene_name)

