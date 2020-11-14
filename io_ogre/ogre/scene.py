import bpy, mathutils, os, getpass, math
from os.path import join
from .. import util
from .. import config
from . import mesh
from . import skeleton
from ..report import Report
from ..util import *
from ..xml import *
from .mesh import *
from .material import *
from . import material
from .. import bl_info

def dot_scene(path, scene_name=None):
    """
    path: string - target path to save the scene file and related files to
    scene_name: string optional - the name of the scene file, defaults to the scene name of blender
    """
    if not scene_name:
        scene_name = bpy.context.scene.name
    scene_file = scene_name + '.scene'
    target_scene_file = join(path, scene_file)
    
    # Create target path if it does not exist
    if not os.path.exists(path):
        print("Creating Directory -", path)
        os.mkdir(path)

    print("Processing Scene: name:%s, path: %s"%(scene_name, path))
    prefix = scene_name

    # Nodes (objects) - gather because macros will change selection state
    objects = []
    linkedgroups = []
    invalidnamewarnings = []
    for ob in bpy.context.scene.objects:
        if ob.subcollision:
            continue
        if not util.should_export(ob):
            continue
        if config.get("SELONLY") and not ob.select_get():
            if ob.type == 'CAMERA' and config.get("FORCE_CAMERA"):
                pass
            elif ob.type == 'LAMP' and config.get("FORCE_LAMPS"):
                pass
            else:
                continue
        if ob.type == 'EMPTY' and ob.instance_collection and ob.instance_type == 'COLLECTION':
            linkedgroups.append(ob)
        else:
            # Gather data of invalid names. Don't bother user with warnings on names
            # that only get spaces converted to _, just do that automatically.
            cleanname = clean_object_name(ob.name)
            cleannamespaces = clean_object_name(ob.name, spaces = False)

            if cleanname != ob.name:
                if cleannamespaces != ob.name:
                    invalidnamewarnings.append(ob.name + " -> " + cleanname)
            objects.append(ob)

    # Print invalid obj names so user can go and fix them.
    if len(invalidnamewarnings) > 0:
        print ("[Warning]: Following object names have invalid characters for creating files. They will be automatically converted.")
        for namewarning in invalidnamewarnings:
            Report.warnings.append("Auto correcting object name: " + namewarning)
            print ("  - ", namewarning)

    # Linked groups - allows 3 levels of nested blender library linking
    temps = []
    for e in linkedgroups:
        grp = e.instance_collection
        subs = []
        for o in grp.objects:
            if o.type=='MESH':
                subs.append( o )     # TOP-LEVEL
            elif o.type == 'EMPTY' and o.instance_collection and o.instance_type == 'COLLECTION':
                ss = []     # LEVEL2
                for oo in o.instance_collection.objects:
                    if oo.type=='MESH':
                        ss.append( oo )
                    elif oo.type == 'EMPTY' and oo.instance_collection and oo.instance_type == 'COLLECTION':
                        sss = []    # LEVEL3
                        for ooo in oo.instance_collection.objects:
                            if ooo.type=='MESH':
                                sss.append( ooo )
                        if sss:
                            m = merge_objects( sss, name=oo.name, transform=oo.matrix_world )
                            subs.append( m )
                            temps.append( m )
                if ss:
                    m = merge_objects( ss, name=o.name, transform=o.matrix_world )
                    subs.append( m )
                    temps.append( m )
        if subs:
            m = merge_objects( subs, name=e.name, transform=e.matrix_world )
            objects.append( m )
            temps.append( m )

    # Track that we don't export same data multiple times
    exported_meshes = []

    # Find merge groups
    mgroups = []
    mobjects = []
    for ob in objects:
        group = get_merge_group( ob )
        if group:
            for member in group.objects:
                if member not in mobjects: mobjects.append( member )
            if group not in mgroups: mgroups.append( group )
    for rem in mobjects:
        if rem in objects:
            objects.remove( rem )
            exported_meshes.append(rem.data.name)

    for group in mgroups:
        merged = merge_group( group )
        objects.append( merged )
        temps.append( merged )

    # Gather roots because ogredotscene supports parents and children
    def _flatten( _c, _f ):
        if _c.parent in objects: _f.append( _c.parent )
        if _c.parent: _flatten( _c.parent, _f )
        else: _f.append( _c )

    roots = []
    meshes = []

    for ob in objects:
        flat = []
        _flatten( ob, flat )
        root = flat[-1]
        if root not in roots:
            roots.append(root)
        if ob.type=='MESH':
            meshes.append(ob)

    materials = []
    if config.get("MATERIALS"):
        print ("  Processing Materials")
        materials = util.objects_merge_materials(meshes)
        dot_materials(materials, path, separate_files=config.get('SEP_MATS'), prefix=prefix)

    doc = ogre_document(materials)

    mesh_collision_prims = {}
    mesh_collision_files = {}

    for root in roots:
        print('      - Exporting root node:', root.name)
        dot_scene_node_export(root, path = path, doc = doc,
            exported_meshes = exported_meshes,
            meshes = meshes,
            mesh_collision_prims = mesh_collision_prims,
            mesh_collision_files = mesh_collision_files,
            prefix = prefix,
            objects = objects,
            xmlparent = doc._scene_nodes
        )

    if config.get('SCENE'):
        data = doc.toprettyxml()
        with open(target_scene_file, 'wb') as fd:
            fd.write(bytes(data,'utf-8'))
        print('  Exported Ogre Scene:', target_scene_file)

    for ob in temps:
        #BQfix for 2.8 unable to find merged object in collection
        #bpy.context.scene.objects.unlink( ob )
        #bpy.context.collection.objects.unlink( ob )
        bpy.data.objects.remove(ob)


