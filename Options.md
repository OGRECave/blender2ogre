
# `blender2ogre` Options

## Index
 - [Exporter](#exporter)
   - [Exporter Options](#exporter-options)
   - [Exporter Script](#exporter-script)
 - [Importer](#importer)
   - [Importer Options](#importer-options)
   - [Importer Script](#importer-script)

## Exporter

### Exporter Options
Option|Name|Description|Default Value
|---|---|---|---|
|**General**|
|EX_SWAP_AXIS|Swap Axis|Axis swapping mode|'xyz'|
|EX_V2_MESH_TOOL_VERSION|Mesh Export Version|Specify Ogre version format to write|'v2'|
|EX_XML_DELETE|Clean up xml files|Remove the generated xml files after binary conversion.[^1]|True|
|**Scene**|
|EX_SCENE|Export Scene|Export current scene (OgreDotScene xml file)|True|
|EX_SELECTED_ONLY|Export Selected Only|Export only selected objects. Turn on to avoid exporting non-selected stuff|True|
|EX_EXPORT_HIDDEN|Export Hidden Also|Export hidden meshes in addition to visible ones. Turn off to avoid exporting hidden stuff|True|
|EX_EXPORT_USER|Export User Properties|Export user properties such as as physical properties. Turn off to avoid exporting the user data|True|
|EX_FORCE_CAMERA|Force Camera|Export active camera|True|
|EX_FORCE_LAMPS|Force Lamps|Export all Lamps|True|
|EX_NODE_ANIMATION|Export Node Animations|Export Node Animations, these are animations of the objects properties like position, rotation and scale|True|
|**Materials**|
|EX_MATERIALS|Export Materials|Exports .material scripts|True|
|EX_SEPARATE_MATERIALS|Separate Materials|Exports a .material for each material (rather than putting all materials into a single .material file)|True|
|EX_COPY_SHADER_PROGRAMS|Copy Shader Programs|When using script inheritance copy the source shader programs to the output path|True|
|EX_USE_FFP_PARAMETERS|Fixed Function Parameters|Convert material parameters to Blinn-Phong model|False|
|**Textures**|
|EX_DDS_MIPS|DDS Mips|Number of Mip Maps (DDS)|16|
|EX_FORCE_IMAGE_FORMAT|Convert Images|Convert all textures to selected image format|'NONE'|
|**Armature**|
|EX_ARMATURE_ANIMATION|Armature Animation|Export armature animations (updates the .skeleton file)|True|
|EX_SHARED_ARMATURE|Shared Armature|Export a single .skeleton file for objects that have the same Armature parent[^2]|False|
|EX_ONLY_KEYFRAMES|Only Keyframes|Only export Keyframes.[^3]|False|
|EX_ONLY_DEFORMABLE_BONES|Only Deformable Bones|Only exports bones that are deformable.[^4]|False|
|EX_ONLY_KEYFRAMED_BONES|Only Keyframed Bones|Only exports bones that have been keyframed for a given animation. Useful to limit the set of bones on a per-animation basis|False|
|EX_OGRE_INHERIT_SCALE|OGRE Inherit Scale|Whether the OGRE bones have the 'inherit scale' flag on.[^5]|False|
|EX_TRIM_BONE_WEIGHTS|Trim Weights|Ignore bone weights below this value (Ogre supports 4 bones per vertex)|0.01|
|**Mesh Options**|
|EX_MESH|Export Meshes|Export meshes|True|
|EX_MESH_OVERWRITE|Export Meshes (overwrite)|Export meshes (overwrite existing files)|True|
|EX_ARRAY|Optimise Arrays|Optimise array modifiers as instances (constant offset only)|True|
|EX_V1_EXTREMITY_POINTS|Extremity Points|[^6]|0|
|EX_Vx_GENERATE_EDGE_LISTS|Generate Edge Lists|Generate Edge Lists (for Stencil Shadows)|False|
|EX_GENERATE_TANGENTS|Tangents|Export tangents generated by Blender[^7]|0|
|EX_Vx_OPTIMISE_ANIMATIONS|Optimise Animations|DON"T optimise out redundant tracks & keyframes|True|
|EX_V2_OPTIMISE_VERTEX_BUFFERS|Optimise Vertex Buffers For Shaders|Optimise vertex buffers for shaders.[^8]|True|
|EX_V2_OPTIMISE_VERTEX_BUFFERS_OPTIONS|Vertex Buffers Options|Used when optimizing vertex buffers for shaders.[^9]|'puqs'|
|**LOD**|
|EX_LOD_LEVELS|LOD Levels|Number of LOD levels|0|
|EX_LOD_DISTANCE|LOD Distance|Distance increment to reduce LOD|300|
|EX_LOD_PERCENT|LOD Percentage|LOD percentage reduction|40|
|EX_LOD_MESH_TOOLS|Use OgreMesh Tools|Use OgreMeshUpgrader/OgreMeshTool instead of Blender to generate the mesh LODs.[^10]|False|
|**Pose Animation**|
|EX_SHAPE_ANIMATIONS|Shape Animation|Export shape animations (updates the .mesh file)|True|
|EX_SHAPE_NORMALS|Shape Normals|Export normals in shape animations (updates the .mesh file)|True|
|**Logging**|
|EX_Vx_ENABLE_LOGGING|Write Exporter Logs|Write Log file to the output directory (blender2ogre.log)|False|
|EX_Vx_DEBUG_LOGGING|Debug Logging|Whether to show DEBUG log messages|False|

[^1]: The removal will only happen if OgreXMLConverter/OgreMeshTool finishes successfully
[^2]: This is useful for using with: `shareSkeletonInstanceWith()`
  NOTE: The name of the.skeleton file will be that of the Armature
[^3]: Exported animation won't be affected by Inverse Kinematics, Drivers and modified F-Curves
[^4]: Useful for hiding IK-Bones used in Blender.
  NOTE: Any bone with deformablechildren/descendants will be output as well
[^5]: If the animation has scale in it, the exported animation needs to be adjusted to account for the state of the inherit-scale flag in OGRE
[^6]: Submeshes can have optional "extremity points" stored with them to allow submeshes to be sorted with respect to each other in the case of transparency.
  For some meshes with transparent materials (partial transparency) this can be useful
[^7]: Options:
  '0': Do not export
  '3': Generate
  '4': Generate with parity
[^8]: See Vertex Buffers Options for more settings
[^9]: Available flags are:
  p - converts POSITION to 16-bit floats.
  q - converts normal tangent and bitangent (28-36 bytes) to QTangents (8 bytes).
  u - converts UVs to 16-bit floats.
  s - make shadow mapping passes have their own optimised buffers. Overrides existing ones if any.
  S - strips the buffers for shadow mapping (consumes less space and memory)
[^10]: OgreMeshUpgrader/OgreMeshTool does LOD by removing edges, which allows only changing the index buffer and re-use the vertex-buffer (storage efficient).
  Blenders decimate does LOD by collapsing vertices, which can result in a visually better LOD, but needs different vertex-buffers per LOD.

### Exporter Script
This is an example exporting script with all the options and their default values

```python
import bpy

bpy.ops.ogre.export(
filepath="D:\\tmp\\NormalsExport\\blender2ogre.scene", 

# General
EX_SWAP_AXIS='xz-y', 
# - 'xyz': No swapping
# - 'xz-y'OGRE Standard
# - '-xzy': Non standard
EX_V2_MESH_TOOL_VERSION='v2', 
# - 'v1': Export the mesh as a v1 object
# - 'v2': Export the mesh as a v2 object
EX_XML_DELETE=True, 

# Scene
EX_SCENE=True, 
EX_SELECTED_ONLY=True, 
EX_EXPORT_HIDDEN=True, 
EX_FORCE_CAMERA=True, 
EX_FORCE_LAMPS=True, 
EX_NODE_ANIMATION=True, 

# Materials
EX_MATERIALS=True, 
EX_SEPARATE_MATERIALS=True, 
EX_COPY_SHADER_PROGRAMS=True, 

# Textures
EX_DDS_MIPS=16, 
EX_FORCE_IMAGE_FORMAT='NONE', 

# Armature
EX_ARMATURE_ANIMATION=True, 
EX_SHARED_ARMATURE=False, 
EX_ONLY_KEYFRAMES=False, 
EX_ONLY_DEFORMABLE_BONES=False, 
EX_ONLY_KEYFRAMED_BONES=False, 
EX_OGRE_INHERIT_SCALE=False, 
EX_TRIM_BONE_WEIGHTS=0.01, 

# Mesh Options
EX_MESH=True, 
EX_MESH_OVERWRITE=True, 
EX_ARRAY=True,
EX_V1_EXTREMITY_POINTS=0, 
EX_Vx_GENERATE_EDGE_LISTS=False, 
EX_GENERATE_TANGENTS='0', 
# - '0': Do not export
# - '3': Generate
# - '4': Generate with parity
EX_Vx_OPTIMISE_ANIMATIONS=True, 
EX_V2_OPTIMISE_VERTEX_BUFFERS=True, 
EX_V2_OPTIMISE_VERTEX_BUFFERS_OPTIONS="puqs", 

# LOD
EX_LOD_LEVELS=0, 
EX_LOD_DISTANCE=300, 
EX_LOD_PERCENT=40, 
EX_LOD_MESH_TOOLS=False, 

# Pose Animation
EX_SHAPE_ANIMATIONS=True, 
EX_SHAPE_NORMALS=True, 

# Logging
EX_Vx_ENABLE_LOGGING=True,
EX_Vx_DEBUG_LOGGING=True
)
```

## Importer

### Importer Options
Option|Name|Description|Default Value
|---|---|---|---|
|**General**|
|IM_SWAP_AXIS|Swap Axis|Axis swapping mode|'xyz'|
|IM_V2_MESH_TOOL_VERSION|Mesh Import Version|Specify Ogre version format to read|'v2'|
|IM_XML_DELETE|Clean up xml files|Remove the generated xml files after binary conversion.[^11]|True|
|**Mesh**|
|IM_IMPORT_NORMALS|Import Normals|Import custom mesh normals|True|
|IM_MERGE_SUBMESHES|Merge Submeshes|Whether to merge submeshes to form a single mesh with different materials|True|
|**Armature**|
|IM_IMPORT_ANIMATIONS|Import animation|Import animations as actions|True|
|IM_ROUND_FRAMES|Adjust frame rate|Adjust scene frame rate to match imported animation|True|
|IM_USE_SELECTED_SKELETON|Use selected skeleton|Link with selected armature object rather than importing a skeleton.[^12]|True|
|**Shape Keys**|
|IM_IMPORT_SHAPEKEYS|Import shape keys|Import shape keys (morphs)|True|
|**Logging**|
|IM_Vx_ENABLE_LOGGING|Write Importer Logs|Write Log file to the output directory (blender2ogre.log)|False|

[^11]: The removal will only happen if OgreXMLConverter/OgreMeshTool finishes successfully
[^12]: Use this for importing skinned meshes that don't have their own skeleton.
  Make sure you have the correct skeleton selected or the weight maps may get mixed up.

### Importer Script
This is an example importing script with all the options and their default values

```python
import bpy

bpy.ops.ogre.import_mesh(
filepath="D:\\tmp\\NormalsExport\\Suzanne.mesh", 

# General
IM_SWAP_AXIS='xz-y',            # Axis swapping mode
IM_V2_MESH_TOOL_VERSION='v2',   # Specify Ogre version format to read
IM_XML_DELETE=True,             # Remove the generated xml files after binary conversion.

# Mesh
IM_IMPORT_NORMALS=True,         # Import custom mesh normals
IM_MERGE_SUBMESHES=True,        # Whether to merge submeshes to form a single mesh with different materials

# Armature
IM_IMPORT_ANIMATIONS=True,      # Import animations as actions
IM_ROUND_FRAMES=True,           # Adjust scene frame rate to match imported animation
IM_USE_SELECTED_SKELETON=True,  # Link with selected armature object rather than importing a skeleton

# Shape Keys
IM_IMPORT_SHAPEKEYS=True,       # Import shape keys (morphs)

# Logging
IM_Vx_ENABLE_LOGGING=True       # Write Log file to the output directory (blender2ogre.log)
)
```