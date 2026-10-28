import os, time, logging
import bmesh
import numpy as np

from ..report import Report
from ..util import *
from ..xml import *
from .. import util, config
from .material import *
from .skeleton import Skeleton

logger = logging.getLogger('mesh')

# Material referenced by meshes that have no material slots at all. Ogre's
# serializers reject an empty material name, so point at the built-in material
# instead. Applications can override it at runtime.
BASE_WHITE = 'BaseWhite'

# Sentinel for a mesh that has no material slots at all. Unlike an empty slot
# (None), which is a likely authoring mistake and maps to _missing_material_,
# a mesh without slots is exported with BASE_WHITE.
NO_MATERIAL = object()

def foreach_get(collection, attr, dtype, width=1):
    """Read the attribute `attr` of all items of a bpy collection into a numpy array"""
    data = np.empty(len(collection) * width, dtype=dtype)
    collection.foreach_get(attr, data)
    return data.reshape(-1, width) if width > 1 else data

def triangulate(mesh):
    """
    Triangulate the mesh in place, as Ogre only supports triangles.
    Returns the mapping from the new triangle indices to the original polygon indices.
    """
    bm = bmesh.new()
    bm.from_mesh(mesh)
    face_map = bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='FIXED')['face_map']
    bm.to_mesh(mesh)
    tess_polygon_face_map = {tess_face.index: face.index for tess_face, face in face_map.items()}
    bm.free()
    return tess_polygon_face_map

def calc_normals(mesh, tangents):
    if tangents != 0:
        mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    elif bpy.app.version < (4, 1, 0):
        # calc_tangents() already calculates split normals for us
        mesh.calc_normals_split()

def calc_triangles(mesh):
    """Return the loop indices of the triangles of a triangulated mesh as (N, 3) array"""
    if np.any(foreach_get(mesh.polygons, 'loop_total', np.int32) != 3):
        raise ValueError('Polygon not a triangle')
    loop_start = foreach_get(mesh.polygons, 'loop_start', np.int32)
    return loop_start[:, None] + np.arange(3, dtype=np.int32)

def first_occurrences(*columns):
    """
    Deduplicate the rows formed by stacking `columns`.

    Returns the index of the first occurrence of every distinct row, in order
    of appearance, and for every row the position of its distinct row therein.
    """
    # adding 0.0 turns -0.0 into 0.0, so they compare equal as in Python
    keys = np.column_stack(columns).astype(np.float64) + 0.0
    if len(keys) == 0:
        return np.zeros(0, np.intp), np.zeros(0, np.intp)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    order = np.argsort(first)
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    return first[order], rank[inverse.reshape(-1)]

def vertex_colors(mesh):
    """Return the per loop vertex colors as (N, 4) array or None if the mesh has no colors"""
    color_names = ["col", "color", "colour", "attribute"]

    # In Blender version 3.2, vertex colors have been refactored into generic color attributes
    # https://developer.blender.org/docs/release_notes/3.2/sculpt/
    if bpy.app.version >= (3, 2, 0):
        vertex_colors = mesh.color_attributes
    else:
        vertex_colors = mesh.vertex_colors

    if len(vertex_colors) == 0:
        return None
    logger.debug("* Mesh has vertex colors")

    found = None
    for key, colors in vertex_colors.items():
        if (found is None) and (key.lower() in color_names):
            found = colors

            if (bpy.app.version >= (3, 2, 0)):
                if colors.domain != 'CORNER':
                    Report.warnings.append( 'Mesh "%s" with color attribute "%s" has wrong color domain: "%s" (should be: "CORNER")' % \
                        (mesh.name, key, colors.domain) )
                if colors.data_type != 'BYTE_COLOR':
                    Report.warnings.append( 'Mesh "%s" with color attribute "%s" has wrong color data type: "%s" (should be: "BYTE_COLOR")' % \
                        (mesh.name, key, colors.data_type) )

    if found is None:
        # No color found by name, assume that the only vertex color data is actual color data
        logger.debug("No color found by name, assume that the only vertex color data is actual color data")
        found = colors

    return foreach_get(found.data, 'color', np.float32, 4)