class _WrapLogic(object):
    SwapName = { 'frame_property' : 'animation' } # custom name hacks

    def __init__(self, node):
        self.node = node
        self.name = node.name
        self.type = node.type

    def widget(self, layout):
        box = layout.box()
        row = box.row()
        row.label( text=self.type )
        row.separator()
        row.prop( self.node, 'name', text='' )
        if self.type in self.TYPES:
            for name in self.TYPES[ self.type ]:
                if name in self.SwapName:
                    box.prop( self.node, name, text=self.SwapName[name] )
                else:
                    box.prop( self.node, name )

    def xml( self, doc ):
        g = doc.createElement( self.LogicType )
        g.setAttribute('name', self.name)
        g.setAttribute('type', self.type)
        if self.type in self.TYPES:
            for name in self.TYPES[ self.type ]:
                attr = getattr( self.node, name )
                if name in self.SwapName: name = self.SwapName[name]
                a = doc.createElement( 'component' )
                g.appendChild(a)
                a.setAttribute('name', name)
                if attr is None: a.setAttribute('type', 'POINTER' )
                else: a.setAttribute('type', type(attr).__name__)

                if type(attr) in (float, int, str, bool): a.setAttribute('value', str(attr))
                elif not attr: a.setAttribute('value', '')        # None case
                elif hasattr(attr,'filepath'): a.setAttribute('value', attr.filepath)
                elif hasattr(attr,'name'): a.setAttribute('value', attr.name)
                elif hasattr(attr,'x') and hasattr(attr,'y') and hasattr(attr,'z'):
                    a.setAttribute('value', '%s %s %s' %(attr.x, attr.y, attr.z))
                else:
                    print('ERROR: unknown type', attr)
        return g

class WrapSensor( _WrapLogic ):
    LogicType = 'sensor'
    TYPES = {
        'COLLISION': ['property'],
        'MESSAGE' : ['subject'],
        'NEAR' : ['property', 'distance', 'reset_distance'],
        'RADAR'  :  ['property', 'axis', 'angle', 'distance' ],
        'RAY'  :  ['ray_type', 'property', 'material', 'axis', 'range', 'use_x_ray'],
        'TOUCH'  :  ['material'],
    }

