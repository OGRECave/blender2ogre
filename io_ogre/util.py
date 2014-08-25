import mathutils
import logging
import time
import bpy
from .config import CONFIG
from itertools import chain

def swap(vec):
    if CONFIG['SWAP_AXIS'] == 'xyz': return vec
    elif CONFIG['SWAP_AXIS'] == 'xzy':
        if len(vec) == 3: return mathutils.Vector( [vec.x, vec.z, vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, vec.x, vec.z, vec.y] )
    elif CONFIG['SWAP_AXIS'] == '-xzy':
        if len(vec) == 3: return mathutils.Vector( [-vec.x, vec.z, vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, -vec.x, vec.z, vec.y] )
    elif CONFIG['SWAP_AXIS'] == 'xz-y':
        if len(vec) == 3: return mathutils.Vector( [vec.x, vec.z, -vec.y] )
        elif len(vec) == 4: return mathutils.Quaternion( [ vec.w, vec.x, vec.z, -vec.y] )
    else:
        logging.warn( 'unknown swap axis mode %s', CONFIG['SWAP_AXIS'] )
        assert 0

def uid(ob):
    if ob.uid == 0:
        high = 0
        multires = 0
        for o in bpy.data.objects:
            if o.uid > high: high = o.uid
            if o.use_multires_lod: multires += 1
        high += 1 + (multires*10)
        if high < 100: high = 100   # start at 100
        ob.uid = high
    return ob.uid

def timer_diff_str(start):
    return "%0.2f" % (time.time()-start)

def find_bone_index( ob, arm, groupidx): # sometimes the groups are out of order, this finds the right index.
    if groupidx < len(ob.vertex_groups): # reported by Slacker
        vg = ob.vertex_groups[ groupidx ]
        j = 0
        for i,bone in enumerate(arm.pose.bones):
            if not bone.bone.use_deform and CONFIG['ONLY_DEFORMABLE_BONES']:
                j+=1 # if we skip bones we need to adjust the id
            if bone.name == vg.name:
                return i-j
    else:
        print('WARNING: object vertex groups not in sync with armature', ob, arm, groupidx)

def mesh_is_smooth( mesh ):
    for face in mesh.tessfaces:
        if face.use_smooth: return True

def find_uv_layer_index( uvname, material=None ):
    # This breaks if users have uv layers with same name with different indices over different objects
    idx = 0
    for mesh in bpy.data.meshes:
        if material is None or material.name in mesh.materials:
            if mesh.uv_textures:
                names = [ uv.name for uv in mesh.uv_textures ]
                if uvname in names:
                    idx = names.index( uvname )
                    break # should we check all objects using material and enforce the same index?
    return idx

def has_custom_property( a, name ):
    for prop in a.items():
        n,val = prop
        if n == name:
            return True

def is_strictly_simple_terrain( ob ):
    # A default plane, with simple-subsurf and displace modifier on Z
    if len(ob.data.vertices) != 4 and len(ob.data.tessfaces) != 1:
        return False
    elif len(ob.modifiers) < 2:
        return False
    elif ob.modifiers[0].type != 'SUBSURF' or ob.modifiers[1].type != 'DISPLACE':
        return False
    elif ob.modifiers[0].subdivision_type != 'SIMPLE':
        return False
    elif ob.modifiers[1].direction != 'Z':
        return False # disallow NORMAL and other modes
    else:
        return True

def get_image_textures( mat ):
    r = []
    for s in mat.texture_slots:
        if s and s.texture.type == 'IMAGE':
            r.append( s )
    return r

def objects_merge_materials(objs):
    """
    return a list that contains unique material objects
    """
    materials = set()
    for obj in objs:
        for mat in obj.data.materials:
            materials.add(mat)
    return materials

def indent( level, *args ):
    if not args:
        return '    ' * level
    else:
        a = ''
        for line in args:
            a += '    ' * level
            a += line
            a += '\n'
        return a

def gather_instances():
    instances = {}
    for ob in bpy.context.scene.objects:
        if ob.data and ob.data.users > 1:
            if ob.data not in instances:
                instances[ ob.data ] = []
            instances[ ob.data ].append( ob )
    return instances

def select_instances( context, name ):
    for ob in bpy.context.scene.objects:
        ob.select = False
    ob = bpy.context.scene.objects[ name ]
    if ob.data:
        inst = gather_instances()
        for ob in inst[ ob.data ]: ob.select = True
        bpy.context.scene.objects.active = ob

def select_group( context, name, options={} ):
    for ob in bpy.context.scene.objects:
        ob.select = False
    for grp in bpy.data.groups:
        if grp.name == name:
            # context.scene.objects.active = grp.objects
            # Note that the context is read-only. These values cannot be modified directly,
            # though they may be changed by running API functions or by using the data API.
            # So bpy.context.object = obj will raise an error. But bpy.context.scene.objects.active = obj
            # will work as expected. - http://wiki.blender.org/index.php?title=Dev:2.5/Py/API/Intro&useskin=monobook
            bpy.context.scene.objects.active = grp.objects[0]
            for ob in grp.objects:
                ob.select = True
        else:
            pass

def get_objects_using_materials( mats ):
    obs = []
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            for mat in ob.data.materials:
                if mat in mats:
                    if ob not in obs:
                        obs.append( ob )
                    break
    return obs

def get_materials_using_image( img ):
    mats = []
    for mat in bpy.data.materials:
        for slot in get_image_textures( mat ):
            if slot.texture.image == img:
                if mat not in mats:
                    mats.append( mat )
    return mats

