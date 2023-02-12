#!BPY

"""
Name: 'OGRE for Kenshi (*.MESH)'
Blender: 2.63a, 2.77a, 2.79
Group: 'Import/Export'
Tooltip: 'Import/Export Kenhi OGRE mesh files'

Author: Someone

Based on the Torchlight Impost/Export script by 'Dusho'

Thanks goes to 'goatman' for his port of Ogre export script from 2.49b to 2.5x,
and 'CCCenturion' for trying to refactor the code to be nicer (to be included)
"""

__author__ = "someone"
__version__ = "0.8.15 17-Jul-2019"

__bpydoc__ = """\
This script imports/exports Kenshi Ogre models into/from Blender.

Supported:<br>
    * import/export of basic meshes
    * import/export of skeleton
    * import/export of animations
    * import/export of vertex weights (ability to import characters and adjust rigs)
    * import/export of vertex colour (RGB)
    * import/export of vertex alpha (Uses second vertex colour layer called Alpha)
    * import/export of shape keys
    * Calculation of tangents and binormals for export

Known issues:<br>
    * imported materials will lose certain informations not applicable to Blender when exported

History:<br>
    * v0.8.15  (17-Jul-2019) - Added option to import normals
    * v0.8.14  (14-May-2019) - Fixed blender deleting zero length bones
    * v0.8.13  (19-Mar-2019) - Exporting material files is optional
    * v0.8.12  (14-Mar-2019) - Fixed error exporting animation scale keyframes
    * v0.8.11  (26-Feb-2019) - Fixed tangents and binormals for mirrorred uvs
    * v0.8.10  (32-Jan-2019) - Fixed export when mesh has multiple uv sets
    * v0.8.9   (08-Mar-2018) - Added import option to match weight maps and link with a previously imported skeleton
    * v0.8.8   (26-Feb-2018) - Fixed export triangulation and custom normals
    * v0.8.7   (01-Feb-2018) - Scene frame rate adjusted on import, Fixed quatenion normalisation
    * v0.8.6   (31-Jan-2018) - Fixed crash exporting animations in blender 2.79
    * v0.8.5   (02-Jan-2018) - Optimisation: Use hashmap for duplicate vertex detection
    * v0.8.4   (20-Nov-2017) - Fixed animation quaternion interpolation
    * v0.8.3   (06-Nov-2017) - Warning when linked skeleton file not found
    * v0.8.2   (25-Sep-2017) - Fixed bone translations in animations
    * v0.8.1   (28-Jul-2017) - Added alpha component to vertex colour
    * v0.8.0   (30-Jun-2017) - Added animation and shape key support. Rewritten skeleton export
    * v0.7.2   (08-Dec-2016) - fixed divide by 0 error calculating tangents
    * v0.7.1   (07-Sep-2016) - bug fixes
    * v0.7.0   (02-Sep-2016) - Implemented changes needed for Kenshi: Persistant Ogre bone IDs, Export vertex colours. Generates tangents and binormals.
    * v0.6.2   (09-Mar-2013) - bug fixes (working with materials+textures), added 'Apply modifiers' and 'Copy textures'
    * v0.6.1   (27-Sep-2012) - updated to work with Blender 2.63a
    * v0.6     (01-Sep-2012) - added skeleton import + vertex weights import/export
    * v0.5     (06-Mar-2012) - added material import/export
    * v0.4.1   (29-Feb-2012) - flag for applying transformation, default=true
    * v0.4     (28-Feb-2012) - fixing export when no UV data are present
    * v0.3     (22-Feb-2012) - WIP - started cleaning + using OgreXMLConverter
    * v0.2     (19-Feb-2012) - WIP - working export of geometry and faces
    * v0.1     (18-Feb-2012) - initial 2.59 import code (from .xml)
    * v0.0     (12-Feb-2012) - file created
"""

"""
When importing: (x)-Blender, (x')-Ogre
vectors: x=x', y=-z', z=y'
UVtex: u=u', v = -v'+1

Inner data representation:
MESHDATA:
['sharedgeometry']: {}
    ['positions'] - vectors with [x,y,z]
    ['normals'] - vectors with [x,y,z]
    ['vertexcolors'] - vectors with [r,g,b,a]
    ['texcoordsets'] - integer (number of UV sets)
    ['uvsets'] - vectors with [u,v] * number or UV sets for vertex [[u,v]][[u,v]]...
    ['boneassignments']: {[boneName]} - for every bone name:
        [[vertexNumber], [weight]], [[vertexNumber], [weight]],  ..
['submeshes'][idx]
        [material] - string (material name)
        [materialOrg] - original material name - for searching the in shared materials file
        [faces] - vectors with faces [v1,v2,v3]
        [geometry] - identical to 'sharedgeometry' data content
['materials']
    [(matID)]: {}
        ['texture'] - full path to texture file
        ['imageNameOnly'] - only image name from material file
['skeleton']: {[boneName]} for each bone
        ['name'] - bone name
        ['id'] - bone ID
        ['position'] - bone position [x,y,z]
        ['rotation'] - bone rotation [x,y,z,angle]
        ['parent'] - bone name of parent bone
        ['children'] - list with names if children ([child1, child2, ...])
['boneIDs']: {[bone ID]:[bone Name]} - dictionary with ID to name
['skeletonName'] - name of skeleton

Note: Bones store their OGREID as a custom variable so they are consistent when a mesh is exported
"""

# When bpy is already in local, we know this is not the initial import...
if "bpy" in locals():
    # ...so we need to reload our submodule(s) using importlib
    import importlib
    if "material_parser" in locals():
        importlib.reload(material_parser.MaterialParser)

#from Blender import *
import bpy
from xml.dom import minidom
from mathutils import Vector, Matrix
import math, os, subprocess
from .material_parser import MaterialParser
from .. import config
from .. import util
from ..report import Report
from ..util import *

logger = logging.getLogger('ogre_import')

# Script internal options:
SHOW_IMPORT_DUMPS = False
SHOW_IMPORT_TRACE = False
MIN_BONE_LENGTH = 0.00001	# Prevent automatic removal of bones

# Default blender version of script
blender_version = 259

# Makes sure name doesn't exceed Blenders naming limits
# Also keeps after name (as Torchlight uses names to identify types -boots, chest, ...- with names)
# TODO: This is not needed for Blender 2.62 and above
def GetValidBlenderName(name):

    global blender_version

    newname = name.strip()
    
    maxChars = 20
    if blender_version > 262:
        maxChars = 63

    if(len(name) > maxChars):
        if(name.find("/") >= 0):
            if(name.find("Material") >= 0):
                # Replace 'Material' string with only 'Mt'
                newname = name.replace("Material", "Mt")
            # Check if it's still above 20
            if(len(newname) > maxChars):
                suffix = newname[newname.find("/"):]
                prefix = newname[0:(maxChars+1-len(suffix))]
                newname = prefix + suffix
        else:
            newname = name[0 : maxChars + 1]

    if(newname != name):
        logger.warning("Name truncated (%s -> %s)" % (name, newname))

    return newname