class MeshAttributes:
    """
    The vertex attributes of a triangulated mesh as numpy arrays, with vectors
    converted to the Ogre coordinate system. Positions are indexed by vertex,
    everything else by loop.
    """
    def __init__(self, mesh, tangents):
        self.positions = swap_array(foreach_get(mesh.vertices, 'co', np.float32, 3))
        self.vertex_index = foreach_get(mesh.loops, 'vertex_index', np.int32)

        if bpy.app.version < (3, 6, 0):
            self.normals = swap_array(foreach_get(mesh.loops, 'normal', np.float32, 3))
        else:
            self.normals = swap_array(foreach_get(mesh.corner_normals, 'vector', np.float32, 3))

        if tangents != 0:
            self.tangents = np.column_stack((
                swap_array(foreach_get(mesh.loops, 'tangent', np.float32, 3)),
                foreach_get(mesh.loops, 'bitangent_sign', np.float32)))
        else:
            self.tangents = np.zeros((len(mesh.loops), 4), np.float32)

        self.uvs = [foreach_get(layer.data, 'uv', np.float32, 2) for layer in mesh.uv_layers]
        self.colors = vertex_colors(mesh)

    @property
    def has_color_data(self):
        return self.colors is not None

    def template(self, doc, tangents, dotextures):
        """Format string for a <vertex> element, see rows()"""
        xyz = {'x' : '%6f', 'y' : '%6f', 'z' : '%6f'}
        children = [doc.leaf_template('position', xyz, 1), doc.leaf_template('normal', xyz, 1)]
        if tangents != 0:
            children.append(doc.leaf_template('tangent', {'w' : '%6f', **xyz}, 1))
        if self.has_color_data:
            children.append(doc.leaf_template('colour_diffuse', {'value' : '%6f %6f %6f %6f'}, 1))
        if dotextures:
            children += [doc.leaf_template('texcoord', {'u' : '%6f', 'v' : '%6f'}, 1)] * len(self.uvs)
        return doc.element_template('vertex', children)

    def rows(self, loops, tangents, dotextures):
        """Values for template() of the vertices given by one of their loops"""
        columns = [self.positions[self.vertex_index[loops]], self.normals[loops]]
        if tangents != 0:
            columns.append(self.tangents[loops][:, [3, 0, 1, 2]]) # w, x, y, z
        if self.has_color_data:
            columns.append(self.colors[loops])
        if dotextures:
            for uv in self.uvs:
                u, v = uv[loops].astype(np.float64).T
                columns += [u, 1.0 - v]
        return np.column_stack(columns)

def write_submeshnames (doc, material_names):
    doc.start_tag('submeshnames', {})
    for i, name in enumerate (material_names):
        doc.leaf_tag('submesh', {'name': name, 'index': i})
    doc.end_tag('submeshnames')

def write_skeletonlink (obj_name, arm, doc):
    if arm is None:
        return
    skeleton_name = obj_name
    if config.get('SHARED_ARMATURE') is True:
        skeleton_name = arm.data.name
    skeleton_name = util.clean_object_name(skeleton_name)
    doc.leaf_tag('skeletonlink', { 'name' : '%s.skeleton' % skeleton_name })

def write_faces (doc, faces):
    doc.start_tag('faces', { 'count' : str(len(faces))})
    doc.write_rows(doc.leaf_template('face', {'v1' : '%d', 'v2' : '%d', 'v3' : '%d'}), faces.tolist())
    doc.end_tag('faces')

def calc_boneindex (arm):
    """
    Return the vertex-group name -> Ogre bone index mapping.

    This must match Skeleton.to_xml(): only bones with shouldOutput are
    written, and ancestors of deformable bones are kept as well. Otherwise
    ONLY_DEFORMABLE_BONES shifts the indices relative to the .skeleton file.
    """
    if arm is None:
        return {}

    outputEnabled = {bone.name: True for bone in arm.pose.bones}
    if config.get('ONLY_DEFORMABLE_BONES') is True:
        for bone in arm.pose.bones:
            outputEnabled[bone.name] = bone.bone.use_deform
        # Keep every ancestor of a deformable bone so the Ogre bone
        # hierarchy remains connected.
        for bone in arm.pose.bones:
            if bone.bone.use_deform:
                parent = bone.parent
                while parent:
                    outputEnabled[parent.name] = True
                    parent = parent.parent

    boneIndexFromName = {}
    boneIndex = 0
    for bone in arm.pose.bones:
        if outputEnabled[bone.name]:
            boneIndexFromName[bone.name] = boneIndex
            boneIndex += 1
    return boneIndexFromName

def calc_bone_weights (mesh, ob, arm):
    """Return the (bone index, weight) pairs of every vertex of the mesh"""
    if arm is None:
        return [[] for v in mesh.vertices]
    boneindex = calc_boneindex (arm)
    group_bones = [boneindex.get(vg.name) for vg in ob.vertex_groups]
    TRIM_BONE_WEIGHTS = config.get('TRIM_BONE_WEIGHTS')
    return [[(group_bones[g.group], g.weight) for g in v.groups
             if g.weight > TRIM_BONE_WEIGHTS and group_bones[g.group] is not None]
            for v in mesh.vertices]

def calc_materials (ob):
    materials = []
    for material in ob.data.materials:
        materials.append (material)
    if not materials:
        # Keep the face material index valid; write_unshared() maps this to
        # the built-in BaseWhite material.
        materials.append(NO_MATERIAL)
    return materials

def material_reference (mat, prefix=''):
    """
    Return (name, extern) for a material slot as used in the .mesh file.

    A mesh without material slots references the built-in BaseWhite material,
    an empty slot references _missing_material_ and materials prefixed with
    extern. reference a material that is provided by the Ogre project.
    """
    if mat is NO_MATERIAL:
        return BASE_WHITE, True
    if mat is None:
        return '_missing_material_', True

    name = mat.name
    if name.startswith("extern."):
        name = name[len("extern."):]
        if not name:
            return BASE_WHITE, True
        # External material names are not prefixed with the library name.
        return material_name(name, prefix=prefix), True
    return material_name(mat, prefix=prefix), False

def valid_material_faces (mesh, num_materials):
    """Return a mask of the faces with a valid material index, warn about the others"""
    material_index = foreach_get(mesh.polygons, 'material_index', np.int32)
    valid = material_index < num_materials
    for fidx in np.flatnonzero(~valid):
        failure = 'Invalid material index %s on face %s of mesh %s' % (
            material_index[fidx], fidx, mesh.name)
        logger.error(failure)
        Report.warnings.append(failure)
    return material_index, valid

