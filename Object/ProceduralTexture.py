import random

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from OpenGL.GL import *

from Common import logger
from App import CoreManager
from Utilities import Attributes
from OpenGLContext import CreateTexture, Material, Texture2D, Texture3D, TextureCube


def CreateProceduralTexture(**datas):
    texture_class = datas.get('texture_type', None)
    if texture_class is not None:
        texture_class = eval(texture_class)
        return texture_class(**datas)
    return None


class NoiseTexture3D:
    def __init__(self, **data):
        self.name = self.__class__.__name__

        self.noise_width = data.get('noise_width', 256)
        self.noise_height = data.get('noise_height', 256)
        self.noise_depth = data.get('noise_depth', 32)
        self.noise_persistance = data.get('noise_persistance', 0.7)
        self.noise_scale = data.get('noise_scale', 6)

        self.attribute = Attributes()

    def render(self):
        core_manager = CoreManager.getInstance()
        resource_manager = core_manager.resource_manager
        renderer = core_manager.renderer

        texture = CreateTexture(
            name='noise_3d',
            texture_type=Texture3D,
            image_mode='RGBA',
            width=self.noise_width,
            height=self.noise_height,
            depth=self.noise_depth,
            internal_format=GL_RGBA8,
            texture_format=GL_RGBA,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            data_type=GL_UNSIGNED_BYTE,
            wrap=GL_REPEAT,
            wrap_r=GL_CLAMP_TO_EDGE,
        )

        resource = resource_manager.textureLoader.getResource('noise_3d')
        if resource is None:
            resource = resource_manager.textureLoader.create_resource("noise_3d", texture)
            resource_manager.textureLoader.save_resource(resource.name)
        else:
            old_texture = resource.get_data()
            old_texture.delete()
            resource.set_data(texture)

        glPolygonMode(GL_FRONT_AND_BACK, renderer.viewMode)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_CULL_FACE)
        glFrontFace(GL_CCW)
        glEnable(GL_DEPTH_TEST)
        glDepthMask(True)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClearDepth(1.0)

        renderer.set_blend_state(False)

        renderer.framebuffer_manager.bind_framebuffer(texture)
        glClear(GL_COLOR_BUFFER_BIT)

        renderer.postprocess.bind_quad()

        mat = resource_manager.getMaterialInstance('examples.noise_3d')
        mat.use_program()
        mat.bind_uniform_data('noise_persistance', self.noise_persistance)
        mat.bind_uniform_data('noise_scale', self.noise_scale)

        for i in range(texture.depth):
            mat.bind_uniform_data('depth', i / texture.depth)
            renderer.framebuffer_manager.bind_framebuffer(texture, target_layer=i)
            renderer.postprocess.draw_elements()

        renderer.restore_blend_state_prev()

    def get_save_data(self):
        save_data = dict(
            texture_type=self.__class__.__name__,
            noise_width=self.noise_width,
            noise_height=self.noise_height,
            noise_depth=self.noise_depth,
            noise_persistance=self.noise_persistance,
            noise_scale=self.noise_scale,
        )
        return save_data

    def getAttribute(self):
        self.attribute.setAttribute("noise_width", self.noise_width)
        self.attribute.setAttribute("noise_height", self.noise_height)
        self.attribute.setAttribute("noise_depth", self.noise_depth)
        self.attribute.setAttribute("noise_persistance", self.noise_persistance)
        self.attribute.setAttribute("noise_scale", self.noise_scale)
        return self.attribute

    def setAttribute(self, attributeName, attributeValue, attribute_index):
        if hasattr(self, attributeName):
            setattr(self, attributeName, attributeValue)
        return self.attribute