def xOpenFile(filename):
    xml_file = open(filename)
    try:
        xml_doc = minidom.parse(xml_file)
        output = xml_doc
    except Exception:
        logger.error("File %s is not valid XML!" % filename)
        Report.errors.append("File %s is not valid XML!" % filename)
        output = 'None'
    xml_file.close()
    return output


def xCollectFaceData(facedata):
    faces = []
    for face in facedata.childNodes:
        if face.localName == 'face':
            v1 = int(face.getAttributeNode('v1').value)
            v2 = int(face.getAttributeNode('v2').value)
            v3 = int(face.getAttributeNode('v3').value)
            faces.append([v1, v2, v3])

    return faces


def xCollectVertexData(data):
    vertexdata = {}
    vertices = []
    normals = []
    vertexcolors = []

    for vb in data.childNodes:
        if vb.localName == 'vertexbuffer':
            if vb.hasAttribute('positions'):
                for vertex in vb.getElementsByTagName('vertex'):
                    for vp in vertex.childNodes:
                        if vp.localName == 'position':
                            x = float(vp.getAttributeNode('x').value)
                            y = -float(vp.getAttributeNode('z').value)
                            z = float(vp.getAttributeNode('y').value)
                            vertices.append([x, y, z])
                vertexdata['positions'] = vertices

            if vb.hasAttribute('normals') and config.get('IMPORT_NORMALS'):
                for vertex in vb.getElementsByTagName('vertex'):
                    for vn in vertex.childNodes:
                        if vn.localName == 'normal':
                            x = float(vn.getAttributeNode('x').value)
                            y = -float(vn.getAttributeNode('z').value)
                            z = float(vn.getAttributeNode('y').value)
                            normals.append([x, y, z])
                vertexdata['normals'] = normals

            if vb.hasAttribute('colours_diffuse'):
                for vertex in vb.getElementsByTagName('vertex'):
                    for vcd in vertex.childNodes:
                        if vcd.localName == 'colour_diffuse':
                            rgba = vcd.getAttributeNode('value').value
                            r = float(rgba.split()[0])
                            g = float(rgba.split()[1])
                            b = float(rgba.split()[2])
                            a = float(rgba.split()[3])
                            vertexcolors.append([r, g, b, a])
                vertexdata['vertexcolors'] = vertexcolors

            if vb.hasAttribute('texture_coord_dimensions_0'):
                texcosets = int(vb.getAttributeNode('texture_coords').value)
                vertexdata['texcoordsets'] = texcosets
                uvcoordset = []
                for vertex in vb.getElementsByTagName('vertex'):
                    uvcoords = []
                    for vt in vertex.childNodes:
                        if vt.localName == 'texcoord':
                            u = float(vt.getAttributeNode('u').value)
                            v = -float(vt.getAttributeNode('v').value)+1.0
                            uvcoords.append([u, v])

                    if len(uvcoords) > 0:
                        uvcoordset.append(uvcoords)
                vertexdata['uvsets'] = uvcoordset

    return vertexdata


def xCollectMeshData(meshData, xmldoc, meshname, dirname):
    logger.info("* Collecting mesh data...")
    
    # Global has_skeleton
    faceslist = []
    subMeshData = []
    allObjs = []
    isSharedGeometry = False
    sharedGeom = []
    hasSkeleton = 'boneIDs' in meshData

    # Collect shared geometry
    if(len(xmldoc.getElementsByTagName('sharedgeometry')) > 0):
        isSharedGeometry = True
        for subnodes in xmldoc.getElementsByTagName('sharedgeometry'):
            meshData['sharedgeometry'] = xCollectVertexData(subnodes)

        if hasSkeleton:
            for subnodes in xmldoc.getElementsByTagName('boneassignments'):
                meshData['sharedgeometry']['boneassignments'] = xCollectBoneAssignments(meshData, subnodes)

    # Collect submeshes data
    for submeshes in xmldoc.getElementsByTagName('submeshes'):
        for submesh in submeshes.childNodes:
            if submesh.localName == 'submesh':
                materialOrg = str(submesh.getAttributeNode('material').value)
                # To avoid Blender naming limit problems
                material = GetValidBlenderName(materialOrg)
                sm = {}
                sm['material'] = material
                sm['materialOrg'] = materialOrg
                for subnodes in submesh.childNodes:
                    if subnodes.localName == 'faces':
                        facescount = int(subnodes.getAttributeNode('count').value)
                        sm['faces'] = xCollectFaceData(subnodes)

                        if len(xCollectFaceData(subnodes)) != facescount:
                            logger.debug("FacesCount doesn't match!")
                            break

                    if (subnodes.localName == 'geometry'):
                        vertexcount = int(subnodes.getAttributeNode('vertexcount').value)
                        sm['geometry'] = xCollectVertexData(subnodes)

                    if hasSkeleton and subnodes.localName == 'boneassignments' and isSharedGeometry==False:
                        sm['geometry']['boneassignments'] = xCollectBoneAssignments(meshData, subnodes)

                subMeshData.append(sm)

    meshData['submeshes'] = subMeshData

    return meshData


def xCollectBoneAssignments(meshData, xmldoc):
    boneIDtoName = meshData['boneIDs']

    VertexGroups = {}
    for vg in xmldoc.childNodes:
        if vg.localName == 'vertexboneassignment':
            VG = str(vg.getAttributeNode('boneindex').value)
            if VG in boneIDtoName.keys():
                VGNew = boneIDtoName[VG]
            else:
                VGNew = 'Group ' + VG
            if VGNew not in VertexGroups.keys():
                VertexGroups[VGNew] = []

    for vg in xmldoc.childNodes:
        if vg.localName == 'vertexboneassignment':

            VG = str(vg.getAttributeNode('boneindex').value)
            if VG in boneIDtoName.keys():
                VGNew = boneIDtoName[VG]
            else:
                VGNew = VG
            verti = int(vg.getAttributeNode('vertexindex').value)
            weight = float(vg.getAttributeNode('weight').value)
            #logger.debug("bone=%s, vert=%s, weight=%s" % (VGNew, verti, weight))
            VertexGroups[VGNew].append([verti, weight])

    return VertexGroups


def xCollectPoseData(meshData, xmldoc):
    logger.info("* Collecting pose data...")

    poses = xmldoc.getElementsByTagName('pose')
    if(len(poses) > 0):
        meshData['poses'] = []

    for pose in poses:
        name = pose.getAttribute('name')
        target = pose.getAttribute('target')
        index = pose.getAttribute('index')
        if target == 'submesh':
            poseData = {}
            poseData['name'] = name
            poseData['submesh'] = int(index)
            poseData['data'] = data = []
            meshData['poses'].append(poseData)
            for value in pose.getElementsByTagName('poseoffset'):
                index = int(value.getAttribute('index'))
                x = float(value.getAttribute('x'))
                y = float(value.getAttribute('y'))
                z = float(value.getAttribute('z'))
                data.append((index, x, -z, y))


