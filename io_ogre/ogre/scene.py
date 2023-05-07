
# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    # ...so we need to reload our submodule(s) using importlib
    import importlib
    if "material" in locals():
        importlib.reload(material)
    if "materialv2json" in locals():
        importlib.reload(materialv2json)
    if "node_anim" in locals():
        importlib.reload(node_anim)
    if "mesh" in locals():
        importlib.reload(mesh)
    if "skeleton" in locals():
        importlib.reload(skeleton)
    if "config" in locals():
        importlib.reload(config)
    if "util" in locals():
        importlib.reload(util)
    if "report" in locals():
        importlib.reload(report)
    if "xml" in locals():
        importlib.reload(xml)

# This is only relevant on first run, on later reloads those modules
# are already in locals() and those statements do not do anything.
import bpy, mathutils, os, getpass, math
from os.path import join
from . import material
from . import materialv2json
from . import node_anim
from . import mesh
from . import skeleton
from .. import bl_info
from .. import config
from .. import util
from ..report import Report
from ..util import *
from ..xml import *
from .material import *
from .materialv2json import *
from .mesh import *

logger = logging.getLogger('scene')

# Called by io_ogre/ui/exporter.py to start exporting the scene
def dot_scene(path, scene_name=None):
    """
    path: string - target path to save the scene file and related files to
    scene_name: string optional - the name of the scene file, defaults to the scene name of blender
    """
    if not scene_name:
        scene_name = bpy.context.scene.name
    scene_file = scene_name + '.scene'
    target_scene_file = join(path, scene_file)

    start = time.time()

    # Create target path if it does not exist
    if not os.path.exists(path):
        logger.info("Creating Directory: %s" % path)
        os.mkdir(path)

    logger.info("* Processing Scene: %s, path: %s" % (scene_name, path))
    prefix = scene_name

    # If an object has an animation, then we want to export the position at the first frame (with the object at rest)
    # Otherwise the objects position will be at an arbitrary place if current frame is different from frame_start
    frame_start = bpy.context.scene.frame_start
    frame_current = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(frame_start)

    # Nodes (objects) - gather because macros will change selection state
    objects = []
    linkedgroups = []
    invalidnamewarnings = []
    for ob in bpy.context.scene.objects:
        if ob.subcollision:
            continue
        if not (config.get("EXPORT_HIDDEN") or ob in bpy.context.visible_objects):
            continue
        if config.get("SELECTED_ONLY") and not ob.select_get():
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
            logger.debug("ABABA %s" % ob.name)
            if cleanname != ob.name:
                if cleannamespaces != ob.name:
                    invalidnamewarnings.append(ob.name + " -> " + cleanname)
            objects.append(ob)

    # Print invalid obj names so user can go and fix them.
    if len(invalidnamewarnings) > 0:
        logger.warning("The following object names have invalid characters for creating files. They will be automatically converted.")
        for namewarning in invalidnamewarnings:
            Report.warnings.append('Auto corrected Object name: "%s"' % namewarning)
            logger.warning("+ - %s" % namewarning)

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
    exported_armatures = []

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
            exported_meshes.append( rem.data.name )

    for group in mgroups:
        merged = merge_group( group )
        objects.append( merged )
        temps.append( merged )

        # If user has set an offset for the dupli_group, then use that to set the origin of the merged objects
        if group.instance_offset != mathutils.Vector((0.0, 0.0, 0.0)):
            logger.info("Change origin of merged object %s to: %s" % ( merged.name, group.instance_offset ))
            
            # Use the 3D cursor to set the object origin
            merged.select_set(True)
            saved_location = bpy.context.scene.cursor.location  # Save 3D cursor location
            bpy.context.scene.cursor.location = group.instance_offset
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')     # Set the origin on the current object to the 3D cursor location
            bpy.context.scene.cursor.location = saved_location  # Set 3D cursor location back to the stored location

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
        logger.info("* Processing Materials")
        materials = util.objects_merge_materials(meshes)

        converter_type= detect_converter_type()
        if converter_type == "OgreMeshTool":
            dot_materialsv2json(materials, path, separate_files=config.get('SEPARATE_MATERIALS'), prefix=prefix)
        elif converter_type == "OgreXMLConverter":
            dot_materials(materials, path, separate_files=config.get('SEPARATE_MATERIALS'), prefix=prefix)
        else: # Unkown converter type, error
            logger.error("Unkown converter type '{}', will not generate materials".format(converter_type))
            Reports.error.append("Unkown converter type '{}', will not generate materials".format(converter_type))

    doc = ogre_document(materials)

    mesh_collision_prims = {}
    mesh_collision_files = {}

    # Export the objects in the scene
    for root in roots:
        logger.info("* Exporting root node: %s " % root.name)
        dot_scene_node_export(root, path = path, doc = doc,
            exported_meshes = exported_meshes,
            meshes = meshes,
            mesh_collision_prims = mesh_collision_prims,
            mesh_collision_files = mesh_collision_files,
            exported_armatures = exported_armatures,
            prefix = prefix,
            objects = objects,
            xmlparent = doc._scene_nodes
        )

    # Create the .scene file
    if config.get('SCENE'):
        data = doc.toprettyxml()
        try:
            with open(target_scene_file, 'wb') as fd:
                fd.write(bytes(data,'utf-8'))
            logger.info("- Exported Ogre Scene: %s " % target_scene_file)
        except Exception as e:
            logger.error("Unable to create scene file: %s" % target_scene_file)
            logger.error(e)
            Report.errors.append("Unable to create scene file: %s" % target_scene_file)

    # Remove temporary objects/meshes
    for ob in temps:
        logger.debug("Removing temporary mesh: %s" % ob.data.name)
        bpy.data.meshes.remove(ob.data)
        #BQfix for 2.8 unable to find merged object in collection
        #bpy.context.collection.objects.unlink( ob )
        #bpy.data.objects.remove(ob, do_unlink=True)

    # Restore the scene previous frame position
    bpy.context.scene.frame_set(frame_current)

    logger.info('- Done at %s seconds' % util.timer_diff_str(start))

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
                    logger.error('Unknown type: %s' % attr)
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

