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
            obj.data.update(calc_tessface=True)
            export_mesh(obj, '/tmp')


if __name__ == "__main__":
    idx = sys.argv.index('--')
    argv = sys.argv[idx+3:]
    path = sys.argv[idx+2]
    io_ogre_path = sys.argv[idx+1]

    sys.path.append(io_ogre_path)

    from io_ogre import config
    from io_ogre.ogre.scene import dot_scene
    from io_ogre.ogre.mesh  import dot_mesh
    from io_ogre.ogre.skeleton import dot_skeleton

    match = re.compile("scene (.*)").match(argv[0])
    if match:
        scene_name = match.group(1)
        dot_scene(path, scene_name=scene_name)