def xGetSkeletonLink(xmldoc, folder):
    skeletonFile = "None"
    if(len(xmldoc.getElementsByTagName("skeletonlink")) > 0):
        # Get the skeleton link of the mesh
        skeletonLink = xmldoc.getElementsByTagName("skeletonlink")[0]
        skeletonName = skeletonLink.getAttribute("name")
        skeletonFile = os.path.join(folder, skeletonName)
        # Check for existence of skeleton file
        if not os.path.isfile(skeletonFile):
            Report.warnings.append("Cannot find linked skeleton file '%s'\nIt must be in the same directory as the mesh file." % skeletonName)
            logger.warning("Ogre skeleton missing: %s" % skeletonFile)
            skeletonFile = "None"

    return skeletonFile


#def xCollectBoneData(meshData, xDoc, name, folder):
def xCollectBoneData(meshData, xDoc):
    logger.info("* Collecting bone data...")
    
    OGRE_Bones = {}
    BoneIDToName = {}
    meshData['skeleton'] = OGRE_Bones
    meshData['boneIDs'] = BoneIDToName

    for bones in xDoc.getElementsByTagName('bones'):
        for bone in bones.childNodes:
            OGRE_Bone = {}
            if bone.localName == 'bone':
                boneName = str(bone.getAttributeNode('name').value)
                boneID = int(bone.getAttributeNode('id').value)
                OGRE_Bone['name'] = boneName
                OGRE_Bone['id'] = boneID
                BoneIDToName[str(boneID)] = boneName

                for b in bone.childNodes:
                    if b.localName == 'position':
                        x = float(b.getAttributeNode('x').value)
                        y = float(b.getAttributeNode('y').value)
                        z = float(b.getAttributeNode('z').value)
                        OGRE_Bone['position'] = [x, y, z]
                    if b.localName == 'rotation':
                        angle = float(b.getAttributeNode('angle').value)
                        axis = b.childNodes[1]
                        axisx = float(axis.getAttributeNode('x').value)
                        axisy = float(axis.getAttributeNode('y').value)
                        axisz = float(axis.getAttributeNode('z').value)
                        OGRE_Bone['rotation'] = [axisx, axisy, axisz, angle]

                OGRE_Bones[boneName] = OGRE_Bone

    for bonehierarchy in xDoc.getElementsByTagName('bonehierarchy'):
        for boneparent in bonehierarchy.childNodes:
            if boneparent.localName == 'boneparent':
                Bone = str(boneparent.getAttributeNode('bone').value)
                Parent = str(boneparent.getAttributeNode('parent').value)
                OGRE_Bones[Bone]['parent'] = Parent

    # Update Ogre bones with list of children
    calcBoneChildren(OGRE_Bones)

    # Helper bones
    calcHelperBones(OGRE_Bones)
    calcZeroBones(OGRE_Bones)

    # Update Ogre bones with head positions
    calcBoneHeadPositions(OGRE_Bones)

    # Update Ogre bones with rotation matrices
    calcBoneRotations(OGRE_Bones)

    return OGRE_Bones


def calcBoneChildren(BonesData):
    for bone in BonesData.keys():
        childlist = []
        for key in BonesData.keys():
            if 'parent' in BonesData[key]:
                parent = BonesData[key]['parent']
                if parent == bone:
                    childlist.append(key)
        BonesData[bone]['children'] = childlist


def calcHelperBones(BonesData):
    count = 0
    helperBones = {}
    for bone in BonesData.keys():
        if ((len(BonesData[bone]['children']) == 0) or
                (len(BonesData[bone]['children']) > 1)):
            HelperBone = {}
            HelperBone['position'] = [0.2, 0.0, 0.0]
            HelperBone['parent'] = bone
            HelperBone['rotation'] = [1.0, 0.0, 0.0, 0.0]
            HelperBone['flag'] = 'helper'
            HelperBone['name'] = 'Helper' + str(count)
            HelperBone['children'] = []
            helperBones['Helper' + str(count)] = HelperBone
            count += 1
    for hBone in helperBones.keys():
        BonesData[hBone] = helperBones[hBone]


def calcZeroBones(BonesData):
    zeroBones = {}
    for bone in BonesData.keys():
        pos = BonesData[bone]['position']
        if (math.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2)) == 0:
            ZeroBone = {}
            ZeroBone['position'] = [0.2, 0.0, 0.0]
            ZeroBone['rotation'] = [1.0, 0.0, 0.0, 0.0]
            if 'parent' in BonesData[bone]:
                ZeroBone['parent'] = BonesData[bone]['parent']
            ZeroBone['flag'] = 'zerobone'
            ZeroBone['name'] = 'Zero' + bone
            ZeroBone['children'] = []
            zeroBones['Zero' + bone] = ZeroBone
            if 'parent' in BonesData[bone]:
                BonesData[BonesData[bone]['parent']]['children'].append('Zero' + bone)
    for hBone in zeroBones.keys():
        BonesData[hBone] = zeroBones[hBone]


def calcBoneHeadPositions(BonesData):
    for key in BonesData.keys():

        start = 0
        thisbone = key
        posh = BonesData[key]['position']
        #print("SetBonesASPositions: bone=%s, org. position=%s" % (key, posh))
        while start == 0:
            if 'parent' in BonesData[thisbone]:
                parentbone = BonesData[thisbone]['parent']
                prot = BonesData[parentbone]['rotation']
                ppos = BonesData[parentbone]['position']

                #protmat = RotationMatrix(math.degrees(prot[3]), 3, 'r', Vector(prot[0], prot[1], prot[2])).invert()
                protmat = Matrix.Rotation(math.degrees(prot[3]), 3, Vector([prot[0], prot[1], prot[2]])).inverted()
                #print ("SetBonesASPositions: bone=%s, protmat=%s" % (key, protmat))
                #print(protmat)
                #newposh = protmat * Vector([posh[0], posh[1], posh[2]])
                #newposh = protmat * Vector([posh[2], posh[1], posh[0]]) #02
                newposh = protmat.transposed() * Vector([posh[0], posh[1], posh[2]]) #03
                #print("SetBonesASPositions: bone=%s, newposh=%s" % (key, newposh))
                positionh = VectorSum(ppos,newposh)

                posh = positionh

                thisbone = parentbone
            else:
                start = 1

        BonesData[key]['posHAS'] = posh
        #print("SetBonesASPositions: bone=%s, posHAS=%s" % (key, posh))


