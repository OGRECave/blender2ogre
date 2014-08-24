import unittest
from os.path import join
import base_test

class TestSceneGeneration(base_test.BlenderTestCase):

    def setUp(self):
        pass

    def test_scene_basic(self):
        """
        ensure that the basic scene can be exported
        """
        self.run_io_ogre("scene CubeScene")
        self.assertCreatedFile("CubeScene.scene") 
        self.assertCreatedFile("Cube.mesh.xml") 
        self.assertCreatedFile("Cube.mesh") 
        self.assertCreatedFile("Material.material") 

