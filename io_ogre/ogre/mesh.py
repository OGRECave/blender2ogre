import os, time, sys, logging
import bmesh
import mathutils
from ..report import Report
from ..util import *
from ..xml import *
from .. import util
from .material import *
from .skeleton import Skeleton

logger = logging.getLogger('mesh')

class VertexColorLookup:
    def __init__(self, mesh):
        self.vcolors = None
        self.vcolors_alpha = None
        self.has_vcolors = False

        if len(mesh.vertex_colors) == 0:
            return
        self.vcolors = mesh.vertex_colors[0]
        self.has_vcolors = bool(self.vcolors)

        for bloc in mesh.vertex_colors:
            if bloc.name.lower().startswith('alpha'):
                self.vcolors_alpha = bloc
                break

    def get(self, index):
        if not self.has_vcolors:
            return (1.0,) * 4

        r,g,b = self.vcolors.data[index].color
        if self.vcolors_alpha:
            ra,ga,ba = self.vcolors_alpha.data[index].color
        else:
            ra = 1.0

        return (r,g,b,ra)

def dot_mesh( ob, path, force_name=None, ignore_shape_animation=False, normals=True, tangents=4, isLOD=False, **kwargs):
    """
    export the vertices of an object into a .mesh file

    ob: the blender object
    path: the path to save the .mesh file to. path MUST exist
    force_name: force a different name for this .mesh
    kwargs:
      * material_prefix - string. (optional)
      * overwrite - bool. (optional) default False
    """
    obj_name = force_name or ob.data.name
    obj_name = clean_object_name(obj_name)
    target_file = os.path.join(path, '%s.mesh.xml' % obj_name )

    material_prefix = kwargs.get('material_prefix', '')
    overwrite = kwargs.get('overwrite', False)

    if os.path.isfile(target_file) and not overwrite:
        return []

    if not os.path.isdir( path ):
        os.makedirs( path )

    start = time.time()

    # blender per default does not calculate these. when querying the quads/tris
    # of the object blender would crash if calc_tessface was not updated
    ob.data.update(calc_tessface=True)

    Report.meshes.append( obj_name )
    Report.faces += len( ob.data.tessfaces )
    Report.orig_vertices += len( ob.data.vertices )

    cleanup = False
    if ob.modifiers:
        cleanup = True
        copy = ob.copy()
        #bpy.context.scene.objects.link(copy)
        rem = []
        for mod in copy.modifiers:        # remove armature and array modifiers before collaspe
            if mod.type in 'ARMATURE ARRAY'.split(): rem.append( mod )
        for mod in rem: copy.modifiers.remove( mod )
    else:
        copy = ob

    # bake mesh
    mesh = copy.to_mesh(bpy.context.scene, True, "PREVIEW")

    logger.info('* Generating: %s.mesh.xml' % obj_name)

    try:
        with open(target_file, 'w') as f:
            f.flush()
    except Exception as e:
        show_dialog("Invalid mesh object name: %s" % obj_name)
        return

    with open(target_file, 'w') as f:
        doc = SimpleSaxWriter(f, 'mesh', {})

        # Very ugly, have to replace number of vertices later
        doc.start_tag('sharedgeometry', {'vertexcount' : '__TO_BE_REPLACED_VERTEX_COUNT__'})

        logger.info('* Writing shared geometry')

        # Textures
        dotextures = False
        if mesh.tessface_uv_textures.active:
            dotextures = True
        else:
            tangents = 0

        doc.start_tag('vertexbuffer', {
                'positions':'true',
                'normals':'true',
                'tangents': str(bool(tangents)),
                'tangent_dimensions': str(tangents),
                'colours_diffuse' : str(bool( mesh.vertex_colors )),
                'texture_coords' : '%s' % len(mesh.uv_textures) * dotextures
        })

        # Materials
        # saves tuples of material name and material obj (or None)
        materials = []
        # a material named 'vertex.color.<yourname>' will overwrite
        # the diffuse color in the mesh file!

        for mat in ob.data.materials:
            mat_name = "_missing_material_"
            if mat is not None:
                mat_name = mat.name
            mat_name = material_name(mat_name, prefix=material_prefix)
            extern = False
            if mat_name.startswith("extern."):
                mat_name = mat_name[len("extern."):]
                extern = True
            if mat:
                materials.append( (mat_name, extern, mat) )
            else:
                logger.warn('Bad material data in: %s' % ob.name)
                materials.append( ('_missing_material_', True, None) ) # fixed dec22, keep proper index
        if not materials:
            materials.append( ('_missing_material_', True, None) )
        vertex_groups = {}
        material_faces = []
        for matidx, mat in enumerate(materials):
            material_faces.append([])

        shared_vertices = {}
        _remap_verts_ = []
        _remap_normals_ = []
        _face_indices_ = []
        numverts = 0

        # Create bmesh to help obtain custom vertex normals
        bm = bmesh.new()
        if mesh.has_custom_normals:
            mesh.calc_normals_split()
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
        else:
            bm.from_mesh(mesh)

        # Ogre only supports triangles
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)

        # Vertex colors
        vertex_color_lookup = VertexColorLookup(mesh)

        if tangents:
            mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)

        progressScale = 1.0 / (len(mesh.polygons) - 1)
        for F in mesh.polygons:
            percent = F.index * progressScale
            sys.stdout.write( "\r + Faces [" + '=' * int(percent * 50) + '>' + '.' * int(50 - percent * 50) + "] " + str(int(percent * 10000) / 100.0) + "%   ")
            sys.stdout.flush()
            
            smooth = F.use_smooth
            tri = (F.vertices[0], F.vertices[1], F.vertices[2])
            face = []
            for loop_idx, idx in zip(F.loop_indices, tri):
                v = mesh.vertices[ idx ]

                if smooth:
                    n = mathutils.Vector()
                    if mesh.has_custom_normals:
                        for loop in bm.verts[idx].link_loops:
                            n += mesh.loops[loop.index].normal
                        n.normalize()
                        nx,ny,nz = swap( n )
                    # when no custom normals or mesh.loops[...].normal is zero vector
                    # use normal vector from vertex
                    if n.length_squared == 0:
                        nx,ny,nz = swap( v.normal ) # fixed june 17th 2011
                        n = mathutils.Vector( [nx, ny, nz] )
                elif tangents:
                    nx,ny,nz = swap( mesh.loops[ loop_idx ].normal )
                    n = mathutils.Vector( [nx, ny, nz] )
                else:
                    nx,ny,nz = swap( F.normal )
                    n = mathutils.Vector( [nx, ny, nz] )

                if tangents:
                    tx,ty,tz = swap( mesh.loops[ loop_idx ].tangent )
                    tw = mesh.loops[ loop_idx ].bitangent_sign

                r,g,b,ra = vertex_color_lookup.get(loop_idx)

                # Texture maps
                vert_uvs = []
                if dotextures:
                    for layer in mesh.uv_layers:
                        vert_uvs.append( layer.data[ loop_idx ].uv )

                ''' Check if we already exported that vertex with same normal, do not export in that case,
                    (flat shading in blender seems to work with face normals, so we copy each flat face'
                    vertices, if this vertex with same normals was already exported,
                    todo: maybe not best solution, check other ways (let blender do all the work, or only
                    support smooth shading, what about seems, smoothing groups, materials, ...)
                '''
                vert = VertexNoPos(numverts, nx, ny, nz, r, g, b, ra, vert_uvs)
                alreadyExported = False
                if idx in shared_vertices:
                    for vert2 in shared_vertices[idx]:
                        #does not compare ogre_vidx (and position at the moment)
                        if vert == vert2:
                            face.append(vert2.ogre_vidx)
                            alreadyExported = True
                            #print(idx,numverts, nx,ny,nz, r,g,b,ra, vert_uvs, "already exported")
                            break
                    if not alreadyExported:
                        face.append(vert.ogre_vidx)
                        shared_vertices[idx].append(vert)
                        #print(numverts, nx,ny,nz, r,g,b,ra, vert_uvs, "appended")
                else:
                    face.append(vert.ogre_vidx)
                    shared_vertices[idx] = [vert]
                    #print(idx, numverts, nx,ny,nz, r,g,b,ra, vert_uvs, "created")

                if alreadyExported:
                    continue

                numverts += 1
                _remap_verts_.append( v )
                _remap_normals_.append( n )
                _face_indices_.append( F.index )

                x,y,z = swap(v.co)        # xz-y is correct!

                doc.start_tag('vertex', {})
                doc.leaf_tag('position', {
                        'x' : '%6f' % x,
                        'y' : '%6f' % y,
                        'z' : '%6f' % z
                })

                doc.leaf_tag('normal', {
                        'x' : '%6f' % nx,
                        'y' : '%6f' % ny,
                        'z' : '%6f' % nz
                })

                if tangents:
                    doc.leaf_tag('tangent', {
                            'x' : '%6f' % tx,
                            'y' : '%6f' % ty,
                            'z' : '%6f' % tz,
                            'w' : '%6f' % tw
                    })

                if vertex_color_lookup.has_vcolors:
                    doc.leaf_tag('colour_diffuse', {'value' : '%6f %6f %6f %6f' % (r,g,b,ra)})

                # Texture maps
                if dotextures:
                    for uv in vert_uvs:
                        doc.leaf_tag('texcoord', {
                                'u' : '%6f' % uv[0],
                                'v' : '%6f' % (1.0-uv[1])
                        })

                doc.end_tag('vertex')

            append_triangle_in_vertex_group(mesh, ob, vertex_groups, face, tri)
            material_faces[F.material_index].append(face)

        Report.vertices += numverts

        doc.end_tag('vertexbuffer')
        doc.end_tag('sharedgeometry')

        print("")
        logger.info('- Done at %s seconds' % timer_diff_str(start))
        logger.info('* Writing submeshes')

        doc.start_tag('submeshes', {})
        for matidx, (mat_name, extern, mat) in enumerate(materials):
            if not len(material_faces[matidx]):
                Report.warnings.append('BAD SUBMESH "%s": material %r, has not been applied to any faces - not exporting as submesh.' % (obj_name, mat_name) )
                continue # fixes corrupt unused materials

            submesh_attributes = {
                'usesharedvertices' : 'true',
                # Maybe better look at index of all faces, if one over 65535 set to true;
                # Problem: we know it too late, postprocessing of file needed
                "use32bitindexes" : str(bool(numverts > 65535)),
                "operationtype" : "triangle_list"
            }
            if mat_name != "_missing_material_":
                submesh_attributes['material'] = mat_name

            doc.start_tag('submesh', submesh_attributes)
            doc.start_tag('faces', {
                'count' : str(len(material_faces[matidx]))
            })
            for fidx, (v1, v2, v3) in enumerate(material_faces[matidx]):
                doc.leaf_tag('face', {
                    'v1' : str(v1),
                    'v2' : str(v2),
                    'v3' : str(v3)
                })
            doc.end_tag('faces')
            doc.end_tag('submesh')
            Report.triangles += len(material_faces[matidx])

        for name, ogre_indices in vertex_groups.items():
            if len(ogre_indices) <= 0:
                continue
            submesh_attributes = {
                'usesharedvertices' : 'true',
                "use32bitindexes" : str(bool(numverts > 65535)),
                "operationtype" : "triangle_list",
                "material": "none",
            }
            doc.start_tag('submesh', submesh_attributes)
            doc.start_tag('faces', {
                'count' : len(ogre_indices)
            })
            for (v1, v2, v3) in ogre_indices:
                doc.leaf_tag('face', {
                    'v1' : str(v1),
                    'v2' : str(v2),
                    'v3' : str(v3)
                })
            doc.end_tag('faces')
            doc.end_tag('submesh')

        del material_faces
        del shared_vertices
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

        logger.info('- Done at %s seconds' % timer_diff_str(start))

        # Generate lod levels
        if isLOD == False and ob.type == 'MESH' and config.get('LOD_LEVELS') > 0 and config.get('LOD_MESH_TOOLS') == False:
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
                scene.objects.link(ob_new)
                ob_new.select = True

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

                for level in range(lod_levels+1)[1:]:
                    decimate.ratio = lod_current_ratio
                    lod_mesh = ob_copy.to_mesh(scene = bpy.context.scene, apply_modifiers = True, settings = 'PREVIEW')
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

                    logger.info('- Generating: %s LOD meshes. Original: vertices %s, faces: %s' % (len(lod_generated), len(mesh.vertices), len(mesh.tessfaces)))
                    for lod in lod_generated:
                        ratio_percent = round(lod['ratio'] * 100.0, 0)
                        logger.info("- Writing LOD %s for distance %s and ratio %s/100, with %s vertices, %s faces" % (lod['level'], lod['distance'], str(ratio_percent), len(lod['mesh'].vertices), len(lod['mesh'].tessfaces)))
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
                        bpy.data.objects.remove(bpy.data.objects[lod_ob_temp.name], do_unlink=True)
                        del lod_ob_temp

                    doc.end_tag('levelofdetail')

            # Delete temporary LOD object
            bpy.data.objects.remove(ob_copy, do_unlink=True)
            del ob_copy

            # Delete temporary data/mesh objects
            for mesh_iter in ob_copy_meshes:
                mesh_iter.user_clear()
                bpy.data.meshes.remove(mesh_iter)
                del mesh_iter
            ob_copy_meshes = []

            if lod_pre_mesh_count != len(bpy.data.meshes):
                logger.warn('- After LOD generation, cleanup failed to erase all temporary data!')

        arm = ob.find_armature()
        if arm:
            doc.leaf_tag('skeletonlink', {
                    'name' : '%s.skeleton' % obj_name
            })
            doc.start_tag('boneassignments', {})
            boneOutputEnableFromName = {}
            boneIndexFromName = {}
            for bone in arm.pose.bones:
                boneOutputEnableFromName[ bone.name ] = True
                if config.get('ONLY_DEFORMABLE_BONES'):
                    # if we found a deformable bone,
                    if bone.bone.use_deform:
                        # visit all ancestor bones and mark them "output enabled"
                        parBone = bone.parent
                        while parBone:
                            boneOutputEnableFromName[ parBone.name ] = True
                            parBone = parBone.parent
                    else:
                        # non-deformable bone, no output
                        boneOutputEnableFromName[ bone.name ] = False
            boneIndex = 0
            for bone in arm.pose.bones:
                boneIndexFromName[ bone.name ] = boneIndex
                if boneOutputEnableFromName[ bone.name ]:
                    boneIndex += 1
            badverts = 0
            for vidx, v in enumerate(_remap_verts_):
                check = 0
                for vgroup in v.groups:
                    if vgroup.weight > config.get('TRIM_BONE_WEIGHTS'):
                        groupIndex = vgroup.group
                        if groupIndex < len(copy.vertex_groups):
                            vg = copy.vertex_groups[ groupIndex ]
                            if vg.name in boneIndexFromName: # allows other vertex groups, not just armature vertex groups
                                bnidx = boneIndexFromName[ vg.name ] # find_bone_index(copy,arm,vgroup.group)
                                doc.leaf_tag('vertexboneassignment', {
                                        'vertexindex' : str(vidx),
                                        'boneindex' : str(bnidx),
                                        'weight' : '%6f' % vgroup.weight
                                })
                                check += 1
                        else:
                            logger.warn('Mesh: %s vertex groups not in sync with armature %s (groupIndex = %s)' % (mesh.name, arm.name, groupIndex))
                if check > 4:
                    badverts += 1
                    logger.warn('<%s> vertex %s is in more than 4 vertex groups (bone weights). This maybe Ogre incompatible' % (mesh.name, vidx))
            if badverts:
                Report.warnings.append( 'Mesh "%s" has %s vertices weighted to too many bones (Ogre limits a vertex to 4 bones). Try increasing the Trim-Weights threshold option' % (mesh.name, badverts) )
            doc.end_tag('boneassignments')

        # Updated June3 2011 - shape animation works
        if config.get('SHAPE_ANIMATIONS') and ob.data.shape_keys and len(ob.data.shape_keys.key_blocks):
            logger.info('* Writing shape keys')

            doc.start_tag('poses', {})
            for sidx, skey in enumerate(ob.data.shape_keys.key_blocks):
                if sidx == 0: continue
                if len(skey.data) != len( mesh.vertices ):
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

                snormals = None

                if config.get('SHAPE_NORMALS'):
                    if smooth:
                        snormals = skey.normals_vertex_get()
                    else:
                        snormals = skey.normals_polygon_get()

                for vidx, v in enumerate(_remap_verts_):
                    pv = skey.data[ v.index ]
                    x,y,z = swap( pv.co - v.co )

                    if config.get('SHAPE_NORMALS'):
                        n = _remap_normals_[ vidx ]
                        if smooth:
                            pn = mathutils.Vector( [snormals[ v.index * 3 ], snormals[ v.index * 3 + 1], snormals[ v.index * 3 + 2]] )
                        else:
                            vindex = _face_indices_[ vidx ]
                            pn = mathutils.Vector( [snormals[ vindex * 3 ], snormals[ vindex * 3 + 1], snormals[ vindex * 3 + 2]] )
                        nx,ny,nz = swap( pn - n )

                    #for i,p in enumerate( skey.data ):
                    #x,y,z = p.co - ob.data.vertices[i].co
                    #x,y,z = swap( ob.data.vertices[i].co - p.co )
                    #if x==.0 and y==.0 and z==.0: continue        # the older exporter optimized this way, is it safe?
                    if config.get('SHAPE_NORMALS'):
                        doc.leaf_tag('poseoffset', {
                                'x' : '%6f' % x,
                                'y' : '%6f' % y,
                                'z' : '%6f' % z,
                                'nx' : '%6f' % nx,
                                'ny' : '%6f' % ny,
                                'nz' : '%6f' % nz,
                                'index' : str(vidx)     # is this required?
                        })
                    else:
                        doc.leaf_tag('poseoffset', {
                                'x' : '%6f' % x,
                                'y' : '%6f' % y,
                                'z' : '%6f' % z,
                                'index' : str(vidx)     # is this required?
                        })
                doc.end_tag('pose')
            doc.end_tag('poses')

            logger.info('- Done at %s seconds' % timer_diff_str(start))

            if ob.data.shape_keys.animation_data and len(ob.data.shape_keys.animation_data.nla_tracks):
                logger.info('* Writing shape animations')
                doc.start_tag('animations', {})
                _fps = float( bpy.context.scene.render.fps )
                for nla in ob.data.shape_keys.animation_data.nla_tracks:
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
                            for sidx, skey in enumerate( ob.data.shape_keys.key_blocks ):
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
                logger.info('- Done at %s seconds' % timer_diff_str(start))

        ## Clean up and save
        mesh.user_clear()
        bpy.data.meshes.remove(mesh)
        del mesh

        if cleanup:
            #bpy.context.scene.objects.unlink(copy)
            copy.user_clear()
            bpy.data.objects.remove(copy)
            del copy

        del _remap_verts_
        del _remap_normals_
        del _face_indices_
        doc.close() # reported by Reyn
        f.close()

        logger.info('- Created %s.mesh.xml at %s seconds' % (obj_name, timer_diff_str(start)))

    # todo: Very ugly, find better way
    def replaceInplace(f,searchExp,replaceExp):
            import fileinput
            for line in fileinput.input(f, inplace=1):
                if searchExp in line:
                    line = line.replace(searchExp,replaceExp)
                sys.stdout.write(line)
            fileinput.close() # reported by jakob

    replaceInplace(target_file, '__TO_BE_REPLACED_VERTEX_COUNT__' + '"', str(numverts) + '"' )#+ ' ' * (ls - lr))
    del(replaceInplace)

    # Start .mesh.xml to .mesh convertion tool
    util.xml_convert(target_file, has_uvs=dotextures)

    logger.info('- Created %s.mesh in total time %s seconds' % (obj_name, timer_diff_str(start)))

    # If requested by the user, generate LOD levels through OgreMeshUpgrader
    if config.get('LOD_LEVELS') > 0 and config.get('LOD_MESH_TOOLS') == True:
        target_mesh_file = os.path.join(path, '%s.mesh' % obj_name )
        util.lod_create(target_mesh_file)
    
    # Note that exporting the skeleton does not happen here anymore
    # It was moved to the function dot_skeleton in its own module (skeleton.py)

    mats = []
    for mat_name, extern, mat in materials:
        # _missing_material_ is marked as extern
        if not extern:
            mats.append(mat_name)
        else:
            logger.info("Extern material: %s" % mat_name)

    return mats

