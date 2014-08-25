import unittest
from os.path import join
import base_test

class TestSceneGeneration(base_test.BlenderTestCase):

    def test_scene_basic(self):
        """
        ensure that the basic scene can be exported
        """
        self.run_io_ogre("scene CubeScene")
        self.assertCreatedFile("CubeScene.scene") 
        self.assertCreatedFile("Cube.mesh.xml") 
        self.assertCreatedFile("Cube.mesh") 
        self.assertCreatedFile("Material.material") 

        scene = self.load_xml("CubeScene.scene")
        scene_cube = scene.find('.//node[@name="Cube"]')
        self.assertIsNotNone(scene_cube)
        self.assertIsNotNone(scene_cube.find('entity'))

        cube = self.load_xml("Cube.mesh.xml")
        self.assertEqual(len(cube.findall(".//faces/face")), 12) # cube has 6 sides of quads, makes 12 triangles
        vertex_count = int(cube.find(".//sharedgeometry").attrib["vertexcount"])
        self.assertEqual(len(cube.findall(".//vertexbuffer/vertex")), vertex_count)