class WrapActuator( _WrapLogic ):
    LogicType = 'actuator'
    TYPES = {
        'CAMERA'  :  ['object', 'height', 'min', 'max', 'axis'],
        'CONSTRAINT'  :  ['mode', 'limit', 'limit_min', 'limit_max', 'damping'],
        'MESSAGE' : ['to_property', 'subject', 'body_message'],        #skipping body_type
        'OBJECT'  :  'damping derivate_coefficient force force_max_x force_max_y force_max_z force_min_x force_min_y force_min_z integral_coefficient linear_velocity mode offset_location offset_rotation proportional_coefficient reference_object torque use_local_location use_local_rotation use_local_torque use_servo_limit_x use_servo_limit_y use_servo_limit_z'.split(),
        'SOUND'  :  'cone_inner_angle_3d cone_outer_angle_3d cone_outer_gain_3d distance_3d_max distance_3d_reference gain_3d_max gain_3d_min mode pitch rolloff_factor_3d sound use_sound_3d volume'.split(),        # note .sound contains .filepath
        'VISIBILITY'  :  'apply_to_children use_occlusion use_visible'.split(),
        'SHAPE_ACTION'  :  'frame_blend_in frame_end frame_property frame_start mode property use_continue_last_frame'.split(),
        'EDIT_OBJECT'  :  'dynamic_operation linear_velocity mass mesh mode object time track_object use_3d_tracking use_local_angular_velocity use_local_linear_velocity use_replace_display_mesh use_replace_physics_mesh'.split(),
    }

def _property_helper(doc, user, propname, propvalue):
    prop = doc.createElement('property')
    user.appendChild(prop)
    prop.setAttribute('name', propname)
    prop.setAttribute('data', str(propvalue))
    prop.setAttribute('type', type(propvalue).__name__)

def _mesh_entity_helper(doc, ob, o):
    user = doc.createElement('userData')
    o.appendChild(user)

    """
    nope - no more ".game" in 2.80
    
    # # extended format - BGE Physics ##
    _property_helper(doc, user, 'mass', ob.game.mass)
    _property_helper(doc, user, 'mass_radius', ob.game.radius)
    _property_helper(doc, user, 'physics_type', ob.game.physics_type)
    _property_helper(doc, user, 'actor', ob.game.use_actor)
    _property_helper(doc, user, 'ghost', ob.game.use_ghost)
    _property_helper(doc, user, 'velocity_min', ob.game.velocity_min)
    _property_helper(doc, user, 'velocity_max', ob.game.velocity_max)
    _property_helper(doc, user, 'lock_trans_x', ob.game.lock_location_x)
    _property_helper(doc, user, 'lock_trans_y', ob.game.lock_location_y)
    _property_helper(doc, user, 'lock_trans_z', ob.game.lock_location_z)
    _property_helper(doc, user, 'lock_rot_x', ob.game.lock_rotation_x)
    _property_helper(doc, user, 'lock_rot_y', ob.game.lock_rotation_y)
    _property_helper(doc, user, 'lock_rot_z', ob.game.lock_rotation_z)
    _property_helper(doc, user, 'anisotropic_friction', ob.game.use_anisotropic_friction)
    x, y, z = ob.game.friction_coefficients
    _property_helper(doc, user, 'friction_x', x)
    _property_helper(doc, user, 'friction_y', y)
    _property_helper(doc, user, 'friction_z', z)
    _property_helper(doc, user, 'damping_trans', ob.game.damping)
    _property_helper(doc, user, 'damping_rot', ob.game.rotation_damping)
    _property_helper(doc, user, 'inertia_tensor', ob.game.form_factor)
    """

    mesh = ob.data
    # custom user props
    for prop in mesh.items():
        propname, propvalue = prop
        if not propname.startswith('_'):
            _property_helper(doc, user, propname, propvalue)

