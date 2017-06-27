# coding: utf-8


#-- Example;
"""
hlms Material.001 pbs 
{
	roughness	0.4
	fresnel		1.33
	diffuse		1 0 0
	specular	1 0 0
	//detail_map0				MRAMOR6X6.jpg
	//detail_offset_scale0 	0 0 5 5
	//diffuse_map		Rocks_Diffuse.tga
}
"""

PBS_TEMPLATE = """
hlms {material_name} pbs 
{{
	roughness	{roughness}
	fresnel		{fresnel}
	diffuse		{diffuse}
	specular	{specular}
}}
"""
PBS_TEMPLATE_TEXTURED = """
hlms {material_name} pbs 
{{
	roughness	{roughness}
	fresnel		{fresnel}
	diffuse		{diffuse}
	specular	{specular}
	detail_map0	{texture_file}
}}
"""
