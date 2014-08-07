
import bpy
from ..ogre.export import export_mesh

def export(object_names):
    for name in object_names:
        index = bpy.data.objects.find(name)
        if index != -1:
            obj = bpy.data.objects[index]
            obj.data.update(calc_tessface=True)
            export_mesh(obj, '/tmp')