def triangle_list_in_group(mesh, shared_vertices, group_index):
    faces = []
    for face in mesh.data.tessfaces:
        vertices = [mesh.data.vertices[v] for v in face.vertices]
        match_group = lambda g, v: g in [x.group for x in v.groups]
        all_in_group = all([match_group(group_index, v) for v in vertices])
        if not all_in_group:
            continue
        assert len(face.vertices) == 3
        entry = [shared_vertices[v][0].ogre_vidx for v in face.vertices]
        faces.append(tuple(entry))
    return faces

def append_triangle_in_vertex_group(mesh, obj, vertex_groups, ogre_indices, blender_indices):
    vertices = [mesh.vertices[i] for i in blender_indices]
    names = set()
    for v in vertices:
        for g in v.groups:
            if g.group >= len(obj.vertex_groups):
                return
            group = obj.vertex_groups[g.group]
            if not group.name.startswith("ogre.vertex.group."):
                return
            names.add(group.name)
    match_group = lambda name, v: name in [obj.vertex_groups[x.group].name for x in v.groups]
    for name in names:
        all_in_group = all([match_group(name, v) for v in vertices])
        if not all_in_group:
            continue
        if name not in vertex_groups:
            vertex_groups[name] = []
        vertex_groups[name].append(ogre_indices)