def get_parent_matrix( ob, objects ):
    if not ob.parent:
        return mathutils.Matrix(((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)))   # Requiered for Blender SVN > 2.56
    else:
        if ob.parent in objects:
            return ob.parent.matrix_world.copy()
        else:
            return get_parent_matrix(ob.parent, objects)

def merge_group( group ):
    print('--------------- merge group ->', group )
    copies = []
    for ob in group.objects:
        if ob.type == 'MESH':
            print( '\t group member', ob.name )
            o2 = ob.copy(); copies.append( o2 )
            o2.data = o2.to_mesh(bpy.context.scene, True, "PREVIEW") # collaspe modifiers
            while o2.modifiers:
                o2.modifiers.remove( o2.modifiers[0] )
            bpy.context.scene.objects.link( o2 ) #; o2.select = True
    merged = merge( copies )
    merged.name = group.name
    merged.data.name = group.name
    return merged

def merge_objects( objects, name='_temp_', transform=None ):
    assert objects
    copies = []
    for ob in objects:
        ob.select = False
        if ob.type == 'MESH':
            o2 = ob.copy(); copies.append( o2 )
            o2.data = o2.to_mesh(bpy.context.scene, True, "PREVIEW") # collaspe modifiers
            while o2.modifiers:
                o2.modifiers.remove( o2.modifiers[0] )
            if transform:
                o2.matrix_world =  transform * o2.matrix_local
            bpy.context.scene.objects.link( o2 ) #; o2.select = True
    merged = merge( copies )
    merged.name = name
    merged.data.name = name
    return merged

def merge( objects ):
    print('MERGE', objects)
    for ob in bpy.context.selected_objects:
        ob.select = False
    for ob in objects:
        print('\t'+ob.name)
        ob.select = True
        assert not ob.library
    bpy.context.scene.objects.active = ob
    bpy.ops.object.join()
    return bpy.context.active_object

def get_merge_group( ob, prefix='merge' ):
    m = []
    for grp in ob.users_group:
        if grp.name.lower().startswith(prefix): m.append( grp )
    if len(m)==1:
        #if ob.data.users != 1:
        #    print( 'WARNING: an instance can not be in a merge group' )
        #    return
        return m[0]
    elif m:
        print('WARNING: an object can not be in two merge groups at the same time', ob)
        return

def wordwrap( txt ):
    r = ['']
    for word in txt.split(' '): # do not split on tabs
        word = word.replace('\t', ' '*3)
        r[-1] += word + ' '
        if len(r[-1]) > 90:
            r.append( '' )
    return r

def get_lights_by_type( T ):
    r = []
    for ob in bpy.context.scene.objects:
        if ob.type=='LAMP':
            if ob.data.type==T: r.append( ob )
    return r

invalid_chars = '\/:*?"<>|'

def clean_object_name(value):
    global invalid_chars
    for invalid_char in invalid_chars:
        value = value.replace(invalid_char, '_')
    value = value.replace(' ', '_')
    return value;

def clean_object_name_with_spaces(value):
    global invalid_chars
    for invalid_char in invalid_chars:
        value = value.replace(invalid_char, '_')
    return value;

def get_subcollision_meshes():
    ''' returns all collision meshes found in the scene '''
    r = []
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH' and ob.subcollision: r.append( ob )
    return r

def get_objects_with_subcollision():
    ''' returns objects that have active sub-collisions '''
    r = []
    for ob in bpy.context.scene.objects:
        if ob.type=='MESH' and ob.collision_mode not in ('NONE', 'PRIMITIVE'):
            r.append( ob )
    return r

def get_subcollisions(ob):
    prefix = '%s.' %ob.collision_mode
    r = []
    for child in ob.children:
        if child.subcollision and child.name.startswith( prefix ):
            r.append( child )
    return r

class IndentedWriter(object):
    """
    Can be used to write well formed documents.

    w = IndentedWriter()
    with w.word("hello").embed():
        w.indent().word("world").string("!!!").nl()
        with w.word("hello").embed():
            w.iline("schnaps")

    print(w.text)
    > hello {
        world "!!!"
        hello {
          schnaps
        }
      }



    """

    sym_stack = []
    text = ""
    embed_syms = None

    def __init__(self, indent = 0):
        for i in range(indent):
            sym_stack.append(None)

    def __enter__(self, **kwargs):
        begin_sym, end_sym, nl = self.embed_syms
        self.write(begin_sym)
        if nl:
            self.nl()
        self.sym_stack.append(end_sym)

    def __exit__(self, *kwargs):
        sym = self.sym_stack.pop()
        self.indent().write(sym).nl()

    def embed(self, begin_sym="{", end_sym="}", nl=True):
        self.embed_syms = (begin_sym, end_sym, nl)
        return self

    def string(self, text):
        self.write("\"")
        self.write(text)
        self.write("\"")
        return self

    def indent(self, plus=0):
        return self.write("    " * (len(self.sym_stack) + plus))

    def nl(self):
        self.write("\n")
        return self

    def write(self, text):
        self.text += text
        return self

    def word(self, text):
        return self.write(text).write(" ")

    def iwrite(self, text):
        return self.indent().write(text)

    def iword(self, text):
        return self.indent().word(text)

    def iline(self, text):
        return self.indent().line(text)

    def line(self, text):
        return self.write(text + "\n")