def calcBoneRotations(BonesDic):
    objDic = {}
    scn = bpy.context.scene
    #scn = Scene.GetCurrent()
    for bone in BonesDic.keys():
        #obj = Object.New('Empty',bone)
        obj = bpy.data.objects.new(bone, None)
        objDic[bone] = obj
        scn.objects.link(obj)
    #print("all objects created")
    #print(bpy.data.objects)
    for bone in BonesDic.keys():
        if 'parent' in BonesDic[bone]:
            #Parent = Object.Get(BonesDic[bone]['parent'])
            #print(BonesDic[bone]['parent'])
            Parent = objDic.get(BonesDic[bone]['parent'])
            object = objDic.get(bone)
            object.parent = Parent
            #Parent.makeParent([object])
    #print("all parents linked")
    for bone in BonesDic.keys():
        obj = objDic.get(bone)
        rot = BonesDic[bone]['rotation']
        loc = BonesDic[bone]['position']
        #print ("CreateEmptys:bone=%s, rot=%s" % (bone, rot))
        #print ("CreateEmptys:bone=%s, loc=%s" % (bone, loc))
        euler = Matrix.Rotation(rot[3], 3, Vector([rot[0], -rot[2], rot[1]])).to_euler()
        obj.location = [loc[0], -loc[2], loc[1]]
        #print ("CreateEmptys:bone=%s, euler=%s" % (bone, euler))
        #print ("CreateEmptys:bone=%s, obj.rotation_euler=%s" % (bone,[math.radians(euler[0]),math.radians(euler[1]),math.radians(euler[2])]))
        #obj.rotation_euler = [math.radians(euler[0]),math.radians(euler[1]),math.radians(euler[2])]
        #print ("CreateEmptys:bone=%s, obj.rotation_euler=%s" % (bone,[euler[0],euler[1],euler[2]])) # 02
        obj.rotation_euler = [euler[0], euler[1], euler[2]] # 02
    # Redraw()
    scn.update()
    # print("all objects rotated")
    for bone in BonesDic.keys():
        obj = objDic.get(bone)
        # TODO: need to get rotation matrix out of objects rotation
        # loc, rot, scale = obj.matrix_local.decompose()
        loc, rot, scale = obj.matrix_world.decompose() #02
        rotmatAS = rot.to_matrix()
        # print(rotmatAS)
        #obj.rotation_quaternion.
        #rotmatAS = Matrix(.matrix_local..getMatrix().rotationPart()
        BonesDic[bone]['rotmatAS'] = rotmatAS
        #print ("CreateEmptys:bone=%s, rotmatAS=%s" % (bone, rotmatAS))
    # print("all matrices stored")

    #for bone in BonesDic.keys():
    #    obj = objDic.get(bone)
    #    scn.objects.unlink(obj)
    #    del obj

    # TODO cyclic
    for bone in BonesDic.keys():
        obj = objDic.get(bone)
        #obj.select = True
        #bpy.ops.object.select_name(bone, False)
        #bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        scn.objects.unlink(obj) # TODO: cyclic message in console
        #del obj
        #bpy.context.scene.objects.unlink(obj)
        bpy.data.objects.remove(obj)

    scn.update()
    #removedObj = {}
    #children=1
    #while children > 0:
    #    children = 0
    #    for bone in BonesDic.keys():
    #        if('children' in BonesDic[bone].keys() and bone not in removedObj):
    #            if len(BonesDic[bone]['children'])==0:
    #                obj = objDic.get(bone)
    #                scn.objects.unlink(obj)
    #                del obj
    #                removedObj[bone]=True
    #            else:
    #                children+=1

    #print("all objects removed")

def VectorSum(vec1, vec2):
    vecout = [0, 0, 0]
    vecout[0] = vec1[0] + vec2[0]
    vecout[1] = vec1[1] + vec2[1]
    vecout[2] = vec1[2] + vec2[2]

    return vecout

## =========================================================================================== ##
def quaternionFromAngleAxis(angle, x, y, z):
    r = angle * 0.5
    s = math.sin(r)
    c = math.cos(r)
    return (c, x*s, y*s, z*s)


def xGetChild(node, tag):
    for n in node.childNodes:
        if n.nodeType == 1 and n.tagName == tag:
            return n
    return None


def xAnalyseFPS(xDoc):
    fps = 0
    lastTime = 1e8
    samples = 0
    for container in xDoc.getElementsByTagName('animations'):
        for animation in container.childNodes:
            if animation.nodeType == 1 and animation.tagName == 'animation':
                tracks = xGetChild(animation, 'tracks')
                for track in tracks.childNodes:
                    if track.nodeType == 1:
                        for keyframe in xGetChild(track, 'keyframes').childNodes:
                            if keyframe.nodeType == 1:
                                time = float(keyframe.getAttribute('time'))
                                if time > lastTime:
                                    fps = max(fps, 1 / (time - lastTime))
                                lastTime = time
                                samples = samples + 1
                                if samples > 100:
                                    return round(fps, 2)    # stop here
    return round(fps, 2)


def xCollectAnimations(meshData, xDoc):
    logger.info("* Collecting animation data...")

    if 'animations' not in meshData:
        meshData['animations'] = {}
    for container in xDoc.getElementsByTagName('animations'):
        for animation in container.childNodes:
            if animation.nodeType == 1 and animation.tagName == 'animation':
                name = animation.getAttribute('name')

                # read action data
                action = {}
                tracks = xGetChild(animation, 'tracks')
                xReadAnimation(action, tracks.childNodes)
                meshData['animations'][name] = action


def xReadAnimation(action, tracks):
    fps = bpy.context.scene.render.fps
    for track in tracks:
        if track.nodeType != 1:
            continue
        target = track.getAttribute('bone')
        action[target] = trackData = [[] for i in range(3)]  # pos, rot, scl
        for keyframe in xGetChild(track, 'keyframes').childNodes:
            if keyframe.nodeType != 1:
                continue
            time = float(keyframe.getAttribute('time'))
            frame = time * fps
            if config.get('ROUND_FRAMES'):
                frame = round(frame)
            for key in keyframe.childNodes:
                if key.nodeType != 1:
                    continue
                if key.tagName == 'translate':
                    x = float(key.getAttribute('x'))
                    y = float(key.getAttribute('y'))
                    z = float(key.getAttribute('z'))
                    trackData[0].append([frame, (x, y, z)])
                elif key.tagName == 'rotate':
                    axis = xGetChild(key, 'axis')
                    angle = key.getAttribute('angle')
                    x = axis.getAttribute('x')
                    y = axis.getAttribute('y')
                    z = axis.getAttribute('z')
                    # skip if axis contains #INF or #IND
                    if '#' not in x and '#' not in y and '#' not in z:
                        quat = quaternionFromAngleAxis(float(angle), float(z), float(x), float(y))
                        trackData[1].append([frame, quat])
                elif key.tagName == 'scale':
                    x = float(key.getAttribute('x'))
                    y = float(key.getAttribute('y'))
                    z = float(key.getAttribute('z'))
                    trackData[2].append([frame, (-x, z, y)])