def _ogre_node_helper( doc, ob, prefix='', pos=None, rot=None, scl=None ):
    mat = ob.matrix_local

    o = doc.createElement('node')
    o.setAttribute('name',prefix+ob.name)
    p = doc.createElement('position')
    q = doc.createElement('rotation')       #('quaternion')
    s = doc.createElement('scale')
    for n in (p,q,s):
        o.appendChild(n)

    if pos:
        v = swap(pos)
    else:
        v = swap( mat.to_translation() )
    p.setAttribute('x', '%6f'%v.x)
    p.setAttribute('y', '%6f'%v.y)
    p.setAttribute('z', '%6f'%v.z)

    if rot:
        v = swap(rot)
    else:
        v = swap( mat.to_quaternion() )
    q.setAttribute('qx', '%6f'%v.x)
    q.setAttribute('qy', '%6f'%v.y)
    q.setAttribute('qz', '%6f'%v.z)
    q.setAttribute('qw','%6f'%v.w)

    if scl:        # this should not be used
        v = swap(scl)
        x=abs(v.x); y=abs(v.y); z=abs(v.z)
        s.setAttribute('x', '%6f'%x)
        s.setAttribute('y', '%6f'%y)
        s.setAttribute('z', '%6f'%z)
    else:        # scale is different in Ogre from blender - rotation is removed
        ri = mat.to_quaternion().inverted().to_matrix()
        scale = ri.to_4x4() @ mat
        v = swap( scale.to_scale() )
        x=abs(v.x); y=abs(v.y); z=abs(v.z)
        s.setAttribute('x', '%6f'%x)
        s.setAttribute('y', '%6f'%y)
        s.setAttribute('z', '%6f'%z)
    return o

def ogre_document(materials):
    now = time.time()
    doc = RDocument()
    scn = doc.createElement('scene')
    doc.appendChild( scn )
    time_format = "%a, %d %b %Y %H:%M:%S +0000"
    doc.addComment('exporter: blender2ogre ' + ".".join(str(i) for i in bl_info["version"]))
    doc.addComment('export_time: ' + time.strftime(time_format, time.gmtime(now)))
    scn.setAttribute('formatVersion', '1.1')
    bscn = bpy.context.scene

    if '_previous_export_time_' in bscn.keys():
        doc.addComment('previous_export_time: ' + time.strftime(time_format, time.gmtime(bscn['_previous_export_time_'])))

    bscn[ '_previous_export_time_' ] = now
    scn.setAttribute('author', getpass.getuser())

    nodes = doc.createElement('nodes')
    doc._scene_nodes = nodes
    extern = doc.createElement('externals')
    environ = doc.createElement('environment')
    for n in (nodes,extern,environ):
        scn.appendChild( n )

    # Extern files
    for mat in materials:
        item = doc.createElement('item')
        extern.appendChild( item )
        item.setAttribute('type','material')
        a = doc.createElement('file')
        item.appendChild( a )
        a.setAttribute('name', '%s.material'%material.material_name(mat))

    # Environ settings
    world = bpy.context.scene.world
    if world: # multiple scenes - other scenes may not have a world
        _c = [ ('colourBackground', world.color)]
        for ctag, color in _c:
            a = doc.createElement(ctag); environ.appendChild( a )
            a.setAttribute('r', '%s'%color.r)
            a.setAttribute('g', '%s'%color.g)
            a.setAttribute('b', '%s'%color.b)

    if world and world.mist_settings.use_mist:
        a = doc.createElement('fog'); environ.appendChild( a )
        a.setAttribute('linearStart', '%s'%world.mist_settings.start )
        mist_falloff = world.mist_settings.falloff
        if mist_falloff == 'QUADRATIC': a.setAttribute('mode', 'exp')    # on DTD spec (none | exp | exp2 | linear)
        elif mist_falloff == 'LINEAR': a.setAttribute('mode', 'linear')
        else: a.setAttribute('mode', 'exp2')
        #a.setAttribute('mode', world.mist_settings.falloff.lower() )    # not on DTD spec
        a.setAttribute('linearEnd', '%s' %(world.mist_settings.start+world.mist_settings.depth))
        a.setAttribute('expDensity', world.mist_settings.intensity)
        
        c = doc.createElement('colourDiffuse'); a.appendChild( c )
        c.setAttribute('r', '%s'%color.r)
        c.setAttribute('g', '%s'%color.g)
        c.setAttribute('b', '%s'%color.b)

    return doc

