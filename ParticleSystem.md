
# Exporting Particle Systems

## Introduction
A common technique for laying out random objects on a scene in Blender is to use the Particle System. 
(That is, before Geometry Nodes in Blender 2.92)

In this tutorial we are going to explore how to layout objects in a scene randomly and export that scene for using with OGRE.

This tutorial is based on the ideas showed in this "CG Geek" video:
[Create Realistic Grass in Blender 2.8 in 15 minutes](https://www.youtube.com/watch?v=-GAm-7_3N6g)

Terminology:
 - *Base Object*: an object with a mesh that represents a terrain or some other form where we want to place random objects on.
 - *Dupli Objects*: an object with a mesh that represents random objects (like grass, trees, rocks, etc.) that we want to place on the Base object.

The scene in the images is available [here](examples/particle-system.blend), it was made with the A.N.T Landscape Plugin that comes bundled with Blender (River preset) and very simple "Earth" and "Water" materials.

## Creating and setting up the Particle System
Select the mesh where you want to place your foliage or debris over (the *Base Object*).

Go to the `Particles` tab and click on new to add a new particle system.

Select type: `Hair` and click on `Advanced` to show the advanced options.

By default `Hair Length` is set to 4 which makes the debris show 4 x larger so set the value to 1.

With `Number` it is possible to control the amount of objects that will appear randomly on the mesh surface.

![ParticleSystem1.png](images/ParticleSystem1.png)

Click on `Rotation` and select `Initial Orientation: Normal`.

You can change the `Phase` and `Random` values to have the debris show random rotations around the Z axis (tangent space), this way if you have trees they will be showing in different orientations.

![ParticleSystem2.png](images/ParticleSystem2.png)

In the `Render` setting change the type to `Object` and in `Dupli Object` select the object you want to duplicate randomly over the mesh.
Check the `Rotation` and `Scale` options so the Particle System will take the *Dupli Objects* rotation and scale into account.
Set `Size` to 1 and choose a `Random Size` value to control the amount of randomness in the size distribution of the *Dupli Objects*.

![ParticleSystem3.png](images/ParticleSystem3.png)

At this point you should see the object appearing randomly in the places where there were hair strands.
But, the objects appear rotated -90 degree over the Y axis.
In order to solve this it is necessary to rotate the Dupli Object 90 degree over the Y axis to counter this rotation.
Don't apply this rotation to the Dupli Object, otherwise the `blender2ogre` add-on will export the mesh with this rotation applied.
The add-on will automatically apply this rotation to the nodes in the exported scene.

Another thing to take into account is that the Dupli Object origin should be at its base, otherwise it will appear to be buried halfway.

## Extras
It is also possible to paint certain parts of the Base Objects mesh to modify the *Dupli Objects* density by using weith paint.
Select the *Base Object*, go into weight paint mode and start painting the areas where you want to increase the *Dupli Objects* density.

Remeber that the *Base Object* should have some tesselation for this to work well, otherwise there might be few vertices to paint.
One way to tesselate is to go into Edit mode and subdivide, or activate Dynotopo in Sculpt mode.

After painting the areas go back to the `Particles` tab and in the `Vertex Groups` section choose the vertex group in `Density` and `Length` (the default vertex group is `Default`).

![ParticleSystem4.png](images/ParticleSystem4.png)

## Troubleshooting
Some tips for troubleshooting:
 - Don't apply the 90 degree rotation on the Y axis to the Dupli Object, that rotation is just to see the object well placed in Blender
 - Make sure that the origin of the Dupli Object is centered in the base
 - Apply any scale used on the Dupli and Base Objects
 - Check the logs for any errors or warnings (in Windows: Window > Toggle System Console)

## Automation
After adding the second particle system you will probably be asking for a way to automate the process of adding more foliage/debris layers to the scene.

That is possible with a very simple Blender script, switch to the `Scripting` layout and copy the following script:
```
import bpy

def add_debris_layer( object_name, seed=1, number=100, phase=1, random=1, size=1, size_rnd=1 ):

    bpy.ops.object.particle_system_add()

    index = len(bpy.context.object.particle_systems) - 1
    particle_system = bpy.context.object.particle_systems[index]

    particle_system_settings = particle_system.settings

    particle_system.name = object_name
    particle_system_settings.name = object_name
    
    particle_system_settings.use_advanced_hair = True

    particle_system_settings.type = "HAIR"
    particle_system_settings.hair_length = 1
    particle_system_settings.count = number
    
    particle_system.seed = seed

    particle_system_settings.use_rotations = True
    particle_system_settings.rotation_mode = "NOR"
    particle_system_settings.phase_factor = phase
    particle_system_settings.phase_factor_random = random

    particle_system_settings.render_type = "OBJECT"
    particle_system_settings.use_rotation_dupli = True

    particle_system_settings.dupli_object = bpy.data.objects[object_name]
    particle_system_settings.particle_size = size
    particle_system_settings.size_random = size_rnd

    bpy.ops.object.vertex_group_add()

    index = len(bpy.context.object.vertex_groups) - 1
    vertex_group = bpy.context.object.vertex_groups[index]

    vertex_group.name = object_name
    
    particle_system.vertex_group_density = object_name
    particle_system.vertex_group_length = object_name

# Example usage:
add_debris_layer("Bush", 1)
add_debris_layer("Grass 1", 2)
add_debris_layer("Stone 1", 5)
add_debris_layer("Tree 1", 10)
```