def bCreateAnimations(meshData):
    path_id = ['location', 'rotation_quaternion', 'scale']

    if 'animations' in meshData:
        logger.info("+ Creating animations...")

        rig = meshData['rig']
        rig.animation_data_create()
        animdata = rig.animation_data

        # calculate transformation matrices for translation
        mat = {}
        fix1 = Matrix([(1, 0, 0), (0, 0, 1), (0, -1, 0)])
        fix2 = Matrix([(0, 1, 0), (0, 0, 1), (1, 0, 0)])
        for bone in rig.pose.bones:
            if bone.parent: 
            	mat[bone.name] = fix2 * bone.parent.matrix.to_3x3().transposed() * bone.matrix.to_3x3()
            else: 
            	mat[bone.name] = fix1 * bone.matrix.to_3x3()
        
        for name in sorted(meshData['animations'].keys(), reverse=True):
            action = bpy.data.actions.new(name)
            Report.armature_animations.append(name)
            
            # action.use_fake_user = True   # Dont need this as we are adding them to the nla editor
            logger.info("+ Created action: %s" % name)

            # Iterate target bones
            for target in meshData['animations'][name]:
                data = meshData['animations'][name][target]
                bone = rig.pose.bones[target]
                if not bone:
                    continue  # error
                bone.rotation_mode = 'QUATERNION'

                # Fix rotation inversions
                for i in range(1, len(data[1])):
                    a = data[1][i-1][1]
                    b = data[1][i][1]
                    dot = a[0]*b[0] + a[1]*b[1] + a[2]*b[2] + a[3]*b[3]
                    if dot < -0.8:
                        #print('fix inversion', name, target, i)
                        data[1][i][1] = (-b[0], -b[1], -b[2], -b[3])

                # Fix translation keys - rotate by inverse rest orientation
                m = mat[target].transposed()
                for i in range(0, len(data[0])):
                    v = Vector(data[0][i][1])
                    data[0][i][1] = m * v

                # Create fcurves
                for i in range(3):
                    if data[i]:
                        path = bone.path_from_id(path_id[i])
                        for channel in range(len(data[i][0][1])):
                            curve = action.fcurves.new(path, channel, bone.name)
                            for key in data[i]:
                                curve.keyframe_points.insert(key[0], key[1][channel])

            # Add action to NLA track
            track = animdata.nla_tracks.new()
            track.name = name
            track.mute = True
            track.strips.new(name, 0, action)


## =========================================================================================== ##


def bCreateMesh(meshData, folder, name, filepath):
    if 'skeleton' in meshData:
        skeletonName = meshData['skeletonName']
        bCreateSkeleton(meshData, skeletonName)

    logger.info("+ Creating mesh: %s" % name)
    
    # From collected data create all sub meshes
    subObjs = bCreateSubMeshes(meshData, name)
    # Skin submeshes
    #bSkinMesh(subObjs)
    
    # Move to parent skeleton if there
    if 'armature' in meshData:
        arm = meshData['armature']
        for obj in subObjs:
            logger.debug('Move to %s' % arm.location)
            obj.location = arm.location
            obj.rotation_euler = arm.rotation_euler
            obj.rotation_axis_angle = arm.rotation_axis_angle
            obj.rotation_quaternion = arm.rotation_quaternion

    bpy.ops.object.select_all(action='DESELECT')

    # Temporarily select all imported objects
    for subOb in subObjs:
        subOb.select = True
    
    # TODO: Try to merge everything into the armature object
    if config.get('MERGE_SUBMESHES') == True:
        #bpy.context.scene.objects.active = bpy.data.objects["Cube"]
        bpy.ops.object.join()
        ob = bpy.context.scene.objects.active
        ob.name = name
        ob.data.name = name

    if SHOW_IMPORT_DUMPS:
        importDump = filepath + "IDump"
        fileWr = open(importDump, 'w')
        fileWr.write(str(meshData))
        fileWr.close()


def bCreateSkeleton(meshData, name):
    if 'skeleton' not in meshData:
        return
    bonesData = meshData['skeleton']
    
    logger.info("+ Creating skeleton: %s" % name)

    # Create Armature
    amt = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, amt)
    meshData['rig'] = rig
    #rig.location = origin
    rig.show_x_ray = True
    #amt.show_names = True
    # Link object to scene
    scn = bpy.context.scene
    scn.objects.link(rig)
    scn.objects.active = rig
    scn.update()
    
    # Chose default length of bones with no children
    averageBone = 0
    for b in bonesData.values():
        childLength = b['position'][0]
        averageBone += childLength
    averageBone /= len(bonesData)
    if averageBone == 0:
        averageBone = 0.2
    logger.debug("Default bone length: %s" % averageBone)

    bpy.ops.object.mode_set(mode='EDIT')
    for bone in bonesData.keys():
        boneData = bonesData[bone]
        boneName = boneData['name']

        children = boneData['children']
        boneObj = amt.edit_bones.new(boneName)

        # Store Ogre bone id to match when exporting
        if 'id' in boneData:
            boneObj['OGREID'] = boneData['id']
            logger.debug("BoneID: %s, BoneName: %s" % (boneData['id'], boneName))

        # boneObj.head = boneData['posHAS']
        # headPos = boneData['posHAS']
        headPos = boneData['posHAS']
        tailVector = 0
        if len(children) > 0:
            for child in children:
                tailVector = max(tailVector, bonesData[child]['position'][0])
        if tailVector < MIN_BONE_LENGTH:
            tailVector = averageBone

        #boneObj.head = Vector([headPos[0], -headPos[2], headPos[1]])
        #boneObj.tail = Vector([headPos[0], -headPos[2], headPos[1] + tailVector])

        #print("bCreateSkeleton: bone=%s, boneObj.head=%s" % (bone, boneObj.head))
        #print("bCreateSkeleton: bone=%s, boneObj.tail=%s" % (bone, boneObj.tail))
        #boneObj.matrix =
        rotmat = boneData['rotmatAS']
        #print(rotmat[1].to_tuple())
        #boneObj.matrix = Matrix(rotmat[1],rotmat[0],rotmat[2])
        if blender_version <= 262:
            r0 = [rotmat[0].x] + [rotmat[0].y] + [rotmat[0].z]
            r1 = [rotmat[1].x] + [rotmat[1].y] + [rotmat[1].z]
            r2 = [rotmat[2].x] + [rotmat[2].y] + [rotmat[2].z]
            boneRotMatrix = Matrix((r1, r0, r2))
        elif blender_version > 262:
            # this is fugly way of flipping matrix
            r0 = [rotmat.col[0].x] + [rotmat.col[0].y] + [rotmat.col[0].z]
            r1 = [rotmat.col[1].x] + [rotmat.col[1].y] + [rotmat.col[1].z]
            r2 = [rotmat.col[2].x] + [rotmat.col[2].y] + [rotmat.col[2].z]
            tmpR = Matrix((r1, r0, r2))
            boneRotMatrix = Matrix((tmpR.col[0], tmpR.col[1], tmpR.col[2]))

        #pos = Vector([headPos[0],-headPos[2],headPos[1]])
        #axis, roll = mat3_to_vec_roll(boneRotMatrix.to_3x3())

        #boneObj.head = pos
        #boneObj.tail = pos + axis
        #boneObj.roll = roll

        #print("bCreateSkeleton: bone=%s, newrotmat=%s" % (bone, Matrix((r1,r0,r2))))
        #print(r1)
        #mtx = Matrix.to_3x3()Translation(boneObj.head) # Matrix((r1,r0,r2))
        #boneObj.transform(Matrix((r1,r0,r2)))
        #print("bCreateSkeleton: bone=%s, matrix_before=%s" % (bone, boneObj.matrix))
        #boneObj.use_local_location = False
        #boneObj.transform(Matrix((r1,r0,r2)) , False, False)
        #print("bCreateSkeleton: bone=%s, matrix_after=%s" % (bone, boneObj.matrix))
        boneObj.head = Vector([0, 0, 0])
        #boneObj.tail = Vector([0,0,tailVector])
        boneObj.tail = Vector([0, tailVector, 0])
        #matx = Matrix.Translation(Vector([headPos[0],-headPos[2],headPos[1]]))

        boneObj.transform(boneRotMatrix)
        #scn.update()
        boneObj.translate(Vector([headPos[0], -headPos[2], headPos[1]]))
        #scn.update()
        #boneObj.translate(Vector([headPos[0],-headPos[2],headPos[1]]))
        #boneObj.head = Vector([headPos[0],-headPos[2],headPos[1]])
        #boneObj.tail = Vector([headPos[0],-headPos[2],headPos[1]]) + (Vector([0,0, tailVector])  * Matrix((r1,r0,r2)))

        #amt.bones[bone] = boneObj
        #amt.update_tag(refresh)

    # Only after all bones are created we can link parents
    for bone in bonesData.keys():
        boneData = bonesData[bone]
        parent = None
        if 'parent' in boneData.keys():
            parent = boneData['parent']
            # get bone obj
            boneData = bonesData[bone]
            boneName = boneData['name']
            boneObj = amt.edit_bones[boneName]
            boneObj.parent = amt.edit_bones[parent]

    # Need to refresh armature before removing bones
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')

    # Delete helper/zero bones
    for bone in amt.bones.keys():
        # print("keys of bone=%s" % bonesData[bone].keys())
        if 'flag' in bonesData[bone].keys():
            # print ("deleting bone=%s" % bone)
            bpy.context.object.data.edit_bones.remove(amt.edit_bones[bone])

    bpy.ops.object.mode_set(mode='OBJECT')
    #for (bname, pname, vector) in boneTable:
    #    bone = amt.edit_bones.new(bname)
    #    if pname:
    #        parent = amt.edit_bones[pname]
    #        bone.parent = parent
    #        bone.head = parent.tail
    #        bone.use_connect = False
    #        (trans, rot, scale) = parent.matrix.decompose()
    #    else:
    #        bone.head = (0,0,0)
    #        rot = Matrix.Translation((0,0,0))    # identity matrix
    #    bone.tail = rot * Vector(vector) + bone.head
    #bpy.ops.object.mode_set(mode='OBJECT')