def write_unshared (target_file, path, dotextures, mesh, normals, tangents, ob, obj_name, material_prefix=''):

    logger.info('* Writing unshared geometry')

    if config.get ('ARMATURE_ANIMATION') is True:
        arm = ob.find_armature()
    else:
        arm = None

    materials = calc_materials (ob)
    material_names = [material_reference(mat, material_prefix)[0] for mat in materials]

    triangulate(mesh)
    calc_normals(mesh, tangents)
    attr = MeshAttributes(mesh, tangents)
    material_index, valid = valid_material_faces(mesh, len(materials))
    material_index = material_index[valid]
    loops = calc_triangles(mesh)[valid].reshape(-1)

    # Bone weights are part of the vertex identity: two loops at the same
    # position with the same normal/UV/color may still be bound to
    # different bones and must not be merged.
    bone_weights = calc_bone_weights(mesh, ob, arm)
    weight_classes = {}
    bone_class = np.array([weight_classes.setdefault(frozenset(w), len(weight_classes))
                           for w in bone_weights], dtype=np.int32)

    vertex_index = attr.vertex_index[loops]
    key = [attr.positions[vertex_index], attr.normals[loops], *[uv[loops] for uv in attr.uvs],
           attr.tangents[loops], bone_class[vertex_index]]
    if attr.has_color_data:
        key.append(attr.colors[loops])
    first, inverse = first_occurrences(*key)
    vertex_loops = loops[first]
    vertices = attr.rows(vertex_loops, tangents, dotextures)
    vertex_weights = [bone_weights[v] for v in attr.vertex_index[vertex_loops].tolist()]
    faces = inverse.reshape(-1, 3)

    with open(target_file, 'w') as f:
        doc = SimpleSaxWriter(f, 'mesh', {})

        doc.start_tag('submeshes', {})

        for i in range(len(materials)):
            logger.info('* Writing submesh: ' + str(i))

            submesh_faces = faces[material_index == i]
            face_count = len (submesh_faces)
            Report.triangles += face_count
            if face_count == 0:
                Report.warnings.append('BAD SUBMESH "%s": material %r, has not been applied to any faces - not exporting as submesh.' % (obj_name, material_names[i]) )
                continue # fixes corrupt unused materials

            # Renumber the vertices used by this submesh
            used_vertices = submesh_faces.reshape(-1)
            first_use, submesh_faces = first_occurrences(used_vertices)
            submesh_vertices = used_vertices[first_use]
            vertex_count = len (submesh_vertices)
            Report.vertices += vertex_count

            submesh_attributes = {
                'usesharedvertices' : 'false',
                "use32bitindexes" : str(bool(vertex_count > 65535)),
                "operationtype" : "triangle_list",
                "material" : material_names[i]}
            doc.start_tag('submesh', submesh_attributes)

            write_faces(doc, submesh_faces.reshape(-1, 3))

            doc.start_tag('geometry', {'vertexcount' : str(vertex_count)})

            doc.start_tag('vertexbuffer', {
                'positions':'true',
                'normals':'true',
                'tangents': str(bool(tangents)),
                'tangent_dimensions': str(tangents),
                'colours_diffuse' : str(attr.has_color_data),
                'texture_coords' : '%s' % int (len (mesh.uv_layers))})

            logger.info('* Writing submesh vertices: ' + str(i))
            doc.write_rows(attr.template(doc, tangents, dotextures), vertices[submesh_vertices].tolist())

            doc.end_tag('vertexbuffer')
            doc.end_tag('geometry')

            if arm:
                doc.start_tag('boneassignments', {})
                template = doc.leaf_template('vertexboneassignment', {'boneindex' : '%d', 'vertexindex' : '%d', 'weight' : '%6f'})
                doc.write_rows(template, [(bone, r, weight)
                                          for r, v in enumerate(submesh_vertices.tolist())
                                          for bone, weight in vertex_weights[v]])
                doc.end_tag('boneassignments')

            doc.end_tag('submesh')
        doc.end_tag('submeshes')

        write_submeshnames (doc, material_names)
        write_skeletonlink (obj_name, arm, doc)

        doc.close() # reported by Reyn
        f.close ()

    return [name for name in material_names if name != '_missing_material_']

