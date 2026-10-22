# Code that handles the "Ogre Mesh Preview" button
# Exports current model to temp folder and loads Ogre viewer from commandline

import bpy, sys, os, subprocess, logging
from bpy.props import BoolProperty
from .report import Report
from . import config
from .ogre.mesh import dot_mesh
from .ogre.material import dot_materials
from .util import objects_merge_materials, merge_objects, get_merge_group, merge_group

## This class is called when the "Preview Mesh" button is pressed. It opens the Ogre mesh previewer
## The button is created int ui/__init__.py > auto_register() function.
class OGREMESH_OT_preview(bpy.types.Operator):
    '''helper to open ogremesh'''
    bl_idname = 'ogremesh.preview'
    bl_label = "opens mesh viewer in a subprocess"
    bl_options = {'REGISTER'}
    preview : BoolProperty(name="preview", description="fast preview", default=True)
    groups : BoolProperty(name="preview merge groups", description="use merge groups", default=False)
    mesh : BoolProperty(name="update mesh", description="update mesh (disable for fast material preview", default=True)

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type in ('MESH','EMPTY') and context.mode != 'EDIT_MESH':
            if context.active_object.type == 'EMPTY' and context.active_object.instance_type != 'COLLECTION':
                return False
            else:
                return True

    def execute(self, context):
        Report.reset()
        Report.messages.append('Running: "%s"' % config.get('MESH_PREVIEWER'))

        if sys.platform.startswith('linux') or sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
            path = os.path.expanduser("~/io_blender2ogre") # use $HOME so snap can access it
            if not os.path.exists(path):
                os.makedirs(path)
        else:
            path = 'C:\\tmp'

        merged = None

        if context.active_object.type == 'EMPTY': # assume group
            obs = []
            for e in context.selected_objects:
                if e.type != 'EMPTY' and e.instance_collection: continue
                grp = e.instance_collection
                subs = []
                for o in grp.objects:
                    if o.type=='MESH': subs.append( o )
                if subs:
                    m = merge_objects( subs, transform=e.matrix_world )
                    obs.append( m )
            if obs:
                merged = merge_objects( obs )
                dot_mesh( merged, path=path, force_name='preview' )
                for o in obs: context.scene.objects.unlink(o)

        if not merged:
            if self.groups:
                group = get_merge_group( context.active_object )
                if group:
                    print('--------------- has merge group ---------------' )
                    merged = merge_group( group )
                else:
                    print('--------------- NO merge group ---------------' )
            elif len(context.selected_objects)>1 and context.selected_objects:
                merged = merge_objects( context.selected_objects )

            dot_mesh( merged or context.active_object, path=path, force_name='preview', overwrite=True )

        mats = objects_merge_materials([merged or context.active_object])
        dot_materials(mats, path, False, "preview")

        if merged: context.scene.objects.unlink( merged )

        try:
            os.environ["OGRE_MIN_LOGLEVEL"] = "3" # only warnings and up
            if sys.platform.startswith('linux') or sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
                subprocess.Popen([config.get('MESH_PREVIEWER'), path + '/preview.mesh'])
            else:
                subprocess.Popen([config.get('MESH_PREVIEWER'), 'C:\\tmp\\preview.mesh'] )
        except:
            Report.errors.append('Viewer not found at "%s"' % config.get('MESH_PREVIEWER'))

        Report.show()
        return {'FINISHED'}

