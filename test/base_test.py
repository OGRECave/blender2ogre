import os
import sys
import unittest
import subprocess
import tempfile
from os.path import join, isfile

SUPPORTED_VERSIONS = ['2.70', '2.71']

class BlenderTestCase(unittest.TestCase):

    def __init__(self, arg):
        unittest.TestCase.__init__(self,arg)
        self.blender_path = self.blender_exe()
        self.path = join(os.getcwd(), 'test')
        self.path_fixtures = join(self.path, 'fixtures')
        self.path_tmp = join(self.path, 'tmp')

    def run_io_ogre(self, cmd, blend_file=''):
        script = join("io_ogre","console.py")
        self.last_path = tempfile.mkdtemp('io_ogre_test')
        io_ogre_path = join(os.getcwd(),'io_ogre')
        proc = subprocess.Popen([self.blender_path, "-b", "--python", script, "--", io_ogre_path, self.last_path, cmd])
        output, error = proc.communicate()
        if error:
            print(output, error)

    def assertCreatedFile(self, name):
        path = join(self.last_path, name)
        if isfile(path):
            assertFalse(True, "the file {} is not a regular file! export failed to create it".format(path))


    def blender_exe(self):
        blender_path_template = join('test','blender', '{path}', '{exe}')
        if sys.platform.startswith("darwin"):
            return blender_path_template.format(path=join('2.71', 'Blender', 'blender.app', 'Contents', 'MacOS'), exe='blender')
        else:
            raise Exception("impl me!")