import cmath
def isclose(a,
            b,
            rel_tol=1e-9,
            abs_tol=0.0,
            method='weak'):
    ### copied from PEP 485. when blender switches to python 3.5 use math.isclose(...)
    """
    returns True if a is close in value to b. False otherwise
    :param a: one of the values to be tested
    :param b: the other value to be tested
    :param rel_tol=1e-8: The relative tolerance -- the amount of error
                         allowed, relative to the magnitude of the input
                         values.
    :param abs_tol=0.0: The minimum absolute tolerance level -- useful for
                        comparisons to zero.
    :param method: The method to use. options are:
                  "asymmetric" : the b value is used for scaling the tolerance
                  "strong" : The tolerance is scaled by the smaller of
                             the two values
                  "weak" : The tolerance is scaled by the larger of
                           the two values
                  "average" : The tolerance is scaled by the average of
                              the two values.
    NOTES:
    -inf, inf and NaN behave similar to the IEEE 754 standard. That
    -is, NaN is not close to anything, even itself. inf and -inf are
    -only close to themselves.
    Complex values are compared based on their absolute value.
    The function can be used with Decimal types, if the tolerance(s) are
    specified as Decimals::
      isclose(a, b, rel_tol=Decimal('1e-9'))
    See PEP-0485 for a detailed description
    """
    if method not in ("asymmetric", "strong", "weak", "average"):
        raise ValueError('method must be one of: "asymmetric",'
                         ' "strong", "weak", "average"')

    if rel_tol < 0.0 or abs_tol < 0.0:
        raise ValueError('error tolerances must be non-negative')

    if a == b:  # short-circuit exact equality
        return True
    # use cmath so it will work with complex or float
    if cmath.isinf(a) or cmath.isinf(b):
        # This includes the case of two infinities of opposite sign, or
        # one infinity and one finite number. Two infinities of opposite sign
        # would otherwise have an infinite relative tolerance.
        return False
    diff = abs(b - a)
    if method == "asymmetric":
        return (diff <= abs(rel_tol * b)) or (diff <= abs_tol)
    elif method == "strong":
        return (((diff <= abs(rel_tol * b)) and
                 (diff <= abs(rel_tol * a))) or
                (diff <= abs_tol))
    elif method == "weak":
        return (((diff <= abs(rel_tol * b)) or
                 (diff <= abs(rel_tol * a))) or
                (diff <= abs_tol))
    elif method == "average":
        return ((diff <= abs(rel_tol * (a + b) / 2) or
                (diff <= abs_tol)))
    else:
        raise ValueError('method must be one of:'
                         ' "asymmetric", "strong", "weak", "average"')

class VertexNoPos(object):
    def __init__(self, ogre_vidx, nx,ny,nz, r,g,b,ra, vert_uvs):
        self.ogre_vidx = ogre_vidx
        self.nx = nx
        self.ny = ny
        self.nz = nz
        self.r = r
        self.g = g
        self.b = b
        self.ra = ra
        self.vert_uvs = vert_uvs

    '''does not compare ogre_vidx (and position at the moment) [ no need to compare position ]'''
    def __eq__(self, o):
        if not isclose(self.nx, o.nx): return False
        if not isclose(self.ny, o.ny): return False
        if not isclose(self.nz, o.nz): return False
        if not isclose(self.r, o.r): return False
        if not isclose(self.g, o.g): return False
        if not isclose(self.b, o.b): return False
        if not isclose(self.ra, o.ra): return False
        if len(self.vert_uvs) != len(o.vert_uvs): return False
        if self.vert_uvs:
            for i, uv1 in enumerate( self.vert_uvs ):
                uv2 = o.vert_uvs[ i ]
                if uv1 != uv2: return False
        return True

    def __repr__(self):
        return 'vertex(%d)' % self.ogre_vidx
