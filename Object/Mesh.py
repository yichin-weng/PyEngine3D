import os
import traceback

import numpy as np

from Common import logger
from OpenGLContext import CreateGeometry, VertexArrayBuffer, UniformMatrix4
from Utilities import Attributes, GetClassName, normalize
from App import CoreManager


class GeometryInstance:
    def __init__(self, parent_actor, geometry, material_instance):
        self.name = geometry.name
        self.parent_actor = parent_actor
        self.geometry = geometry
        self.material_instance = material_instance

    def set_material_instance(self, material_instance):
        self.material_instance = material_instance

    def bindBuffer(self):
        self.geometry.bindBuffer()

    def draw(self):
        self.geometry.draw_elements()


class Mesh:
    def __init__(self, mesh_name, **mesh_data):
        logger.info("Load %s : %s" % (GetClassName(self), mesh_name))

        self.name = mesh_name
        self.geometry_datas = mesh_data.get('geometry_datas', [])
        self.geometries = CreateGeometry(self.geometry_datas)
        self.attributes = Attributes()

    def clear_data(self):
        self.geometry_datas = None

    def get_save_data(self):
        save_data = dict(
            geometry_datas=self.geometry_datas
        )
        return save_data

    def get_geometry_count(self):
        return len(self.geometries)

    def getAttribute(self):
        self.attributes.setAttribute("name", self.name)
        self.attributes.setAttribute("geometries", [geometry.name for geometry in self.geometries])
        return self.attributes

    def setAttribute(self, attributeName, attributeValue, attribute_index):
        pass

    def bindBuffer(self, index=0):
        if index < len(self.geometries):
            self.geometries[index].bindBuffer()

    def draw(self, index=0):
        if index < len(self.geometries):
            self.geometries[index].draw_elements()


class Triangle(Mesh):
    def __init__(self):
        geometry_data = dict(
            positions=[(-1, -1, 0), (1, -1, 0), (-1, 1, 0)],
            colors=[(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1)],
            normals=[(0, 0, 1), (0, 0, 1), (0, 0, 1)],
            texcoords=[(0, 0), (1, 0), (0, 1)],
            indices=[0, 1, 2])
        geometry_datas = [geometry_data, ]
        Mesh.__init__(self, GetClassName(self), geometry_datas=geometry_datas)


# ------------------------------#
# CLASS : Quad
# ------------------------------#
class Quad(Mesh):
    def __init__(self):
        geometry_data = dict(
            positions=[(-1, -1, 0), (1, -1, 0), (-1, 1, 0), (1, 1, 0)],
            colors=[(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), (1, 1, 0, 1)],
            normals=[(0, 0, 1), (0, 0, 1), (0, 0, 1), (0, 0, 1)],
            texcoords=[(0, 0), (1, 0), (0, 1), (1, 1)],
            indices=[0, 1, 2, 1, 3, 2])
        geometry_datas = [geometry_data, ]
        Mesh.__init__(self, GetClassName(self), geometry_datas=geometry_datas)


# ------------------------------#
# CLASS : DebugLine
# ------------------------------#
class DebugLine:
    def __init__(self, pos1, pos2, width=2.5, color=(1, 1, 0)):
        self.width = width
        self.pos1 = pos1
        self.pos2 = pos2
        self.color = color

    def draw(self):
        pass
        # glLineWidth(self.width)
        # glColor3f(1, 1, 1)
        # glBegin(GL_LINES)
        # glVertex3f(*self.pos1)
        # glVertex3f(*self.pos2)
        # glEnd()