def bMergeVertices(subMesh):
    # This sort of works, but leaves all uv seams as sharp.
    geometry = subMesh['geometry']
    vertices = geometry['positions']
    normals = geometry['normals']
    uvsets = geometry['uvsets'] if 'uvsets' in geometry else None
    lookup = {}
    map = [i for i in range(len(vertices))]
    for i in range(len(vertices)):
        vert = vertices[i]
        norm = normals[i]
        uv = tuple(uvsets[i][0]) if uvsets else None
        item = (tuple(vert), tuple(norm), uv)
        target = lookup.get(item)
        if target is None:
            lookup[item] = i
        else:
            map[i] = target
    # update faces
    faces = subMesh['faces']
    for face in faces:
        for i in range(len(face)):
            face[i] = map[face[i]]


def bCreateSubMeshes(meshData, meshName):
    allObjects = []
    submeshes = meshData['submeshes']
    scene = bpy.context.scene

    for subMeshIndex in range(len(submeshes)):
        subMeshData = submeshes[subMeshIndex]
        subMeshName = subMeshData['material']
        Report.meshes.append( subMeshName )
        
        # Create mesh and object
        me = bpy.data.meshes.new(subMeshName)
        ob = bpy.data.objects.new(subMeshName, me)

        # Link object to scene
        scene = bpy.context.scene
        scene.objects.link(ob)
        scene.objects.active = ob
        scene.update()

        # Check for submesh geometry, or take the shared one
        if 'geometry' in subMeshData.keys():
            geometry = subMeshData['geometry']
        else:
            geometry = meshData['sharedgeometry']

        verts = geometry['positions']
        faces = subMeshData['faces']
        
        hasNormals = False
        if 'normals' in geometry.keys():
            normals = geometry['normals']
            hasNormals = True
        # Mesh vertices and faces

        if(blender_version <= 262):
            # Vertices and faces of mesh
            me.from_pydata(verts, [], faces)
            # Mesh normals
            c = 0
            for v in me.vertices:
                if hasNormals:
                    v.normal = Vector((normals[c][0], normals[c][1], normals[c][2]))
                    c += 1
        elif(blender_version > 262):
            # Vertices and faces of mesh
            VertLength = len(verts)
            FaceLength = len(faces)
            me.vertices.add(VertLength)
            me.tessfaces.add(FaceLength)
            for i in range(VertLength):
                me.vertices[i].co = verts[i]
                if hasNormals:
                    me.vertices[i].normal = Vector((normals[i][0], normals[i][1], normals[i][2]))
            #me.vertices[VertLength].co = verts[0]
            for i in range(FaceLength):
                NewFace = (faces[i][0], faces[i][1], faces[i][2], 0)
                me.tessfaces[i].vertices_raw = NewFace

        # Blender 2.62 <-> 2.63 compatibility
        if(blender_version <= 262):
            meshFaces = me.faces
            meshUV_textures = me.uv_textures
            meshVertex_colors = me.vertex_colors
        elif(blender_version > 262):
            meshFaces = me.tessfaces
            meshUV_textures = me.tessface_uv_textures
            meshVertex_colors = me.tessface_vertex_colors
            #meshUV_textures = me.uv_textures

        # Smooth
        for f in meshFaces:
            f.use_smooth = True

        hasTexture = False
        # Material for the submesh
        # Create image texture from image.
        if subMeshName in meshData['materials']:
            matInfo = meshData['materials'][subMeshName]  # material data
            Report.materials.append( subMeshName )
            
            if 'texture' in matInfo:
                texturePath = matInfo['texture']
                if texturePath:
                    hasTexture = True
                    Report.textures.append( matInfo['imageNameOnly'] )
                    
                    # Try to find among already loaded images
                    tex = None
                    for lTex in bpy.data.textures:
                        if lTex.type == 'IMAGE':
                            if lTex.image.name == matInfo['imageNameOnly']:
                                tex = lTex
                                break
                    if not tex:
                        tex = bpy.data.textures.new(matInfo['imageNameOnly'], type='IMAGE')
                        tex.image = bpy.data.images.load(texturePath)
                        tex.use_alpha = True

            # Create shadeless material and MTex
            mat = bpy.data.materials.new(subMeshName)
            # Ambient
            if 'ambient' in matInfo:
                #mat.ambient = matInfo['ambient'][0]
                # RGB to Grayscale Weighted method or luminosity method: ( (0.3 * R) + (0.59 * G) + (0.11 * B) )
                if len(matInfo['ambient']) == 3:
                    mat.ambient = (matInfo['ambient'][0] * 0.2126 + matInfo['ambient'][1] * 0.7152 + matInfo['ambient'][2] * 0.0722);
                else:
                    mat.ambient = (matInfo['ambient'][0] * 0.2126 + matInfo['ambient'][1] * 0.7152 + matInfo['ambient'][2] * 0.0722) * matInfo['ambient'][3];
            else:
                mat.ambient = 1.0

            # Diffuse
            if 'diffuse' in matInfo:
                mat.diffuse_color = matInfo['diffuse'][0:3]
            else:
                mat.diffuse_color = [1.0, 1.0, 1.0]

            # Specular
            if 'specular' in matInfo:
                mat.specular_color = matInfo['specular'][0:3]
                
                # RGB to Grayscale Weighted method or luminosity method: ( (0.3 * R) + (0.59 * G) + (0.11 * B) )
                mat.specular_intensity = (matInfo['specular'][0] * 0.2126 + matInfo['specular'][1] * 0.7152 + matInfo['specular'][2] * 0.0722);

                if len(matInfo['specular']) == 4:
                    if matInfo['specular'][3] <= 1:
                        mat.specular_intensity = (matInfo['specular'][0] * 0.2126 + matInfo['specular'][1] * 0.7152 + matInfo['specular'][2] * 0.0722) * matInfo['specular'][3];
                    else:
                        mat.specular_hardness = matInfo['specular'][3] * 4

                elif len(matInfo['specular']) == 5:
                    mat.specular_hardness = matInfo['specular'][4] * 4
                    
            else:
                mat.specular_color = [0.0, 0.0, 0.0]

            # Emmisive
            if 'emissive' in matInfo:
                mat.emit = matInfo['emissive'][0]
                #mat.emit = matInfo['emissive'][0]
                # RGB to Grayscale Weighted method or luminosity method: ( (0.3 * R) + (0.59 * G) + (0.11 * B) )
                if len(matInfo['emissive']) == 3:
                    mat.emit = (matInfo['emissive'][0] * 0.2126 + matInfo['emissive'][1] * 0.7152 + matInfo['emissive'][2] * 0.0722);
                else:
                    mat.emit = (matInfo['emissive'][0] * 0.2126 + matInfo['emissive'][1] * 0.7152 + matInfo['emissive'][2] * 0.0722) * matInfo['emissive'][3];
            else:
                mat.emit = 0.0

            #mat.use_shadeless = True
            
            if 'vertexcolour' in matInfo:
                mat.use_vertex_color_paint = True
            
            if 'depth_bias' in matInfo:
                mat.offset_z = matInfo['depth_bias']
            
            if 'receive_shadows' in matInfo:
                mat.use_shadows = matInfo['receive_shadows']

            mtex = mat.texture_slots.add()
            if hasTexture:
                mtex.texture = tex
            mtex.texture_coords = 'UV'
            mtex.use_map_color_diffuse = True

            # Add material to object
            ob.data.materials.append(mat)
            # logger.debug(me.uv_textures[0].data.values()[0].image)
        else:
            logger.warning("Definition of material: %s not found!" % subMeshName)
            Report.warnings.append("Definition of material: %s not found!" % subMeshName)

        # Texture coordinates
        if 'texcoordsets' in geometry and 'uvsets' in geometry:
            uvsets = geometry['uvsets']
            for j in range(geometry['texcoordsets']):
                uvLayer = meshUV_textures.new('UVLayer'+str(j))

                meshUV_textures.active = uvLayer

                for f in meshFaces:
                    uvco1sets = uvsets[f.vertices[0]]
                    uvco2sets = uvsets[f.vertices[1]]
                    uvco3sets = uvsets[f.vertices[2]]
                    uvco1 = Vector((uvco1sets[j][0], uvco1sets[j][1]))
                    uvco2 = Vector((uvco2sets[j][0], uvco2sets[j][1]))
                    uvco3 = Vector((uvco3sets[j][0], uvco3sets[j][1]))
                    uvLayer.data[f.index].uv = (uvco1, uvco2, uvco3)
                    if hasTexture:
                        # This will link image to faces
                        uvLayer.data[f.index].image = tex.image
                        # uvLayer.data[f.index].use_image=True

        # Vertex colors
        if 'vertexcolors' in geometry:
            colorLayer = meshVertex_colors.new('Colour')
            meshVertex_colors.active = colorLayer
            vcolors = geometry['vertexcolors']
            for f in meshFaces:
                colv1 = vcolors[f.vertices[0]]
                colv2 = vcolors[f.vertices[1]]
                colv3 = vcolors[f.vertices[2]]
                colorLayer.data[f.index].color1 = (colv1[0], colv1[1], colv1[2])
                colorLayer.data[f.index].color2 = (colv2[0], colv2[1], colv2[2])
                colorLayer.data[f.index].color3 = (colv3[0], colv3[1], colv3[2])
            
            # Vertex Alpha
            for c in vcolors:
                if c[3] != 1.0:
                    alphaLayer = meshVertex_colors.new('Alpha')
                    for f in meshFaces:
                        a1 = vcolors[f.vertices[0]][3]
                        a2 = vcolors[f.vertices[1]][3]
                        a3 = vcolors[f.vertices[2]][3]
                        alphaLayer.data[f.index].color1 = (a1, a1, a1)
                        alphaLayer.data[f.index].color2 = (a2, a2, a2)
                        alphaLayer.data[f.index].color3 = (a3, a3, a3)
                    break

        # Bone assignments:
        if 'boneIDs' in meshData:
            if 'boneassignments' in geometry.keys():
                vgroups = geometry['boneassignments']
                for vgname, vgroup in vgroups.items():
                    # logger.debug("creating VGroup %s" % vgname)
                    grp = ob.vertex_groups.new(vgname)
                    for (v, w) in vgroup:
                        #grp.add([v], w, 'REPLACE')
                        grp.add([v], w, 'ADD')
                        
        # Give mesh object an armature modifier, using vertex groups but not envelopes
        if 'skeleton' in meshData:
            skeletonName = meshData['skeletonName']
            Report.armatures.append(skeletonName)
            
            mod = ob.modifiers.new('OgreSkeleton', 'ARMATURE')
            mod.object = bpy.data.objects[skeletonName]  # gets the rig object
            mod.use_bone_envelopes = False
            mod.use_vertex_groups = True

        elif 'armature' in meshData:
            mod = ob.modifiers.new('OgreSkeleton', 'ARMATURE')
            mod.object = meshData['armature']
            mod.use_bone_envelopes = False
            mod.use_vertex_groups = True

        # Shape keys (poses)
        if 'poses' in meshData:
            base = None
            for pose in meshData['poses']:
                if(pose['submesh'] == subMeshIndex):
                    if base is None:
                        # Must have base shape
                        base = ob.shape_key_add('Basis')
                    name = pose['name']
                    Report.shape_animations.append(name)
                    
                    logger.info('* Creating pose', name)
                    shape = ob.shape_key_add(name)
                    for vkey in pose['data']:
                        b = base.data[vkey[0]].co
                        me.shape_keys.key_blocks[name].data[vkey[0]].co = [
                            vkey[1] + b[0], vkey[2] + b[1], vkey[3] + b[2]]

        # Update mesh with new data
        me.update(calc_edges=True)
        me.use_auto_smooth = True

        Report.orig_vertices = len( me.vertices )

        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.remove_doubles(threshold=0.001)
        bpy.ops.object.editmode_toggle()

        # Update mesh with new data
        me.update(calc_edges=True, calc_tessface=True)

        Report.faces += len( me.tessfaces )
        Report.triangles += len( me.tessfaces )
        Report.vertices += len( me.vertices )

        # Try to set custom normals
        if hasNormals:
            noChange = len(me.loops) == len(faces) * 3
            if not noChange:
                logger.debug('Removed %s faces' % (len(faces) - len(me.loops) / 3))
            split = []
            polyIndex = 0
            for face in faces:
                if noChange or matchFace(face, verts, me, polyIndex):
                    polyIndex += 1
                    for vx in face:
                        split.append(normals[vx])

            if len(split) == len(me.loops):
                me.normals_split_custom_set(split)
            else:
                Report.warnings.append("Failed to import mesh normals")
                logger.warning('Failed to import mesh normals %s / %s', (polyIndex, len(me.polygons)))

        allObjects.append(ob)

    # Forced view mode with textures
    #if TEXTURE_VIEW_MODE:
    #    bpy.context.scene.game_settings.material_mode = 'GLSL'
    #    areas = bpy.context.screen.areas
    #    for area in areas:
    #        if area.type == 'VIEW_3D':
    #            area.spaces.active.viewport_shade = 'TEXTURED'

    return allObjects


