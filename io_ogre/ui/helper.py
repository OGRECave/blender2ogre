import bpy
from ..util import wordwrap

def auto_register(register):
    yield OGRE_MT_ogre_docs
    for clazz in _OGRE_DOCS_:
        yield clazz

_OGRE_DOCS_ = []
def ogredoc( cls ):
    tag = cls.__name__.split('_ogredoc_')[-1]
    cls.bl_label = tag.replace('_', ' ')
    _OGRE_DOCS_.append( cls )
    return cls

class OGRE_MT_ogre_docs(bpy.types.Menu):
    bl_label = "Ogre Help"

    def draw(self, context):
        layout = self.layout
        for cls in _OGRE_DOCS_:
            layout.menu( cls.__name__ )
            layout.separator()
        layout.label(text='bug reports to: https://github.com/OGRECave/blender2ogre/issues')

class OGRE_MT_ogre_helper(bpy.types.Menu):
    bl_label = '_overloaded_'

    def draw(self, context):
        layout = self.layout
        #row = self.layout.box().split(percentage=0.05)
        #col = row.column(align=False)
        #print(dir(col))
        #row.scale_x = 0.1
        #row.alignment = 'RIGHT'

        for line in self.mydoc.splitlines():
            if line.strip():
                for ww in wordwrap( line ): layout.label(text=ww)
        layout.separator()

@ogredoc
class OGRE_MT_ogredoc_Installing( OGRE_MT_ogre_helper ):
    mydoc = """
Installing:
    Installing the Addon:
        You can simply copy io_export_ogreDotScene.py to your blender installation under blender/2.6x/scripts/addons/
        and enable it in the user-prefs interface (CTRL+ALT+U)
        Or you can use blenders interface, under user-prefs, click addons, and click 'install-addon'
        (its a good idea to delete the old version first)

    Required:
        1. Blender 2.63

        2. Install Ogre Command Line tools to the default path: C:\\OgreCommandLineTools from http://www.ogre3d.org/download/tools
            * These tools are used to create the binary Mesh from the .xml mesh generated by this plugin.
            * Linux users may use above and Wine, or install from source, or install via apt-get install ogre-tools.

    Optional:
        3. Install Image Magick
            * http://www.imagemagick.org

        4. Install an mesh viewer (OgreMeshViewer or OgreMeshy)
            * If your using 64bit Windows, put OgreMeshy to C:\\OgreMeshy
"""

@ogredoc
class OGRE_MT_ogredoc_FAQ( OGRE_MT_ogre_helper ):
    mydoc = """

Q: I have hundres of objects, is there a way i can merge them on export only?
A: Yes, just add them to a group named starting with "merge.", or link the group.

Q: Can i use subsurf or multi-res on a mesh with an armature?
A: Yes.

Q: Can i use subsurf or multi-res on a mesh with shape animation?
A: No.

Q: I don't see any objects when i export?
A: You must select the objects you wish to export.

Q: I don't see my animations when exported?
A: Make sure you created an NLA strip on the armature.

Q: Do i need to bake my IK and other constraints into FK on my armature before export?
A: No.

"""

@ogredoc
class OGRE_MT_ogredoc_Animation_System( OGRE_MT_ogre_helper ):
    mydoc = '''
Armature Animation System | OgreDotSkeleton
    Quick Start:
        1. select your armature and set a single keyframe on the object (loc,rot, or scl)
            . note, this step is just a hack for creating an action so you can then create an NLA track.
            . do not key in pose mode, unless you want to only export animation on the keyed bones.
        2. open the NLA, and convert the action into an NLA strip
        3. name the NLA strip(s)
        4. set the in and out frames for each strip ( the strip name becomes the Ogre track name )

    How it Works:
        The NLA strips can be blank, they are only used to define Ogre track names, and in and out frame ranges.  You are free to animate the armature with constraints (no baking required), or you can used baked animation and motion capture.  Blending that is driven by the NLA is also supported, if you don't want blending, put space between each strip.

    The OgreDotSkeleton (.skeleton) format supports multiple named tracks that can contain some or all of the bones of an armature.  This feature can be exploited by a game engine for segmenting and animation blending.  For example: lets say we want to animate the upper torso independently of the lower body while still using a single armature.  This can be done by hijacking the NLA of the armature.

    Advanced NLA Hijacking (selected-bones-animation):
        . define an action and keyframe only the bones you want to 'group', ie. key all the upper torso bones
        . import the action into the NLA
        . name the strip (this becomes the track name in Ogre)
        . adjust the start and end frames of each strip
        ( you may use multiple NLA tracks, multiple strips per-track is ok, and strips may overlap in time )

'''

@ogredoc
class OGRE_MT_ogredoc_Physics( OGRE_MT_ogre_helper ):
    mydoc = '''
Ogre Dot Scene + BGE Physics
    extended format including external collision mesh, and BGE physics settings
<node name="...">
    <entity name="..." meshFile="..." collisionFile="..." collisionPrim="..." [and all BGE physics attributes] />
</node>

collisionFile : sets path to .mesh that is used for collision (ignored if collisionPrim is set)
collisionPrim : sets optimal collision type [ cube, sphere, capsule, cylinder ]
*these collisions are static meshes, animated deforming meshes should give the user a warning that they have chosen a static mesh collision type with an object that has an armature

Blender Collision Setup:
    1. If a mesh object has a child mesh with a name starting with 'collision', then the child becomes the collision mesh for the parent mesh.

    2. If 'Collision Bounds' game option is checked, the bounds type [box, sphere, etc] is used. This will override above rule.

    3. Instances (and instances generated by optimal array modifier) will share the same collision type of the first instance, you DO NOT need to set the collision type for each instance.

'''

@ogredoc
class OGRE_MT_ogredoc_Bugs( OGRE_MT_ogre_helper ):
    mydoc = '''
Known Issues:
    . shape animation breaks when using modifiers that change the vertex count
        (Any modifier that changes the vertex count is bad with shape anim or armature anim)
    . never rename the nodes created by enabling Ogre-Material-Layers
    . never rename collision proxy meshes created by the Collision Panel
'''

