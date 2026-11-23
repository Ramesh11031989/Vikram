"""Original procedural surface detail for the cast's close-ups."""


def skin_surface(material, color):
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    shader = nodes.get('Principled BSDF')
    shader.location = (650, 100)
    nodes.get('Material Output').location = (990, 100)
    shader.inputs['Subsurface Weight'].default_value = .045
    shader.inputs['Subsurface Scale'].default_value = .004
    shader.inputs['Specular IOR Level'].default_value = .29

    coordinates = nodes.new('ShaderNodeTexCoord')
    coordinates.location = (-980, 150)

    variation = nodes.new('ShaderNodeTexNoise')
    variation.label = 'Skin tone and oil variation'
    variation.location = (-750, 250)
    variation.inputs['Scale'].default_value = 63
    variation.inputs['Detail'].default_value = 3.1
    links.new(coordinates.outputs['Object'], variation.inputs['Vector'])

    complexion = nodes.new('ShaderNodeValToRGB')
    complexion.label = 'Warm and cool skin undertones'
    complexion.location = (-460, 400)
    lower, upper = complexion.color_ramp.elements
    lower.position, lower.color = .22, (*[v*f for v,f in zip(color,(.90,.855,.825))], 1)
    upper.position, upper.color = .8, (*[v*f for v,f in zip(color,(1.068,1.04,1.007))], 1)
    links.new(variation.outputs['Fac'], complexion.inputs['Fac'])
    links.new(complexion.outputs['Color'], shader.inputs['Base Color'])

    finish = nodes.new('ShaderNodeMapRange')
    finish.label = 'Soft variation in skin roughness'
    finish.location = (-130, 90)
    finish.inputs['To Min'].default_value = .51
    finish.inputs['To Max'].default_value = .73
    links.new(variation.outputs['Fac'], finish.inputs['Value'])
    links.new(finish.outputs['Result'], shader.inputs['Roughness'])

    pores = nodes.new('ShaderNodeTexVoronoi')
    pores.label = 'Fine pores, object scale in meters'
    pores.location = (-750, -170)
    pores.inputs['Scale'].default_value = 990
    links.new(coordinates.outputs['Object'], pores.inputs['Vector'])
    pore_profile = nodes.new('ShaderNodeValToRGB')
    pore_profile.location = (-470, -185)
    pore_profile.color_ramp.elements[0].position = .06
    pore_profile.color_ramp.elements[1].position = .32
    links.new(pores.outputs['Distance'], pore_profile.inputs['Fac'])

    pores_bump = nodes.new('ShaderNodeBump')
    pores_bump.location = (335, -180)
    pores_bump.inputs['Strength'].default_value = .39
    pores_bump.inputs['Distance'].default_value = .00046
    links.new(pore_profile.outputs['Color'], pores_bump.inputs['Height'])
    links.new(pores_bump.outputs['Normal'], shader.inputs['Normal'])


def lip_surface(material):
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.location = (625, 110)
    nodes.get('Material Output').location = (950, 110)
    shader.inputs['Specular IOR Level'].default_value = .3
    shader.inputs['Subsurface Weight'].default_value = .029
    shader.inputs['Subsurface Scale'].default_value = .002

    tone = nodes.new('ShaderNodeVertexColor')
    tone.layer_name = 'Lip pigment'
    tone.label = 'Darker upper lip, softer skin boundary'
    tone.location = (-620, 325)
    links.new(tone.outputs['Color'], shader.inputs['Base Color'])

    coordinates = nodes.new('ShaderNodeTexCoord')
    coordinates.location = (-850, 115)
    stretched = nodes.new('ShaderNodeVectorMath')
    stretched.operation = 'MULTIPLY'
    stretched.inputs[1].default_value = (2.8, 1, .39)
    stretched.location = (-620, 70)
    links.new(coordinates.outputs['Object'], stretched.inputs[0])
    creases = nodes.new('ShaderNodeTexNoise')
    creases.label = 'Vertical lip ridges'
    creases.location = (-420, 70)
    creases.inputs['Scale'].default_value = 530
    creases.inputs['Detail'].default_value = 2.5
    links.new(stretched.outputs['Vector'], creases.inputs['Vector'])

    bump = nodes.new('ShaderNodeBump')
    bump.location = (330, -155)
    bump.inputs['Strength'].default_value = .29
    bump.inputs['Distance'].default_value = .00023
    links.new(creases.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])

    finish = nodes.new('ShaderNodeMapRange')
    finish.location = (70, 115)
    finish.inputs['To Min'].default_value = .44
    finish.inputs['To Max'].default_value = .68
    links.new(creases.outputs['Fac'], finish.inputs['Value'])
    links.new(finish.outputs['Result'], shader.inputs['Roughness'])


def pigment_material(material, attribute_name):
    nodes = material.node_tree.nodes
    shader = nodes.get('Principled BSDF')
    shader.inputs['Specular IOR Level'].default_value = .09
    pigment = nodes.new('ShaderNodeVertexColor')
    pigment.layer_name = attribute_name
    pigment.label = attribute_name
    pigment.location = (-245, 265)
    material.node_tree.links.new(pigment.outputs['Color'], shader.inputs['Base Color'])


def vertex_pigment(obj, name, samples):
    pigments = obj.data.color_attributes.new(name=name, type='FLOAT_COLOR', domain='POINT')
    pigments.data.foreach_set('color', [component for color in samples for component in (*color, 1)])