# Recursive Node export
def dot_scene_node_export( ob, path, doc=None, rex=None,
        exported_meshes=[], meshes=[], mesh_collision_prims={},
        mesh_collision_files={}, prefix='', objects=[], xmlparent=None ):

    o = _ogre_node_helper( doc, ob )
    xmlparent.appendChild(o)

    # Custom user props
    if len(ob.items()) > 0:
        user = doc.createElement('userData')
        o.appendChild(user)

    for prop in ob.items():
        propname, propvalue = prop
        if not propname.startswith('_'):
            _property_helper(doc, user, propname, propvalue)

    if ob.type == 'MESH':
        # ob.data.tessfaces is empty. always until the following call
        ob.data.update()
        ob.data.calc_loop_triangles()
        # if it has no faces at all, the object itself will not be exported, BUT 
        # it might have children
        print("Vertices: ", len(ob.data.vertices))
        print("Loop triangles: ", len(ob.data.loop_triangles))

    if ob.type == 'MESH' and len(ob.data.loop_triangles):
        collisionFile = None
        collisionPrim = None
        if ob.data.name in mesh_collision_prims:
            collisionPrim = mesh_collision_prims[ ob.data.name ]
        if ob.data.name in mesh_collision_files:
            collisionFile = mesh_collision_files[ ob.data.name ]

        e = doc.createElement('entity')
        o.appendChild(e); e.setAttribute('name', ob.name)
        prefix = ''
        e.setAttribute('meshFile', '%s%s.mesh' %(prefix,clean_object_name(ob.data.name)) )

        if not collisionPrim and not collisionFile:
                for child in ob.children:
                    if child.subcollision and child.name.startswith('DECIMATE'):
                        collisionFile = '%s_collision_%s.mesh' %(prefix,ob.data.name)
                        break
                if collisionFile:
                    mesh_collision_files[ ob.data.name ] = collisionFile
                    mesh.dot_mesh(child, target_path, force_name='%s_collision_%s' % (prefix,ob.data.name) )
                    skeleton.dot_skeleton(child, target_path)

        if collisionPrim:
            e.setAttribute('collisionPrim', collisionPrim )
        elif collisionFile:
            e.setAttribute('collisionFile', collisionFile )

        _mesh_entity_helper( doc, ob, e )

        # export mesh.xml file of this object
        if config.get('MESH') and ob.data.name not in exported_meshes:
            exists = os.path.isfile( join( path, '%s.mesh' % ob.data.name ) )
            overwrite = not exists or (exists and config.get("MESH_OVERWRITE"))
            tangents = int(config.get("generateTangents"))
            mesh.dot_mesh(ob, path, overwrite=overwrite, tangents=tangents)
            skeleton.dot_skeleton(ob, path, overwrite=overwrite)    
            exported_meshes.append( ob.data.name )

        # Deal with Array modifier
        vecs = [ ob.matrix_world.to_translation() ]
        for mod in ob.modifiers:
            if mod.type == 'ARRAY':
                if mod.fit_type != 'FIXED_COUNT':
                    print( 'WARNING: unsupport array-modifier type->', mod.fit_type )
                    continue
                if not mod.use_constant_offset:
                    print( 'WARNING: unsupport array-modifier mode, must be "constant offset" type' )
                    continue
                else:
                    #v = ob.matrix_world.to_translation()
                    newvecs = []
                    for prev in vecs:
                        for i in range( mod.count-1 ):
                            v = prev + mod.constant_offset_displace
                            newvecs.append( v )
                            ao = _ogre_node_helper( doc, ob, prefix='_array_%s_'%len(vecs+newvecs), pos=v )
                            xmlparent.appendChild(ao)

                            e = doc.createElement('entity')
                            ao.appendChild(e); e.setAttribute('name', ob.data.name)
                            e.setAttribute('meshFile', '%s.mesh' % clean_object_name(ob.data.name))

                            if collisionPrim: e.setAttribute('collisionPrim', collisionPrim )
                            elif collisionFile: e.setAttribute('collisionFile', collisionFile )
                    vecs += newvecs

    elif ob.type == 'CAMERA':
        Report.cameras.append( ob.name )
        c = doc.createElement('camera')
        o.appendChild(c); c.setAttribute('name', ob.data.name)
        aspx = bpy.context.scene.render.pixel_aspect_x
        aspy = bpy.context.scene.render.pixel_aspect_y
        sx = bpy.context.scene.render.resolution_x
        sy = bpy.context.scene.render.resolution_y
        if ob.data.type == "PERSP":
            fovY = 0.0
            if (sx*aspx > sy*aspy):
                fovY = 2*math.atan(sy*aspy*16.0/(ob.data.lens*sx*aspx))
            else:
                fovY = 2*math.atan(16.0/ob.data.lens)
            # fov in radians - like OgreMax - requested by cyrfer
            fov = math.radians( fovY*180.0/math.pi )
            c.setAttribute('projectionType', "perspective")
            c.setAttribute('fov', '%s'%fov)
        else: # ob.data.type == "ORTHO":
            c.setAttribute('projectionType', "orthographic")
            c.setAttribute('orthoScale', '%s'%ob.data.ortho_scale)
        a = doc.createElement('clipping'); c.appendChild( a )
        a.setAttribute('near', '%s' %ob.data.clip_start)    # requested by cyrfer
        a.setAttribute('far', '%s' %ob.data.clip_end)

    elif ob.type == 'LAMP' and ob.data.type in 'POINT SPOT SUN'.split():
        Report.lights.append( ob.name )
        l = doc.createElement('light')
        o.appendChild(l)

        if ob.data.type == 'POINT':
            l.setAttribute('type', 'point')
        elif ob.data.type == 'SPOT':
            l.setAttribute('type', 'spot')
        elif ob.data.type == 'SUN':
            l.setAttribute('type', 'directional')

        l.setAttribute('name', ob.name )
        l.setAttribute('powerScale', str(ob.data.energy))

        if ob.data.use_diffuse:
            a = doc.createElement('colourDiffuse'); l.appendChild( a )
            a.setAttribute('r', '%s'%ob.data.color.r)
            a.setAttribute('g', '%s'%ob.data.color.g)
            a.setAttribute('b', '%s'%ob.data.color.b)

        if ob.data.use_specular:
            a = doc.createElement('colourSpecular'); l.appendChild( a )
            a.setAttribute('r', '%s'%ob.data.color.r)
            a.setAttribute('g', '%s'%ob.data.color.g)
            a.setAttribute('b', '%s'%ob.data.color.b)

        if ob.data.type == 'SPOT':
            a = doc.createElement('lightRange')
            l.appendChild(a)
            a.setAttribute('inner',str( ob.data.spot_size*(1.0-ob.data.spot_blend) ))
            a.setAttribute('outer',str(ob.data.spot_size))
            a.setAttribute('falloff','1.0')

        a = doc.createElement('lightAttenuation'); l.appendChild( a )
        a.setAttribute('range', '5000' )            # is this an Ogre constant?
        a.setAttribute('constant', '1.0')        # TODO support quadratic light
        a.setAttribute('linear', '%s'%(1.0/ob.data.distance))
        a.setAttribute('quadratic', '0.0')

    for child in ob.children:
        dot_scene_node_export( child,
            path, doc = doc, rex = rex,
            exported_meshes = exported_meshes,
            meshes = meshes,
            mesh_collision_prims = mesh_collision_prims,
            mesh_collision_files = mesh_collision_files,
            prefix = prefix,
            objects=objects,
            xmlparent=o
        )

