import bpy, sys, os, subprocess
from bpy.props import BoolProperty
from .report import Report

## OgreMeshy

class OgreMeshyPreviewOp(bpy.types.Operator):
    '''helper to open ogremeshy'''
    bl_idname = 'ogremeshy.preview'
    bl_label = "opens ogremeshy in a subprocess"
    bl_options = {'REGISTER'}
    preview = BoolProperty(name="preview", description="fast preview", default=True)
    groups = BoolProperty(name="preview merge groups", description="use merge groups", default=False)
    mesh = BoolProperty(name="update mesh", description="update mesh (disable for fast material preview", default=True)

    @classmethod
    def poll(cls, context):
        if context.active_object and context.active_object.type in ('MESH','EMPTY') and context.mode != 'EDIT_MESH':
            if context.active_object.type == 'EMPTY' and context.active_object.dupli_type != 'GROUP':
                return False
            else:
                return True

    def execute(self, context):
        Report.reset()
        Report.messages.append('running %s' %CONFIG['OGRE_MESHY'])

        if sys.platform.startswith('linux'):
            # If OgreMeshy ends with .exe, set the path for preview meshes to
            # the user's wine directory, otherwise to /tmp.
            if CONFIG['OGRE_MESHY'].endswith('.exe'):
                path = '%s/.wine/drive_c/tmp' % os.environ['HOME']
            else:
                path = '/tmp'
        elif sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
            path = '/tmp'
        else:
            path = 'C:\\tmp'

        mat = None
        mgroup = merged = None
        umaterials = []

        if context.active_object.type == 'MESH':
            mat = context.active_object.active_material
        elif context.active_object.type == 'EMPTY': # assume group
            obs = []
            for e in context.selected_objects:
                if e.type != 'EMPTY' and e.dupli_group: continue
                grp = e.dupli_group
                subs = []
                for o in grp.objects:
                    if o.type=='MESH': subs.append( o )
                if subs:
                    m = merge_objects( subs, transform=e.matrix_world )
                    obs.append( m )
            if obs:
                merged = merge_objects( obs )
                umaterials = dot_mesh( merged, path=path, force_name='preview' )
                for o in obs: context.scene.objects.unlink(o)

        if not self.mesh:
            for ob in context.selected_objects:
                if ob.type == 'MESH':
                    for mat in ob.data.materials:
                        if mat and mat not in umaterials: umaterials.append( mat )

        if not merged:
            mgroup = MeshMagick.get_merge_group( context.active_object )
            if not mgroup and self.groups:
                group = get_merge_group( context.active_object )
                if group:
                    print('--------------- has merge group ---------------' )
                    merged = merge_group( group )
                else:
                    print('--------------- NO merge group ---------------' )
            elif len(context.selected_objects)>1 and context.selected_objects:
                merged = merge_objects( context.selected_objects )

            if mgroup:
                for ob in mgroup.objects:
                    nmats = dot_mesh( ob, path=path )
                    for m in nmats:
                        if m not in umaterials: umaterials.append( m )
                MeshMagick.merge( mgroup, path=path, force_name='preview' )
            elif merged:
                umaterials = dot_mesh( merged, path=path, force_name='preview' )
            else:
                umaterials = dot_mesh( context.active_object, path=path, force_name='preview' )

        if mat or umaterials:
            #CONFIG['TOUCH_TEXTURES'] = True
            #CONFIG['PATH'] = path   # TODO deprecate
            data = ''
            for umat in umaterials:
                data += generate_material( umat, path=path, copy_programs=True, touch_textures=True ) # copies shader programs to path
            f=open( os.path.join( path, 'preview.material' ), 'wb' )
            f.write( bytes(data,'utf-8') ); f.close()

        if merged: context.scene.objects.unlink( merged )

        if sys.platform.startswith('linux') or sys.platform.startswith('darwin') or sys.platform.startswith('freebsd'):
            if CONFIG['OGRE_MESHY'].endswith('.exe'):
                cmd = ['wine', CONFIG['OGRE_MESHY'], 'c:\\tmp\\preview.mesh' ]
            else:
                cmd = [CONFIG['OGRE_MESHY'], '/tmp/preview.mesh']
            print( cmd )
            #subprocess.call(cmd)
            subprocess.Popen(cmd)
        else:
            #subprocess.call([CONFIG_OGRE_MESHY, 'C:\\tmp\\preview.mesh'])
            subprocess.Popen( [CONFIG['OGRE_MESHY'], 'C:\\tmp\\preview.mesh'] )

        Report.show()
        return {'FINISHED'}

