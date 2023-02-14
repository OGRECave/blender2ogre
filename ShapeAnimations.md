
# Shape Animations

## Index
 - [Introduction](#introduction)
 - [Set up](#set-up)
 - [Baking complex animations into Shape Animations](#baking-complex-animations-into-shape-animations)
 - [Using Shape Animations in Ogre](#using-shape-animations-in-ogre)

## Introduction
A common technique for creating face animations is to use Poses or Shapes for the different phonemes that the character should go through when talking.

In this tutorial we are going to explore how to create a couple poses and animate them.

Terminology:
 - *Shape Keys*: a certain pose defined in Blender. This pose can be blended with other poses in different degrees to achieve new poses

## Set up
To make this tutorial simple, the Animation is going to be applied only to the default cube.

To see a better representation of face animations, take a look at [this](examples/shape-animation.blend) example.

Create a new scene in Blender and split it into two, in the second view select `Dope Sheet` and `Shape Key Editor`.
![shape-animations1.png](images/shape-anim/shape-animations1.png)

Select the default cube and go to the `Vertex` or `Data` tab. Under `Shape Keys` press the `+` button three times to create three Shape Keys.
![shape-animations2.png](images/shape-anim/shape-animations2.png)

The Basis is the base shape and the other shape keys are going to be the poses that we apply over the base.

Select `Key 1` and go into `Edit Mode` (press tab).

Once you are in `Edit Mode` press `s` (scale), 2 and `Enter` to scale the cube two times.

Then select `Key 2` and press again `s`, write 0.5 and `Enter` to scale the cube to half size.

Now you have three shapes to animate.

Go into `Object Mode` by pressing tab and in the bottom you should see that the current frame is 1.
![shape-animations3.png](images/shape-anim/shape-animations3.png)

Select `Key 1` and in `value` set it all the way to 1.

Hover the mouse over `value` and press `i` to insert a keyframe at frame 1.

Then, select `Key 2` and leave `value` as it is, Hover the mouse over `value` and press `i` to insert a keyframe at frame 1 for `Key 2`.

You should see in the `Dope Sheet` view that now there is a new "Key Action", press `F` next to it to save the action by associating it with a fake user.

Now, set the current frame to 60 and repeat the above process but setting `value` to 0 for `Key 1` and 1 for `Key 2`, remember to insert the keyframes (the `value`s should turn yellow).

Set the `End` frame to 60 and press play to see the cube changing size. Of course this is a simple animation but with some imagination something much more complex can be achieved like face animations.

Last but not least in order for the `blender2ogre` add-on to properly export the animation it is necessary to turn it into an NLA Track, select the `Push Down` button next to the action name.
![shape-animations1.png](images/shape-anim/shape-animations1.png)

You can now go into the `NLA Editor` view and change the name of the NLA Track that name is the one that is going to be exported.

## Baking complex animations into Shape Animations
[How to Bake Modifier Animation in Blender / 1. Wave Modifier Animation to Shape Keys!](https://www.youtube.com/watch?v=KMIkOhTSP1U)
https://docs.blender.org/manual/en/latest/addons/import_export/shape_mdd.html

Blender is able to perform some complex vertex animations (`Wave Modifier` being an example).
However it is not possible to just export these animations into OGRE directly.
But there is a trick to bake these animations into Shape Key Animations and then it is possible to export into OGRE.
The trick consists of exporting the animation using the `NewTek MDD` format and then importing it, the resulting mesh will have the vertex animations baked as a Shape Key Animation

> NOTE: Care must be taken if the animation has too many frames since there will be one Shape Key for every frame and that makes the exported mesh heavier.

The steps are the following (example using `Wave Modifier`):
1) Add a plane mesh (Shift-A -> Mesh -> Plane), then enter `Edit Mode` (Tab) and subdivide the mesh (Ctrl-E -> Subdivide) 5 times so the `Wave Modifier` has some geometry to work with
2) Set the object shading to smooth (Object -> Shade Smooth)
3) Add the `Wave Modifier` to the "Plane" Object and rename the "Plane" to "Wave"
4) Set the starting and ending frames of the animation (lower right corner)
5) Enable the `NewTek MDD` Add-On (go to Edit -> Preferences -> Add-ons -> `NewTek MDD` and enable the Add-on)
6a) Make sure the Plane/Wave object is selected
6b) Export the animation to an .mdd file: File -> Export -> Lightwave Point Cache (.mdd) and set a proper filename like wave.mdd
7) Duplicate the Plane object (Shift-D) and set a name like Wave2
8) On the Duplicate Plane object, remove the Wave modifier
9a) Make sure the duplicate object "Wave2" is selected
9b) Now import the recently exported .mdd file: File -> Import -> Lightwave Point Cache (.mdd)
Now the duplicate object "Wave2" has a number of Shape Keys, each for every frame that was exported in step 6b)
Besides a new action `KeyAction` is created, which you can see in the `Shape Key Editor` of the `Dope Sheet` (Shift-F12)
10) Now to get blender2ogre to export the animation we need to create a NLA track, go to the `Animation` and in the upper left corner change the view to `Nonlinear Animation`
11) Perform a push-down of the animation towards an NLA Track
12) Set the name of the NLA Track, which will be the name of the Shape/Pose Animation in OGRE
13) Now use `blender2ogre` to export the animation, make sure the option `SHAPE_ANIMATIONS` is set to `True`


## Using Shape Animations in Ogre
Create an Entity and attach it to a SceneNode
```
Ogre::Entity* cube = mSceneMgr->createEntity("Cube", "Cube.mesh");
Ogre::SceneNode* cubeNode = mSceneMgr->getRootSceneNode()->createChildSceneNode("Cube");
cubeNode->attachObject(cube);
```

Get the AnimationState, enable it and set the starting time position
```
auto animationState = cube->getAnimationState("KeyAction");
animationState->setEnabled(true);
animationState->setTimePosition(0);
```

Then you need to `addTime()` to the *AnimationState*, we will use a controller for that.
```
auto& controllerMgr = Ogre::ControllerManager::getSingleton();

// Create a controller to pass the frame time to the Animation State, otherwise the animation won't play
// (this is a better method than using animationState->addTime() in your main loop)
controllerMgr.createFrameTimePassthroughController(Ogre::AnimationStateControllerValue::create(animationState, true));
```

For more information, please take a look at section [Vertex-Animation](https://ogrecave.github.io/ogre/api/latest/_animation.html#Vertex-Animation) in the manual.

And also consult the Ogre API manual:
 - https://ogrecave.github.io/ogre/api/latest/class_ogre_1_1_scene_manager.html
 - https://ogrecave.github.io/ogre/api/latest/class_ogre_1_1_animation_state.html
 - https://ogrecave.github.io/ogre/api/latest/class_ogre_1_1_scene_node.html
 - https://ogrecave.github.io/ogre/api/latest/class_ogre_1_1_controller_manager.html
 - https://ogrecave.github.io/ogre/api/latest/class_ogre_1_1_controller.html
