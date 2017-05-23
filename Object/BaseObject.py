import time, math

import numpy as np

from Common import logger
from Object import TransformObject
from Utilities import GetClassName, Attributes
from App import CoreManager


class BaseObject:
    def __init__(self, objName, pos, mesh):
        self.name = objName
        self.selected = False
        self.transform = TransformObject(pos)
        self.mesh = None
        self.geometry_instances = []
        self.set_mesh(mesh)
        self.attributes = Attributes()

    def set_mesh(self, mesh):
        if mesh:
            self.mesh = mesh
            self.geometry_instances = mesh.get_geometry_instances(self)

    def set_material_instance(self, material_instance, index=0):
        if index < self.mesh.geometry_count:
            self.geometry_instances[index].set_material_instance(material_instance)

    def getAttribute(self):
        self.attributes.setAttribute('name', self.name)
        self.attributes.setAttribute('pos', self.transform.pos)
        self.attributes.setAttribute('rot', self.transform.rot)
        self.attributes.setAttribute('scale', self.transform.scale)
        self.attributes.setAttribute('mesh', self.mesh)
        material_instances = [geometry.material_instance.name if geometry.material_instance else '' for geometry in
                              self.geometry_instances]
        self.attributes.setAttribute('material_instances', material_instances)
        return self.attributes

    def setAttribute(self, attributeName, attributeValue, attribute_index):
        if attributeName == 'pos':
            self.transform.setPos(attributeValue)
        elif attributeName == 'rot':
            self.transform.setRot(attributeValue)
        elif attributeName == 'scale':
            self.transform.setScale(attributeValue)
        elif attributeName == 'mesh':
            mesh = CoreManager.instance().resourceManager.getMesh(attributeValue)
            if mesh and self.mesh != mesh:
                self.set_mesh(mesh)
        elif attributeName == 'material_instances':
            material_instance = CoreManager.instance().resourceManager.getMaterialInstance(
                attributeValue[attribute_index])
            self.set_material_instance(material_instance, attribute_index)

    def setSelected(self, selected):
        self.selected = selected

    def update(self):
        # TEST_CODE
        # self.transform.setPitch((time.time() * 0.3) % (math.pi * 2.0))
        # self.transform.setYaw((time.time() * 0.4) % (math.pi * 2.0))
        # self.transform.setRoll((time.time() * 0.5) % (math.pi * 2.0))

        # update transform
        self.transform.updateTransform()

    def bind_object(self):
        pass
