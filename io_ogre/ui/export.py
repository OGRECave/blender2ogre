
import bpy
from .. import shader
from ..util import ui_register
from ..ogre.export import _OgreCommonExport_
from bpy.props import IntProperty

def auto_register(register):
    yield OP_ogre_export

    if register:
        bpy.types.INFO_MT_file_export.append(menu_func)
    else:
        bpy.types.INFO_MT_file_export.remove(menu_func)

class OP_ogre_export(bpy.types.Operator, _OgreCommonExport_):
    '''Export Ogre Scene'''
    bl_idname = "ogre.export"
    bl_label = "Export Ogre"
    bl_options = {'REGISTER'}

    # Basic options
    EXPORT_TYPE = 'OGRE'

def menu_func(self, context):
    """ invoked when export in drop down menu is clicked """
    op = self.layout.operator(OP_ogre_export.bl_idname, text="Ogre3D (.scene and .mesh)")
    return op

