from setuptools import setup, find_packages

"""
convert blender objects to the ogre file format
"""

setup( name='blender2ogre',
       version='6.1',
       description=__doc__,
       author="",
       author_email="",
       package_dir = {'':'.'},
       packages = ['blender2ogre', 
                   'blender2ogre.ogre',
                   'blender2ogre.tundra'],
       scripts = ['plugin.py'],
     )