def matchFace(face, vertices, mesh, index):
    if index >= len(mesh.polygons):
        return False  # ?? err - what broke
    loop = mesh.polygons[index].loop_start
    for v in face:
        vi = mesh.loops[loop].vertex_index
        vx = mesh.vertices[vi].co

        if (vx-Vector(vertices[v])).length_squared > 1e-6:
            return False

        # if vx != Vector(vertices[v]):
        #    return False  # May need threshold ?
        loop += 1
    return True


def getBoneNameMapFromArmature(arm):
        # Get Ogre bone IDs - need to be in edit mode to access edit_bones
        # Arm should already be the active object
        boneMap = {}
        bpy.context.scene.objects.active = arm
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        for bone in arm.data.edit_bones:
            if 'OGREID' in bone:
                boneMap[ str(bone['OGREID']) ] = bone.name;
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        return boneMap

def load(filepath):
    global blender_version

    blender_version = bpy.app.version[0] * 100 + bpy.app.version[1]

    logger.info("* Loading mesh from: %s" % str(filepath))

    filepath = filepath
    pathMeshXml = filepath
    # Get the mesh as .xml file
    if filepath.lower().endswith(".mesh"):
        if mesh_convert(filepath):
            pathMeshXml = filepath + ".xml"
        else:
            logger.error("Failed to convert .mesh file %s to .xml" % filepath)
            Report.errors.append("Failed to convert .mesh file to .xml")
            return {'CANCELLED'}
    elif filepath.lower().endswith(".xml"):
        pathMeshXml = filepath
    else:
        return {'CANCELLED'}

    folder = os.path.split(filepath)[0]
    nameDotMeshDotXml = os.path.split(pathMeshXml)[1]
    nameDotMesh = os.path.splitext(nameDotMeshDotXml)[0]
    onlyName = os.path.splitext(nameDotMesh)[0]

    # Material
    meshMaterials = []
    nameDotMaterial = onlyName + ".material"
    pathMaterial = os.path.join(folder, nameDotMaterial)
    if not os.path.isfile(pathMaterial):
        # Search directory for .material
        for filename in os.listdir(folder):
            if ".material" in filename:
                # Material file
                pathMaterial = os.path.join(folder, filename)
                meshMaterials.append(pathMaterial)
                # logger.info("alternative material file: %s" % pathMaterial)
    else:
        meshMaterials.append(pathMaterial)

    # Try to parse xml file
    xDocMeshData = xOpenFile(pathMeshXml)

    meshData = {}
    if xDocMeshData != "None":
        # Skeleton data
        # Get the mesh as .xml file
        skeletonFile = xGetSkeletonLink(xDocMeshData, folder)

        # Use selected skeleton
        selectedSkeleton = bpy.context.active_object \
            if (config.get('USE_SELECTED_SKELETON')
                and bpy.context.active_object
                and bpy.context.active_object.type == 'ARMATURE') else None
        if selectedSkeleton:
            map = getBoneNameMapFromArmature(selectedSkeleton)
            if map:
                meshData['boneIDs'] = map
                meshData['armature'] = selectedSkeleton
            else:
                Report.warnings.append("Selected armature has no OGRE data.")
        
        # There is valid skeleton link and existing file
        elif skeletonFile != "None":
            if mesh_convert(skeletonFile):
                skeletonFileXml = skeletonFile + ".xml"

                # Parse .xml skeleton file
                xDocSkeletonData = xOpenFile(skeletonFileXml)
                if xDocSkeletonData != "None":
                    xCollectBoneData(meshData, xDocSkeletonData)
                    meshData['skeletonName'] = os.path.basename(skeletonFile[:-9])

                    # Parse animations
                    if config.get('IMPORT_ANIMATIONS'):
                        fps = xAnalyseFPS(xDocSkeletonData)
                        if(fps and config.get('ROUND_FRAMES')):
                            logger.info(" * Setting FPS to %s" % fps)
                            bpy.context.scene.render.fps = fps
                        xCollectAnimations(meshData, xDocSkeletonData)

            else:
                Report.warnings.append("Failed to load linked skeleton")
                logger.warning("Failed to load linked skeleton")

        # Collect mesh data
        xCollectMeshData(meshData, xDocMeshData, onlyName, folder)
        MaterialParser.xCollectMaterialData(meshData, onlyName, folder)
        
        if config.get('IMPORT_SHAPEKEYS'):
            xCollectPoseData(meshData, xDocMeshData)

        # After collecting is done, start creating stuff#
        # Create skeleton (if any) and mesh from parsed data
        bCreateMesh(meshData, folder, onlyName, pathMeshXml)
        bCreateAnimations(meshData)
        if config.get('XML_DELETE'):
            # Cleanup by deleting the XML file we created
            os.unlink("%s" % pathMeshXml)
            if 'skeleton' in meshData:
                os.unlink("%s" % skeletonFileXml)

    return {'FINISHED'}
