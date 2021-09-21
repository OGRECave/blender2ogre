import bpy

# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    # ...so we need to reload our submodule(s) using importlib
    import importlib
    if "config" in locals():
        importlib.reload(config)
    if "report" in locals():
        importlib.reload(report)
    if "importer" in locals():
        importlib.reload(importer)
    if "export" in locals():
        importlib.reload(export)
    if "meshy" in locals():
        importlib.reload(meshy)

# This is only relevant on first run, on later reloads those modules
# are already in locals() and those statements do not do anything.
import shutil
from .. import config
from ..report import Report
from . import importer
from . import export
from ..meshy import OGREMESH_OT_preview
from os.path import exists

# Variable to visibility state of the mesh preview button is displayed
meshpreviewButtonDisplayed = False

# Function to update the visibility state of the Ogre mesh preview button. Only shows if 'MESH_PREVIEWER' points to a valid path
def update_meshpreview_button_visibility(show):
    global meshpreviewButtonDisplayed

    if show:
        meshpreviewerExists = shutil.which(config.get('MESH_PREVIEWER')) is not None # Check `MESH_PREVIEWER` path is valid. Should check PATH environment variables as well
        if meshpreviewerExists:        
            if not meshpreviewButtonDisplayed:
                # 19/09/2021 - oldmanauz: I don't think this is the proper way to do this. bpy.types.VIEW3D_PT_tools_active doesn't exist in the documentation here: https://docs.blender.org/api/current/bpy.types.html
                # Does this mean it is poorly supported, undefined or depreciated? Possible solution for future implemtation: bpy.utils.register_tool() & bpy.types.WorkSpaceTool;
                bpy.types.VIEW3D_PT_tools_active.append(add_preview_button)
                meshpreviewButtonDisplayed = True
        else:
            if meshpreviewButtonDisplayed:
                bpy.types.VIEW3D_PT_tools_active.remove(add_preview_button)
                meshpreviewButtonDisplayed = False
                
    elif not show and meshpreviewButtonDisplayed:
        bpy.types.VIEW3D_PT_tools_active.remove(add_preview_button)
        meshpreviewButtonDisplayed = False

def add_preview_button(self, context):
    layout = self.layout
    op = layout.operator( 'ogremesh.preview', text='', icon='VIEWZOOM' )
    if op is not None:
        op.mesh = True

def auto_register(register):
    #yield OGRE_HT_toggle_ogre #
    #yield OGRE_OP_interface_toggle
    yield OGRE_MT_mini_report
    yield OGREMESH_OT_preview

    # Tries to show the Ogre mesh preview button
    update_meshpreview_button_visibility(register)    
    
    yield from importer.auto_register(register)
    yield from export.auto_register(register)

    #if register and config.get('INTERFACE_TOGGLE'):
        #OGRE_OP_interface_toggle.toggle(True)

"""
General purpose ui elements
"""

class OGRE_MT_mini_report(bpy.types.Menu):
    bl_label = "Mini-Report | (see console for full report)"
    def draw(self, context):
        layout = self.layout
        txt = Report.report()
        for line in txt.splitlines():
            layout.label(text=line)