def _mesh_instance_helper(e, ob, type):
    group = get_merge_group( ob, type )
    
    # The 'static' / 'instanced' attribute indicates that the mesh will be instanced with either static geometry or instancing
    # The static geometry / instancing manager name is given by the group: (static | instancing).MyGroup
    if group != None:
        e.setAttribute( type, group.name[len(type + "."):] )

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

    # Get the object transform matrix
    mat = ob.matrix_local

    o = doc.createElement('node')
    o.setAttribute('name', prefix + ob.name)

    if pos:
        v = swap(pos)
    else:
        v = swap( mat.to_translation() )
    p = doc.createElement('position')
    p.setAttribute('x', '%6f' % v.x)
    p.setAttribute('y', '%6f' % v.y)
    p.setAttribute('z', '%6f' % v.z)
    o.appendChild(p)

    if rot:
        v = swap(rot)
    else:
        v = swap( mat.to_quaternion() )
    q = doc.createElement('rotation')   #('quaternion')
    q.setAttribute('qx', '%6f' % v.x)
    q.setAttribute('qy', '%6f' % v.y)
    q.setAttribute('qz', '%6f' % v.z)
    q.setAttribute('qw', '%6f' % v.w)
    o.appendChild(q)

    if scl:     # this should not be used
        v = swap(scl)
        x=abs(v.x); y=abs(v.y); z=abs(v.z)
    else:       # scale is different in Ogre from blender - rotation is removed
        ri = mat.to_quaternion().inverted().to_matrix()
        scale = ri.to_4x4() @ mat
        v = swap( scale.to_scale() )
        x=abs(v.x); y=abs(v.y); z=abs(v.z)
    s = doc.createElement('scale')
    s.setAttribute('x', '%6f' % x)
    s.setAttribute('y', '%6f' % y)
    s.setAttribute('z', '%6f' % z)
    o.appendChild(s)

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
        if mat is None: continue
        item = doc.createElement('item')
        extern.appendChild( item )
        item.setAttribute('type', 'material')
        a = doc.createElement('file')
        item.appendChild( a )
        a.setAttribute('name', '%s.material'%material.material_name(mat))

    # Environ settings
    world = bpy.context.scene.world
    if world: # multiple scenes - other scenes may not have a world
        _c = [ ('colourBackground', world.color)]
        for ctag, color in _c:
            a = doc.createElement(ctag); environ.appendChild( a )
            a.setAttribute('r', '%3f' % color.r)
            a.setAttribute('g', '%3f' % color.g)
            a.setAttribute('b', '%3f' % color.b)

    if world and world.mist_settings.use_mist:
        a = doc.createElement('fog'); environ.appendChild( a )
        a.setAttribute('linearStart', '%6f' % world.mist_settings.start )
        mist_falloff = world.mist_settings.falloff
        if mist_falloff == 'QUADRATIC': a.setAttribute('mode', 'exp')    # on DTD spec (none | exp | exp2 | linear)
        elif mist_falloff == 'LINEAR': a.setAttribute('mode', 'linear')
        else: a.setAttribute('mode', 'exp2')
        #a.setAttribute('mode', world.mist_settings.falloff.lower() )    # not on DTD spec
        a.setAttribute('linearEnd', '%6f' % (world.mist_settings.start + world.mist_settings.depth))
        a.setAttribute('expDensity', world.mist_settings.intensity)

        c = doc.createElement('colourDiffuse'); a.appendChild( c )
        c.setAttribute('r', '%3f' % color.r)
        c.setAttribute('g', '%3f' % color.g)
        c.setAttribute('b', '%3f' % color.b)

    return doc

