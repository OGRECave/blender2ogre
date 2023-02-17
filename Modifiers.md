
# Blender Modifiers
Modifiers are automatic operations that affect an object’s geometry in a non-destructive way. 
With modifiers, you can perform many effects automatically that would otherwise be too tedious to do manually 
(such as subdivision surfaces) and without affecting the base geometry of your object.

`blender2ogre` supports exporting meshes with modifiers, but not all modifiers are supported.
Also, some modifiers have special treatment (Array and Armature), please check the corresponding sections

> NOTE: Support for modifiers is *best effort*, in most cases the modifiers have been tested individually and not all combinations have been tried.

> **WARNING**: Beware of using Modifiers that increase the vertex o poly count of the models when exporting (like Subdivision Surface) since the exported mesh might not be very optimal for realtime rendering. Retopology is advised in these cases to improve render times.

## Index
 - [Documentation](#documentation)
 - [Modify type Modifiers](#modify-type-modifiers)
 - [Generate type Modifiers](#generate-type-modifiers)
 - [Deform type Modifiers](#deform-type-modifiers)
 - [Array Modifier](#array-modifier)
 - [Boolean Modifier](#boolean-modifier)

## Documentation
 - [Modifiers - Introduction; Blender Manual](https://docs.blender.org/manual/en/latest/modeling/modifiers/introduction.html)

## Modify type Modifiers
Modifier | Supported | Notes
:-------:|:---------:|:----:
[Data Transfer](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/data_transfer.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK, with normals properly modified
[Mesh Cache](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/mesh_cache.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but the exported mesh won't be animated. Please check [XXX] to see how to bake Animations
[Mesh Sequence Cache](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/mesh_sequence_cache.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but the exported mesh won't be animated. Please check [XXX] to see how to bake Animations
[Normal Edit](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/normal_edit.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK, with normals properly modified
[UV Project](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/uv_project.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK and UV Maps are projected, although any UV animations made in Blender won't be exported and are not supported in OGRE.
[UV Warp](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/uv_warp.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK and UV Maps are warped, although any UV animations made in Blender won't be exported and are not supported in OGRE.
[Vertex Weight Edit](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/weight_edit.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK, with normals properly modified 
[Vertex Weight Mix](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/weight_mix.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK, with normals properly modified
[Vertex Weight Proximity](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/weight_proximity.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but it does not do animation like the Blender example shows
[Weighted Normals](https://docs.blender.org/manual/en/latest/modeling/modifiers/modify/weighted_normal.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but affected by [Blenders' triangulation bug](MeshTriangulation.md)

## Generate type Modifiers
Modifier | Supported | Notes
:-------:|:---------:|:----:
[Array](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/array.html) | ![Supported](images/modifiers/ok.png) | Has full support: [Array Modifier](#array-modifier)
[Bevel](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/bevel.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK with bevel
[Boolean](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/booleans.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK with boolean operation applied, but check [Boolean Modifier](#boolean-modifier) section for more information
[Build](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/build.html) | ![Not Supported](images/modifiers/fail.png) | Can't export a mesh with varying vertex count
[Decimate](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/decimate.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK properly decimated
[Edge Split](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/edge_split.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK with modified normals
[Geometry Nodes](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/geometry_nodes.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK with the proper geometry
[Mask](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/mask.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK with applied mask
[Mirror](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/mirror.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK with applied mirroring
[Multiresolution](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/multiresolution.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK, the `Level Viewport` parameter should be more than 0, otherwise the base mesh will be exported. Also, this potentially exports an insane amount of geometry, you might want to do a retopology and use normal maps to bake the details.
[Remesh](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/remesh.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but UV Maps are removed from the Mesh
[Screw](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/screw.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but the base object has to be a mesh otherwise nothing is exported
[Skin](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/skin.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but UV Maps are removed from the Mesh
[Solidify](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/solidify.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK with thickness added
[Subdivision Surface](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/subdivision_surface.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK, as with the `Multiresolution Modifier` beware of the vertex count of the exported mesh (which affects performance).
[Triangulate](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/triangulate.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but affected by [Blenders' triangulation bug](MeshTriangulation.md)
[Volume to Mesh](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/volume_to_mesh.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but UV Maps are removed from the Mesh
[Weld Modifier](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/weld.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Wireframe](https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/wireframe.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK

## Deform type Modifiers
Modifier | Supported | Notes
:-------:|:---------:|:----:
[Armature](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/armature.html) | ![Supported](images/modifiers/ok.png) | Has full support: [Exporting Skeletal Animations](SkeletalAnimation.md)
[Cast](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/cast.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Curve](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/curve.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Displace](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/displace.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Hook](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/hooks.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Laplacian Deform](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/laplacian_deform.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Lattice](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/lattice.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Mesh Deform](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/mesh_deform.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Shrinkwrap](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/shrinkwrap.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Simple Deform](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/simple_deform.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Smooth](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/smooth.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Smooth Laplacian](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/laplacian_smooth.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Surface Deform](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/surface_deform.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Volume Displace](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/volume_displace.html) | ![Not Supported](images/modifiers/fail.png) | Only works on volumes, not meshes
[Warp](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/warp.html) | ![Supported](images/modifiers/ok.png) | Mesh exports OK
[Wave](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/wave.html) | ![Supported*](images/modifiers/warning.png) | Mesh exports OK, but only in the first frame there is no motion. To bake the animation, consult [xxx]

## Array Modifier
This modifier as well as the `Armature Modifier` get their special section because they are treated differently by `blender2ogre`.
Most modifiers are applied before exporting the model (without affecting the object) by converting an evaluated copy of the object into a mesh.

However the case of the `Array Modifier` is different, since the presence of this modifier has `blender2ogre` treat the object differently.

What happens is that in `scene.py` (which creates the .scene output) the `Array Modifier` is used to place instances of the mesh in positions indicated by the modifier.
This means that the exported mesh appearance is not modified by the `Array Modifier`, but only its placement in the scene.

As a result, there is only one copy of the mesh in the scene that is repeated many times, which could lead to a performance increase if using instancing.

> NOTE: To disable this behavior and have the `Array Modifier` be applied to the mesh directly, then set the option: `ARRAY` to true in the mesh options

## Boolean Modifier
This modifier works well and is in principle fully supported, but you might get this error when exporting meshes with the `Boolean Modifier`:
```
FAILED to assign material to face - you might be using a Boolean Modifier between objects with different materials! [ mesh : Cube ]
```

The issue here is that `blender2ogre` has a problem when the two objects that make contact to perform the boolean operation don't have the same material assigned to the faces which enter into contact.

To solve this you need to assign the same material to the faces which are in contact, this might be as simple as assigning a Material to the whole secondary object or having to do something more complex like assigning the same material to the faces that come into contact by entering `Edit Mode` and assigning the material by hand to each face.

As a last resort, it is also possible to make a copy by hand of the object by applying the `Boolean Modifier` and exporting that mesh.
