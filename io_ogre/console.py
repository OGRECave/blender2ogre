import bpy
import sys
import os
from os.path import join, split

#sys.path.append(split(os.getcwd())[0])
#print(sys.path)

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
    print(sys.path)

    from ogre.scene import dot_scene
    from ogre.mesh  import dot_mesh
    from ogre.mesh  import dot_skeleton

    if argv[0] == "scene":
        scene_name = argv[1]
        dot_scene(path, scene_name=scene_name)

