"""Flat-shaded mesh builder for hard-edged town parts (stone, timber, plaster)."""

import story_kit as SK


class Hard(SK.MeshBuilder):
    """Same API as story_kit.MeshBuilder, but faces stay flat-shaded so boxes keep crisp edges."""

    def build(self, name, collection, smooth=0, solidify=0., location=(0, 0, 0)):
        obj = super().build(name, collection, smooth=smooth, solidify=solidify, location=location)
        for polygon in obj.data.polygons:
            polygon.use_smooth = False
        return obj

    def prism(self, base, apex, material):
        """Triangle prism: `base` is three points of one end, `apex` the same three points shifted."""
        a, b = base, apex
        verts = list(a) + list(b)
        faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
        self.add(verts, faces, material)
