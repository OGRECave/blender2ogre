import os
import sys
import unittest
import subprocess
import tempfile
from os.path import join, isfile
import xml.etree.ElementTree as xml

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
        io_ogre_path = join(os.getcwd())
        proc = subprocess.Popen([self.blender_path, "-b", "--python", script, "--", io_ogre_path, self.last_path, cmd])
        self.output, self.error = proc.communicate()

    def assertCreatedFile(self, name):
        path = join(self.last_path, name)
        if not isfile(path):
            self.fail("the file {} is not a regular file! export failed to create it".format(path))

    def load_xml(self, name):
        path = join(self.last_path, name)
        return xml.parse(path)


    def blender_exe(self):
        blender_path_template = join('test','blender', '{path}', '{exe}')
        if sys.platform.startswith("darwin"):
            return blender_path_template.format(path=join('2.71', 'Blender', 'blender.app', 'Contents', 'MacOS'), exe='blender')
        else:
            raise Exception("impl me!")