def write_shared (target_file, path, dotextures, mesh, normals, tangents, material_prefix, ob, obj_name, copy, start, ignore_shape_animation, isLOD, disable_mods):
    with open(target_file, 'w') as f:
        doc = SimpleSaxWriter(f, 'mesh', {})

        # The vertex count is only known after deduplicating the vertices, so
        # reserve the attribute value and patch it in before closing the file.
        vertex_count = doc.start_tag_with_placeholder('sharedgeometry', 'vertexcount')

        logger.info('* Writing shared geometry')

        # Print a warning if there are no UV Maps created for the object
        # and the user requested to have tangents generated 
        # (they won't be without a UV Map)
        if int(config.get("GENERATE_TANGENTS")) != 0 and len(mesh.uv_layers) == 0:
            logger.warning("No UV Maps were created for this object: <%s>, tangents won't be exported." % ob.name)
            Report.warnings.append( 'Object "%s" has no UV Maps, tangents won\'t be exported.' % ob.name )

        doc.start_tag('vertexbuffer', {
                'positions':'true',
                'normals':'true',
                'tangents': str(bool(tangents)),
                'tangent_dimensions': str(tangents),
                'colours_diffuse' : str(bool(mesh.color_attributes) if bpy.app.version >= (3, 2, 0) else bool(mesh.vertex_colors)),
                'texture_coords' : '%s' % len(mesh.uv_layers) * dotextures
        })

        # Materials
        # saves tuples of material name and material obj (or None)
        materials = []
        # a material named 'vertex.color.<yourname>' will overwrite
        # the diffuse color in the mesh file!

        for mat in ob.data.materials:
            if not mat:
                logger.warn('Bad material data in: %s' % ob.name)
            mat_name, extern = material_reference(mat, material_prefix)
            materials.append( (mat_name, extern, mat) )
        if not materials:
            # No material slots at all: use the built-in material instead of
            # forcing the user-facing _missing_material_ diagnostic on it.
            materials.append( (BASE_WHITE, True, None) )

        if mesh.has_custom_normals:
            logger.debug("* Mesh has custom normals")
        else:
            logger.debug("* Mesh has NO custom normals")

        tess_polygon_face_map = triangulate(mesh)
        calc_normals(mesh, tangents)
        attr = MeshAttributes(mesh, tangents)
        loops = calc_triangles(mesh).reshape(-1)

        # Share the vertices of loops that only differ in position-independent
        # attributes, so flat shading, seams, etc. still get separate vertices.
        # Tangents are not compared, the first loop determines them.
        key = [attr.vertex_index[loops], attr.normals[loops]]
        if attr.has_color_data:
            key.append(attr.colors[loops])
        if dotextures:
            key += [uv[loops] for uv in attr.uvs]
        first, inverse = first_occurrences(*key)
        vertex_loops = loops[first]
        numverts = len(vertex_loops)
        faces = inverse.reshape(-1, 3)
        # Blender vertex and triangle of every Ogre vertex
        vertex_source = attr.vertex_index[vertex_loops]
        vertex_face = first // 3

        doc.write_rows(attr.template(doc, tangents, dotextures), attr.rows(vertex_loops, tangents, dotextures).tolist())

        vertex_groups = vertex_group_triangles(mesh, ob, attr.vertex_index[loops].reshape(-1, 3))
        material_index, valid = valid_material_faces(mesh, len(materials))

        Report.vertices += numverts

        doc.end_tag('vertexbuffer')
        doc.end_tag('sharedgeometry')

        logger.info('- Done at %s seconds' % util.timer_diff_str(start))
        logger.info('* Writing submeshes')

        doc.start_tag('submeshes', {})
        for matidx, (mat_name, extern, mat) in enumerate(materials):
            material_faces = faces[valid & (material_index == matidx)]
            if len(material_faces) == 0:
                Report.warnings.append('BAD SUBMESH "%s": material %r, has not been applied to any faces - not exporting as submesh.' % (obj_name, mat_name) )
                continue # fixes corrupt unused materials

            submesh_attributes = {
                'usesharedvertices' : 'true',
                # Maybe better look at index of all faces, if one over 65535 set to true;
                # Problem: we know it too late, postprocessing of file needed
                "use32bitindexes" : str(bool(numverts > 65535)),
                "operationtype" : "triangle_list"
            }
            submesh_attributes['material'] = mat_name

            doc.start_tag('submesh', submesh_attributes)
            write_faces(doc, material_faces)
            doc.end_tag('submesh')
            Report.triangles += len(material_faces)

        for name, triangles in vertex_groups.items():
            submesh_attributes = {
                'usesharedvertices' : 'true',
                "use32bitindexes" : str(bool(numverts > 65535)),
                "operationtype" : "triangle_list",
                "material": "none",
            }
            doc.start_tag('submesh', submesh_attributes)
            write_faces(doc, faces[triangles])
            doc.end_tag('submesh')

        doc.end_tag('submeshes')

        # Submesh names
        # todo: why is the submesh name taken from the material
        # when we have the blender object name available?
        doc.start_tag('submeshnames', {})
        for matidx, (mat_name, extern, mat) in enumerate(materials):
            doc.leaf_tag('submesh', {
                    'name' : mat_name,
                    'index' : str(matidx)
            })
        idx = len(materials)
        for name in vertex_groups.keys():
            name = name[len('ogre.vertex.group.'):]
            doc.leaf_tag('submesh', {'name': name, 'index': idx})
            idx += 1
        doc.end_tag('submeshnames')

        logger.info('- Done at %s seconds' % util.timer_diff_str(start))

        # Generate LOD levels for manual LOD meshes
        if isLOD == False and ob.type == 'MESH' and config.get('LOD_LEVELS') > 0 and config.get('LOD_GENERATION') == '2':
            lod_levels = config.get('LOD_LEVELS')
            lod_distance = config.get('LOD_DISTANCE')

            lod_generated = []
            lod_current_distance = lod_distance

            for level in range(lod_levels + 1)[1:]:
                lod_ob_name = obj_name + '_LOD_' + str(level)
                lod_manual_ob = bpy.context.scene.objects.get(lod_ob_name)

                if lod_manual_ob:
                    logger.info("- Found LOD Manual object: %s" % lod_ob_name)
                    lod_generated.append({ 'level': level, 'distance': lod_current_distance, 'lod_manual_ob': lod_manual_ob })
                    lod_current_distance += lod_distance

                else:
                    failure = 'FAILED to manually create LOD levels, manual LOD with name %s NOT FOUND!' % lod_ob_name
                    Report.warnings.append( failure )
                    logger.error( failure )
                    break

            # Create lod .mesh files and generate LOD XML to the original .mesh.xml
            if len(lod_generated) > 0:
                # 'manual' means if the geometry gets loaded from a different file than this LOD list references
                doc.start_tag('levelofdetail', {
                    'strategy'  : 'default',
                    'numlevels' : str(len(lod_generated) + 1), # The main mesh is + 1 (kind of weird Ogre logic)
                    'manual'    : "true"
                })

                logger.info('- Generating: %s LOD meshes. Original: vertices %s, faces: %s' % (len(lod_generated), len(mesh.vertices), len(mesh.loop_triangles)))
                for lod in lod_generated:
                    lod_manual_ob = lod['lod_manual_ob']

                    logger.info("- Writing LOD %s for distance %s, with %s vertices and %s faces" % 
                        (lod['level'], lod['distance'], len(lod_manual_ob.data.vertices), len(lod_manual_ob.data.loop_triangles)))

                    dot_mesh(lod_manual_ob, path, lod_manual_ob.data.name, ignore_shape_animation, normals, tangents, isLOD=True)

                    # 'value' is the distance this LOD kicks in for the 'Distance' strategy.
                    doc.leaf_tag('lodmanual', {
                        'value'    : str(lod['distance']),
                        'meshname' : clean_object_name(lod_manual_ob.data.name) + ".mesh"
                    })

                doc.end_tag('levelofdetail')

        # Generate LOD levels automatically using Blenders "Decimate" Modifier
        if isLOD == False and ob.type == 'MESH' and config.get('LOD_LEVELS') > 0 and config.get('LOD_GENERATION') == '1':
            lod_levels = config.get('LOD_LEVELS')
            lod_distance = config.get('LOD_DISTANCE')
            lod_ratio = config.get('LOD_PERCENT') / 100.0
            lod_pre_mesh_count = len(bpy.data.meshes)

            # Cap lod levels to something sensible (what is it?)
            if lod_levels > 10:
                lod_levels = 10

            def duplicate_object(scene, name, copyobj):
                # Create new mesh
                mesh = bpy.data.meshes.new(name)

                # Create new object associated with the mesh
                ob_new = bpy.data.objects.new(name, mesh)

                # Copy data block from the old object into the new object
                ob_new.data = copyobj.data.copy()
                ob_new.location = copyobj.location
                ob_new.rotation_euler = copyobj.rotation_euler
                ob_new.scale = copyobj.scale

                # Link new object to the given scene and select it
                scene.collection.objects.link(ob_new)
                ob_new.select_set(True)

                return ob_new, mesh

            # Create a temporary duplicate
            ob_copy, ob_copy_mesh = duplicate_object(bpy.context.scene, obj_name + "_LOD_TEMP_COPY", ob)
            ob_copy_meshes = [ ob_copy.data, ob_copy_mesh ]

            # Activate clone for modifier manipulation
            decimate = ob_copy.modifiers.new(name="Ogre-LOD_Decimate", type='DECIMATE')
            if decimate is not None:
                decimate.decimate_type = 'COLLAPSE'
                decimate.show_viewport = True
                decimate.show_render = True

                lod_generated = []
                lod_ratio_multiplier = 1.0 - lod_ratio
                lod_current_ratio = 1.0 * lod_ratio_multiplier
                lod_current_distance = lod_distance
                lod_current_vertice_count = len(mesh.vertices)
                lod_min_vertice_count = 12

                for level in range(lod_levels + 1)[1:]:
                    decimate.ratio = lod_current_ratio
                    
                    # https://docs.blender.org/api/current/bpy.types.Depsgraph.html
                    depsgraph = bpy.context.evaluated_depsgraph_get()
                    object_eval = ob_copy.evaluated_get(depsgraph)
                    lod_mesh = bpy.data.meshes.new_from_object(object_eval)
                    
                    ob_copy_meshes.append(lod_mesh)

                    # Check min vertice count and that the vertice count got reduced from last iteration
                    lod_mesh_vertices = len(lod_mesh.vertices)
                    
                    if lod_mesh_vertices < lod_min_vertice_count:
                        logger.info('- LOD level: %s, vertice count: %s too small. Ignoring LOD.' % (level, lod_mesh_vertices))
                        break
                    if lod_mesh_vertices >= lod_current_vertice_count:
                        logger.info('- LOD level: %s, vertice count: %s cannot be decimated any longer. Ignoring LOD.' % (level - 1, lod_mesh_vertices))
                        break
                    # todo: should we check if the ratio gets too small? although its up to the user to configure from the export panel

                    lod_generated.append({ 'level': level, 'distance': lod_current_distance, 'ratio': lod_current_ratio, 'mesh': lod_mesh })
                    lod_current_distance += lod_distance
                    lod_current_vertice_count = lod_mesh_vertices
                    lod_current_ratio *= lod_ratio_multiplier

                # Create lod .mesh files and generate LOD XML to the original .mesh.xml
                if len(lod_generated) > 0:
                    # 'manual' means if the geometry gets loaded from a
                    # different file that this LOD list references
                    # NOTE: This is the approach at the moment. Another option would be to
                    # references to the same vertex indexes in the shared geometry. But the
                    # decimate approach wont work with this as it generates a fresh geometry.
                    doc.start_tag('levelofdetail', {
                        'strategy'  : 'default',
                        'numlevels' : str(len(lod_generated) + 1), # The main mesh is + 1 (kind of weird Ogre logic)
                        'manual'    : "true"
                    })

                    logger.info('- Generating: %s LOD meshes. Original: vertices %s, faces: %s' % (len(lod_generated), len(mesh.vertices), len(mesh.loop_triangles)))
                    for lod in lod_generated:
                        ratio_percent = round(lod['ratio'] * 100.0, 0)
                        logger.info("- Writing LOD %s for distance %s and ratio %s/100, with %s vertices, %s faces" % 
                            (lod['level'], lod['distance'], str(ratio_percent), len(lod['mesh'].vertices), len(lod['mesh'].loop_triangles)))
                        lod_ob_temp = bpy.data.objects.new(obj_name, lod['mesh'])
                        lod_ob_temp.data.name = obj_name + '_LOD_' + str(lod['level'])
                        dot_mesh(lod_ob_temp, path, lod_ob_temp.data.name, ignore_shape_animation, normals, tangents, isLOD=True)

                        # 'value' is the distance this LOD kicks in for the 'Distance' strategy.
                        doc.leaf_tag('lodmanual', {
                            'value'    : str(lod['distance']),
                            'meshname' : lod_ob_temp.data.name + ".mesh"
                        })

                        # Delete temporary LOD object.
                        # The clone meshes will be deleted later.
                        lod_ob_temp.user_clear()
                        logger.debug("Removing temporary LOD object: %s" % lod_ob_temp.name)
                        bpy.data.objects.remove(lod_ob_temp, do_unlink=True)
                        del lod_ob_temp

                    doc.end_tag('levelofdetail')

            # Delete temporary LOD object
            logger.debug("Removing temporary LOD object: %s" % ob_copy.name)
            bpy.data.objects.remove(ob_copy, do_unlink=True)
            del ob_copy

            # Delete temporary data/mesh objects
            bpy.context.evaluated_depsgraph_get().update()
            for mesh_iter in ob_copy_meshes:
                mesh_iter.user_clear()
                logger.debug("Removing temporary LOD mesh: %s" % mesh_iter.name)
                bpy.data.meshes.remove(mesh_iter)
                del mesh_iter
            ob_copy_meshes = []

            if lod_pre_mesh_count != len(bpy.data.meshes):
                logger.warn('- After LOD generation, cleanup failed to erase all temporary data!')

        arm = ob.find_armature()
        if arm:
            write_skeletonlink (obj_name, arm, doc)
            doc.start_tag('boneassignments', {})
            vertex_bone_weights = calc_bone_weights(mesh, copy, arm)
            bone_weights = [vertex_bone_weights[v] for v in vertex_source.tolist()]
            template = doc.leaf_template('vertexboneassignment', {'boneindex' : '%d', 'vertexindex' : '%d', 'weight' : '%6f'})
            doc.write_rows(template, [(bone, vidx, weight)
                                      for vidx, weights in enumerate(bone_weights)
                                      for bone, weight in weights])
            badverts = 0
            for vidx, weights in enumerate(bone_weights):
                if len(weights) > 4:
                    badverts += 1
                    logger.warn('<%s> vertex %s is in more than 4 vertex groups (bone weights). This maybe Ogre incompatible' % (mesh.name, vidx))
            if badverts:
                Report.warnings.append( 'Mesh "%s" has %s vertices weighted to too many bones (Ogre limits a vertex to 4 bones). Try increasing the Trim-Weights threshold option' % (mesh.name, badverts) )
            doc.end_tag('boneassignments')

        # Updated June3 2011 - shape animation works
        if (config.get('SHAPE_ANIMATIONS') is True) and mesh.shape_keys and len(mesh.shape_keys.key_blocks) > 0:
            logger.info('* Writing shape keys')

            if ob.active_shape_key_index != 0 and ob.show_only_shape_key == True:
                warning = "Object \"%s\" mesh will look like selected shape key: '%s', not 'Basis'" % (ob.name, ob.active_shape_key.name)
                logger.warn(warning)
                Report.warnings.append(warning)

            shape_normals = config.get('SHAPE_NORMALS') is True
            if shape_normals:
                # normals_split_get() returns the normals of the loops of the
                # original mesh, polygon by polygon. Map each Ogre vertex to
                # the loop of its original polygon (before tesselation).
                loop_total = foreach_get(ob.data.polygons, 'loop_total', np.int32)
                loop_start = foreach_get(ob.data.polygons, 'loop_start', np.int32)
                polygon_offset = np.cumsum(loop_total) - loop_total
                loops = np.repeat(loop_start - polygon_offset, loop_total) + np.arange(loop_total.sum())
                loop_polygon = np.repeat(np.arange(len(loop_total)), loop_total)
                loop_vertex = foreach_get(ob.data.loops, 'vertex_index', np.int32)[loops]
                normal_index_of = {key: idx for idx, key in enumerate(zip(loop_polygon.tolist(), loop_vertex.tolist()))}
                source_faces = [tess_polygon_face_map.get(f, f) for f in vertex_face.tolist()]
                normal_indices = [normal_index_of[key] for key in zip(source_faces, vertex_source.tolist())]
                template = doc.leaf_template('poseoffset', {'index' : '%d', 'nx' : '%6f', 'ny' : '%6f', 'nz' : '%6f', 'x' : '%6f', 'y' : '%6f', 'z' : '%6f'}, 2)
            else:
                template = doc.leaf_template('poseoffset', {'index' : '%d', 'x' : '%6f', 'y' : '%6f', 'z' : '%6f'}, 2)

            positions = foreach_get(mesh.vertices, 'co', np.float32, 3)[vertex_source]

            doc.start_tag('poses', {})
            for sidx, skey in enumerate(mesh.shape_keys.key_blocks):
                # Skip the basis Shape Key
                if sidx == 0:
                    continue

                if len(skey.data) != len( ob.data.vertices ):
                    failure = 'FAILED to save shape animation - you can not use a modifier that changes the vertex count! '
                    failure += '[ mesh : %s ]' % mesh.name
                    Report.warnings.append( failure )
                    logger.error( failure )
                    break

                doc.start_tag('pose', {
                        'name' : skey.name,
                        # If target is 'mesh', no index needed, if target is submesh then submesh identified by 'index'
                        #'index' : str(sidx-1),
                        #'index' : '0',
                        'target' : 'mesh'
                })

                columns = [np.arange(numverts)]
                if shape_normals:
                    normals = np.array(skey.normals_split_get(), np.float32).reshape(-1, 3)
                    columns.append(swap_array(normals[normal_indices]))
                offsets = foreach_get(skey.data, 'co', np.float32, 3)[vertex_source] - positions
                columns.append(swap_array(offsets))
                doc.write_rows(template, np.column_stack(columns).tolist())

                doc.end_tag('pose')
            doc.end_tag('poses')

            logger.info('- Done at %s seconds' % util.timer_diff_str(start))

            if mesh.shape_keys.animation_data and len(mesh.shape_keys.animation_data.nla_tracks) > 0:
                logger.info('* Writing shape animations')
                doc.start_tag('animations', {})
                _fps = float( bpy.context.scene.render.fps )
                for nla in mesh.shape_keys.animation_data.nla_tracks:
                    for idx, strip in enumerate(nla.strips):
                        doc.start_tag('animation', {
                                'name' : strip.name,
                                'length' : str((strip.frame_end-strip.frame_start)/_fps)
                        })
                        doc.start_tag('tracks', {})
                        doc.start_tag('track', {
                                'type' : 'pose',
                                'target' : 'mesh'
                                # If target is 'mesh', no index needed, if target is submesh then submesh identified by 'index'
                                #'index' : str(idx)
                                #'index' : '0'
                        })
                        doc.start_tag('keyframes', {})
                        for frame in range( int(strip.frame_start), int(strip.frame_end)+1, bpy.context.scene.frame_step):#thanks to Vesa
                            bpy.context.scene.frame_set(frame)
                            doc.start_tag('keyframe', {
                                    'time' : str((frame-strip.frame_start)/_fps)
                            })
                            for sidx, skey in enumerate( mesh.shape_keys.key_blocks ):
                                if sidx == 0: continue
                                doc.leaf_tag('poseref', {
                                        'poseindex' : str(sidx-1),
                                        'influence' : str(skey.value)
                                })
                            doc.end_tag('keyframe')
                        doc.end_tag('keyframes')
                        doc.end_tag('track')
                        doc.end_tag('tracks')
                        doc.end_tag('animation')
                doc.end_tag('animations')
                logger.info('- Done at %s seconds' % util.timer_diff_str(start))

        doc.fill_placeholder(vertex_count, numverts)
        doc.close() # reported by Reyn

    mats = []
    for mat_name, extern, mat in materials:
        # _missing_material_ is marked as extern
        if not extern:
            mats.append(mat_name)
        else:
            logger.info("Extern material: %s" % mat_name)
    return mats