# Recursive Node export
def dot_scene_node_export( ob, path, doc=None, rex=None,
        exported_meshes=[], meshes=[], mesh_collision_prims={}, mesh_collision_files={},
        exported_armatures=[], prefix='', objects=[], xmlparent=None ):

    o = _ogre_node_helper( doc, ob )
    xmlparent.appendChild(o)

    # if config.get('EXPORT_USER'):
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
        e.setAttribute('meshFile', '%s%s.mesh' % (prefix, clean_object_name(ob.data.name)) )
        
        # Set the instancing attribute if the object belongs to the correct group
        _mesh_instance_helper(e, ob, "static")
        _mesh_instance_helper(e, ob, "instanced")

        if not collisionPrim and not collisionFile:
            for child in ob.children:
                if child.subcollision and child.name.startswith('DECIMATE'):
                    collisionFile = '%s_collision_%s.mesh' % (prefix, ob.data.name)
                    break
            if collisionFile:
                mesh_collision_files[ ob.data.name ] = collisionFile
                mesh.dot_mesh(child, path, force_name='%s_collision_%s' % (prefix, ob.data.name) )
                skeleton.dot_skeleton(child, path)

        if collisionPrim:
            e.setAttribute('collisionPrim', collisionPrim )
        elif collisionFile:
            e.setAttribute('collisionFile', collisionFile )

        #if config.get('EXPORT_USER'):
        _mesh_entity_helper( doc, ob, e )

        # export mesh.xml file of this object
        if config.get('MESH') and ob.data.name not in exported_meshes:
            exists = os.path.isfile( join( path, '%s.mesh' % ob.data.name ) )
            overwrite = not exists or (exists and config.get("MESH_OVERWRITE"))
            tangents = int(config.get("GENERATE_TANGENTS"))
            mesh.dot_mesh(ob, path, overwrite=overwrite, tangents=tangents)
            exported_meshes.append( ob.data.name )
            skeleton.dot_skeleton(ob, path, overwrite=overwrite, exported_armatures=exported_armatures)

        # Deal with Array modifier
        vecs = [ ob.matrix_world.to_translation() ]
        for mod in ob.modifiers:
            if config.get("ARRAY") == True and mod.type == 'ARRAY':
                if mod.fit_type != 'FIXED_COUNT':
                    logger.warning("<%s> Unsupported array-modifier type: %s, only 'Fixed Count' is supported" % (ob.name, mod.fit_type))
                    Report.warnings.append("Object \"%s\" has unsupported array-modifier type: %s, only 'Fixed Count' is supported" % (ob.name, mod.fit_type))
                    continue
                if not mod.use_constant_offset:
                    logger.warning("<%s> Unsupported array-modifier mode, must be of 'Constant Offset' type" % ob.name)
                    Report.warnings.append("Object \"%s\" has unsupported array-modifier mode, must be of 'Constant Offset' type" % ob.name)
                    continue
                else:
                    newvecs = []
                    for prev in vecs:
                        for i in range( mod.count - 1 ):
                            count = len(vecs + newvecs)
                            
                            v = prev + (i + 1) * mod.constant_offset_displace
                            
                            newvecs.append( v )
                            ao = _ogre_node_helper( doc, ob, prefix='_array_%s_' % count, pos=v )
                            xmlparent.appendChild(ao)

                            e = doc.createElement('entity')
                            ao.appendChild(e)
                            e.setAttribute('name', '_array_%s_%s' % (count, ob.data.name))
                            e.setAttribute('meshFile', '%s.mesh' % clean_object_name(ob.data.name))

                            # Set the instancing attribute if the object belongs to the correct group
                            _mesh_instance_helper(e, ob, "static")
                            _mesh_instance_helper(e, ob, "instanced")

                            if collisionPrim: e.setAttribute('collisionPrim', collisionPrim )
                            elif collisionFile: e.setAttribute('collisionFile', collisionFile )
                    vecs += newvecs

        # Deal with Particle Systems
        z_rot = mathutils.Quaternion((0.0, 0.0, 1.0), math.radians(90.0))
        
        degp = bpy.context.evaluated_depsgraph_get()
        particle_systems = ob.evaluated_get(degp).particle_systems

        for partsys in particle_systems:
            if partsys.settings.type == 'HAIR' and partsys.settings.render_type == 'OBJECT':
                index = 0
                for particle in partsys.particles:
                    dupob = partsys.settings.instance_object
                    ao = _ogre_node_helper( doc, dupob, prefix='%s_particle_%s_' % (clean_object_name(ob.data.name), index), pos=particle.hair_keys[0].co, rot=(particle.rotation * z_rot), scl=(dupob.scale * particle.size) )
                    o.appendChild(ao)

                    e = doc.createElement('entity')
                    ao.appendChild(e); e.setAttribute('name', ('%s_particle_%s_%s' % (clean_object_name(ob.data.name), index, clean_object_name(dupob.data.name))))
                    e.setAttribute('meshFile', '%s.mesh' % clean_object_name(dupob.data.name))
                    
                    # Set the instancing attribute if the object belongs to the correct group
                    _mesh_instance_helper(e, dupob, "static")
                    _mesh_instance_helper(e, dupob, "instanced")
                    
                    index += 1
            else:
                logger.warn("<%s> Particle System %s is not supported for export (should be of type: 'Hair' and render_type: 'Object')" % (ob.name, partsys.name))
                Report.warnings.append("Object \"%s\" has Particle System: \"%s\" not supported for export (should be of type: 'Hair' and render_type: 'Object')" % (ob.name, partsys.name))

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
                fovY = 2 * math.atan(sy * aspy * 16.0 / (ob.data.lens * sx * aspx))
            else:
                fovY = 2 * math.atan(16.0 / ob.data.lens)
            # fov in radians - like OgreMax - requested by cyrfer
            fov = math.radians( fovY * 180.0 / math.pi )
            c.setAttribute('projectionType', "perspective")
            c.setAttribute('fov', '%6f' % fov)
        else: # ob.data.type == "ORTHO":
            c.setAttribute('projectionType', "orthographic")
            c.setAttribute('orthoScale', '%6f' % ob.data.ortho_scale)
        a = doc.createElement('clipping'); c.appendChild( a )
        a.setAttribute('near', '%6f' % ob.data.clip_start)    # requested by cyrfer
        a.setAttribute('far', '%6f' % ob.data.clip_end)

    elif ob.type == 'LIGHT' and ob.data.type in 'POINT SPOT SUN'.split():
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
        
        if (bpy.app.version[0] == 2 and bpy.app.version[1] >= 93) or (bpy.app.version[0] >= 3):
            a = doc.createElement('colourDiffuse'); l.appendChild(a)
            a.setAttribute('r', '%3f' % (ob.data.color.r * ob.data.diffuse_factor))
            a.setAttribute('g', '%3f' % (ob.data.color.g * ob.data.diffuse_factor))
            a.setAttribute('b', '%3f' % (ob.data.color.b * ob.data.diffuse_factor))

        else:
            a = doc.createElement('colourDiffuse'); l.appendChild(a)
            a.setAttribute('r', '%3f' % ob.data.color.r)
            a.setAttribute('g', '%3f' % ob.data.color.g)
            a.setAttribute('b', '%3f' % ob.data.color.b)

        if ob.data.specular_factor > 0:
            a = doc.createElement('colourSpecular'); l.appendChild(a)
            a.setAttribute('r', '%3f' % (ob.data.color.r * ob.data.specular_factor))
            a.setAttribute('g', '%3f' % (ob.data.color.g * ob.data.specular_factor))
            a.setAttribute('b', '%3f' % (ob.data.color.b * ob.data.specular_factor))

        if ob.data.type == 'SPOT':
            a = doc.createElement('lightRange')
            l.appendChild(a)
            a.setAttribute('inner',str( ob.data.spot_size * (1.0 - ob.data.spot_blend)))
            a.setAttribute('outer',str(ob.data.spot_size))
            a.setAttribute('falloff','1.0')

        a = doc.createElement('lightAttenuation'); l.appendChild( a )
        a.setAttribute('range', '5000' )        # is this an Ogre constant?
        a.setAttribute('constant', '1.0')       # TODO support quadratic light
        a.setAttribute('linear', '%6f' % (1.0 / ob.data.distance))
        a.setAttribute('quadratic', '0.0')

    # Node Animation
    if config.get('NODE_ANIMATION'):
        node_anim.dot_nodeanim(ob, doc, o)

    for child in ob.children:
        dot_scene_node_export( child,
            path, doc = doc, rex = rex,
            exported_meshes = exported_meshes,
            meshes = meshes,
            mesh_collision_prims = mesh_collision_prims,
            mesh_collision_files = mesh_collision_files,
            exported_armatures = exported_armatures,
            prefix = prefix,
            objects=objects,
            xmlparent=o
        )
