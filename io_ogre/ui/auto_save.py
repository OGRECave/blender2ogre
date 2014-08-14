import bpy
from .. import config
from ..report import Report

def auto_register(register):
    yield OP_config_autosave

class OP_config_autosave(bpy.types.Operator):
    '''operator: saves current b2ogre configuration'''
    bl_idname = "ogre.save_config"
    bl_label = "save config file"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return True

    def invoke(self, context, event):
        config.save_config()
        print("save config!!!")
        Report.reset()
        Report.messages.append('SAVED %s' %CONFIG_FILEPATH)
        Report.show()
        return {'FINISHED'}