def dot_mesh(ob, path, force_name=None, ignore_shape_animation=False, normals=True, tangents=4, isLOD=False, **kwargs):
    """
    export the vertices of an object into a .mesh file

    ob: the blender object
    path: the path to save the .mesh file to. path MUST exist
    force_name: force a different name for this .mesh
    kwargs:
      * material_prefix - string. (optional)
      * overwrite - bool. (optional) default False
      * ignore_visibility - bool. (optional) default False. Export even if the
        object is hidden or unselected. Used for auxiliary meshes such as
        collision proxies.
    """
    obj_name = force_name or ob.data.name
    obj_name = clean_object_name(obj_name)
    target_file = os.path.join(path, '%s.mesh.xml' % obj_name )

    material_prefix = kwargs.get('material_prefix', '')
    overwrite = kwargs.get('overwrite', False)
    ignore_visibility = kwargs.get('ignore_visibility', False)

    # Don't export hidden or unselected objects unless told to
    if  not isLOD and not ignore_visibility and (
        (config.get('LOD_GENERATION') == '2' and "_LOD_" in ob.name) or
        ((config.get("EXPORT_HIDDEN") is False) and ob not in bpy.context.visible_objects) or
        ((config.get("SELECTED_ONLY") is True) and not ob.select_get())
        ):
        logger.debug("Skip exporting hidden/non-selected object: %s" % ob.data.name)
        return []

    if os.path.isfile(target_file) and not overwrite:
        return []

    if not os.path.isdir( path ):
        os.makedirs( path )

    start = time.time()

    if ob.modifiers != None:
        # Disable Armature and Array modifiers before `to_mesh()` collapse
        # NOTE: We need to disable the modifiers on the original object itself, we'll enable them again later
        # If we try to remove the unwanted modifiers from the copy object, then none of the modifiers will be applied when doing `to_mesh()`

        # If we want to optimise array modifiers as instances, then the Array Modifier should be disabled
        if config.get("ARRAY") is True:
            disable_mods = ['ARMATURE', 'ARRAY']
        else:
            disable_mods = ['ARMATURE']

        for mod in ob.modifiers:
            if mod.type in disable_mods and mod.show_viewport is True:
                logger.debug("Disabling Modifier: %s" % mod.name)
                mod.show_viewport = False

        # Without this, modifiers won't be applied by `to_mesh()`
        depsgraph = bpy.context.evaluated_depsgraph_get()
        object_eval = ob.evaluated_get(depsgraph)

        copy = object_eval.copy()
        #bpy.context.scene.collection.objects.link(copy)
    else:
        copy = ob

    # bake mesh
    mesh = copy.to_mesh()
    mesh.update()

    # Blender by default does not calculate these. 
    # When querying the quads/tris of the object blender would crash if calc_tessface was not updated
    mesh.calc_loop_triangles()

    Report.meshes.append( obj_name )
    Report.faces += len( mesh.loop_triangles )
    Report.orig_vertices += len( mesh.vertices )

    logger.info('* Generating: %s.mesh.xml' % obj_name)
    logger.info("  - Vertices: %s" % len( mesh.vertices ))
    logger.info("  - Loop triangles: %s" % len( mesh.loop_triangles ))

    try:
        with open(target_file, 'w') as f:
            f.flush()
    except Exception as e:
        logger.error("Unable to create mesh file: %s" % target_file)
        logger.error(e)
        Report.errors.append("Unable to create mesh file: %s" % target_file)
        return []

    # Textures
    dotextures = False
    if mesh.uv_layers:
        dotextures = True
    else:
        tangents = 0

    unshare_geometry = config.get ('UNSHARE_GEOMETRY')
    if unshare_geometry:
        mats = write_unshared (target_file, path, dotextures, mesh, normals, tangents, ob, obj_name, material_prefix)
    else:
        mats = write_shared (target_file, path, dotextures, mesh, normals, tangents, material_prefix, ob, obj_name, copy, start, ignore_shape_animation, isLOD, disable_mods)

    ## If we made a copy of the object, clean it up
    if ob != copy:
        #bpy.context.collection.objects.unlink(copy)    # Blender 2.7x
        #bpy.context.scene.collection.objects.unlink(copy)  # Blender 2.8+
        copy.user_clear()
        logger.debug("Removing temporary object: %s" % copy.name)
        bpy.data.objects.remove(copy)
        del copy

    # Reenable disabled modifiers
    if ob.modifiers != None:
        for mod in ob.modifiers:
            if mod.type in disable_mods and mod.show_viewport == False:
                logger.debug("Enabling Modifier: %s" % mod.name)
                mod.show_viewport = True

    logger.info('- Created %s.mesh.xml at %s seconds' % (obj_name, util.timer_diff_str(start)))

    # Start .mesh.xml to .mesh convertion tool
    util.xml_convert(target_file, has_uvs=dotextures)

    logger.info('- Created %s.mesh in total time %s seconds' % (obj_name, util.timer_diff_str(start)))

    # If requested by the user, generate LOD levels / Edge Lists / Vertex buffer optimization through OgreMeshUpgrader
    if ((config.get('LOD_LEVELS') > 0 and config.get('LOD_GENERATION') == '0') or
        (config.get('GENERATE_EDGE_LISTS') is True) or
        (config.get('PACK_INT_10_10_10_2') is True) or
        (config.get('OPTIMISE_VERTEX_CACHE') is True)):
        target_mesh_file = os.path.join(path, '%s.mesh' % obj_name )
        util.mesh_upgrade_tool(target_mesh_file)

    # Note that exporting the skeleton does not happen here anymore
    # It was moved to the function dot_skeleton in its own module (skeleton.py)

    return mats

def vertex_group_triangles(mesh, obj, triangles):
    """
    Return the indices of the triangles that are entirely within each
    'ogre.vertex.group.*' vertex group. Triangles touching a vertex that is
    in any other vertex group are ignored.
    """
    prefix = "ogre.vertex.group."
    names = [group.name for group in obj.vertex_groups]
    if not any(name.startswith(prefix) for name in names):
        return {}

    # The ogre vertex groups of each vertex or None if it is in any other group
    vertex_groups = []
    for v in mesh.vertices:
        groups = {names[g.group] if g.group < len(names) else '' for g in v.groups}
        vertex_groups.append(groups if all(name.startswith(prefix) for name in groups) else None)

    result = {}
    for tidx, (a, b, c) in enumerate(triangles.tolist()):
        if vertex_groups[a] is None or vertex_groups[b] is None or vertex_groups[c] is None:
            continue
        for name in vertex_groups[a] & vertex_groups[b] & vertex_groups[c]:
            result.setdefault(name, []).append(tidx)
    return result
