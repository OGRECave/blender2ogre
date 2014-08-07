
import bpy
from .. import shader
from ..util import ui_register
from ..ogre.export import _OgreCommonExport_
from bpy.props import IntProperty

class OP_ogre_export(bpy.types.Operator, _OgreCommonExport_):
    '''Export Ogre Scene'''
    bl_idname = "ogre.export"
    bl_label = "Export Ogre"
    bl_options = {'REGISTER'}

    # Basic options
    EXPORT_TYPE = 'OGRE'

def menu_func(self, context):
    """ invoked when export in drop down menu is clicked """
    op = self.layout.operator(INFO_OT_createOgreExport.bl_idname, text="Ogre3D (.scene and .mesh)")

