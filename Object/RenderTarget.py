import gc
import random

import numpy as np

from OpenGL.GL import *
from OpenGL.GL.ARB.framebuffer_object import *
from OpenGL.GL.EXT.framebuffer_object import *

from Utilities import *
from Common import logger
from OpenGLContext import Texture2D, Texture2DMultiSample, TextureCube, RenderBuffer, CreateTexture


class Option:
    NONE = 0
    MSAA = 1 << 1
    SSAA = 1 << 2


class RenderTargets:
    BACKBUFFER = None
    DEPTHSTENCIL = None
    HDR = None
    DIFFUSE = None
    MATERIAL = None
    WORLD_NORMAL = None
    SHADOWMAP = None
    LINEAR_DEPTH = None
    SCREEN_SPACE_REFLECTION = None
    SSAO = None
    SSAO_ROTATION_NOISE = None
    VELOCITY = None
    TEMP_RENDER_BUFFER_MULTISAMPLE = None
    TEMP_RGBA8 = None
    TEMP_HDR = None
    TEMP_MULTISAMPLE_X4 = None


class RenderTargetManager(Singleton):
    name = "RenderTargetManager"

    def __init__(self):
        self.core_manager = None
        self.renderer = None
        self.rendertargets = dict()
        self.temp_rendertargets = dict()

    def initialize(self, core_manager):
        logger.info("initialize " + GetClassName(self))
        self.core_manager = core_manager
        self.renderer = core_manager.renderer
        self.clear()

    def clear(self):
        # for key, rendertarget in self.rendertargets.items():
        #     delete_from_referrer(rendertarget)
        #
        # for key, rendertarget in self.temp_rendertargets.items():
        #     delete_from_referrer(rendertarget)
        self.rendertargets = dict()
        self.temp_rendertargets = dict()
        # gc.collect()

    def find_rendertarget(self, rendertarget_index, rendertarget_name):
        if rendertarget_index < len(self.rendertargets) and rendertarget_name in self.rendertargets:
            return self.rendertargets[rendertarget_name]
        elif rendertarget_name in self.temp_rendertargets:
            return self.temp_rendertargets[rendertarget_name]
        return None

    def get_rendertarget(self, rendertarget_name):
        return self.rendertargets[rendertarget_name] if rendertarget_name in self.rendertargets else None

    def get_temporary(self, rendertarget_name, reference_rendertarget=None, scale=1.0):
        temp_rendertarget = None
        if rendertarget_name in self.temp_rendertargets:
            temp_rendertarget = self.temp_rendertargets[rendertarget_name]
        elif reference_rendertarget:
            rendertarget_datas = reference_rendertarget.get_save_data(get_image_data=False)
            # don't copy image data
            if 'data' in rendertarget_datas:
                rendertarget_datas.pop('data')
            rendertarget_datas['width'] = int(rendertarget_datas['width'] * scale)
            rendertarget_datas['height'] = int(rendertarget_datas['height'] * scale)
            rendertarget_type = rendertarget_datas['texture_type']
            temp_rendertarget = rendertarget_type(name=rendertarget_name, **rendertarget_datas)
            if temp_rendertarget:
                self.temp_rendertargets[rendertarget_name] = temp_rendertarget
                # send rendertarget info to GUI
                self.core_manager.sendRenderTargetInfo(temp_rendertarget.name)

        if temp_rendertarget is None:
            logger.warn("Failed to get temporary %s render target." % rendertarget_name)
        return temp_rendertarget

    def create_rendertarget(self, rendertarget_name, rendertarget_type, **kwargs):
        datas = Data(**kwargs)
        option = datas.option or Option.NONE

        if (Option.MSAA & option) and self.renderer.postprocess.enable_MSAA():
            if rendertarget_type == Texture2D:
                rendertarget_type = Texture2DMultiSample
            datas.multisample_count = self.renderer.postprocess.get_msaa_multisample_count()
        elif (Option.SSAA & option) and self.renderer.postprocess.is_SSAA():
            datas.width *= 2
            datas.height *= 2

        # Create RenderTarget
        rendertarget = None
        if rendertarget_type == RenderBuffer:
            rendertarget = RenderBuffer(rendertarget_name, datas=datas)
        else:
            rendertarget = CreateTexture(name=rendertarget_name, texture_type=rendertarget_type, **datas.get_dict())

        if rendertarget:
            if rendertarget_name not in self.rendertargets:
                self.rendertargets[rendertarget_name] = rendertarget
                # send rendertarget info to GUI
                self.core_manager.sendRenderTargetInfo(rendertarget_name)
            else:
                object_copy(rendertarget, self.rendertargets[rendertarget_name])
        else:
            logger.error("Failed to crate a render target. %s" % rendertarget_name)
        return rendertarget

    def create_rendertargets(self):
        self.clear()

        # Note : # clear rendertarget infos in GUI
        self.core_manager.clearRenderTargetList()

        width = self.renderer.width
        height = self.renderer.height

        fullsize_x = width
        fullsize_y = height
        halfsize_x = int(width / 2)
        halfsize_y = int(height / 2)

        RenderTargets.BACKBUFFER = self.create_rendertarget(
            "BACKBUFFER",
            Texture2D,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA8,
            texture_format=GL_BGRA,
            data_type=GL_UNSIGNED_BYTE,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        RenderTargets.DEPTHSTENCIL = self.create_rendertarget(
            "DEPTHSTENCIL",
            Texture2D,
            option=Option.SSAA,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_DEPTH24_STENCIL8,
            texture_format=GL_DEPTH_STENCIL,
            data_type=GL_UNSIGNED_INT_24_8,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        RenderTargets.HDR = self.create_rendertarget(
            "HDR",
            Texture2D,
            option=Option.MSAA | Option.SSAA,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA16F,
            texture_format=GL_BGRA,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            data_type=GL_FLOAT,
            wrap=GL_CLAMP
        )

        RenderTargets.DIFFUSE = self.create_rendertarget(
            "DIFFUSE",
            Texture2D,
            option=Option.SSAA,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA8,
            texture_format=GL_BGRA,
            data_type=GL_UNSIGNED_BYTE,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        RenderTargets.MATERIAL = self.create_rendertarget(
            "MATERIAL",
            Texture2D,
            option=Option.SSAA,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA8,
            texture_format=GL_BGRA,
            data_type=GL_UNSIGNED_BYTE,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        RenderTargets.WORLD_NORMAL = self.create_rendertarget(
            "WORLD_NORMAL",
            Texture2D,
            option=Option.SSAA,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA8,
            texture_format=GL_BGRA,
            data_type=GL_UNSIGNED_BYTE,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        # It must attach to depth render target
        RenderTargets.SHADOWMAP = self.create_rendertarget(
            "SHADOWMAP",
            Texture2D,
            width=1024,
            height=1024,
            internal_format=GL_DEPTH_COMPONENT32,
            texture_format=GL_DEPTH_COMPONENT,
            data_type=GL_FLOAT,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        # It must attach to color render target
        RenderTargets.LINEAR_DEPTH = self.create_rendertarget(
            "LINEAR_DEPTH",
            Texture2D,
            width=fullsize_x,
            height=fullsize_x,
            internal_format=GL_R32F,
            texture_format=GL_RED,
            data_type=GL_FLOAT,
            min_filter=GL_NEAREST,
            mag_filter=GL_NEAREST,
            wrap=GL_CLAMP
        )

        RenderTargets.SCREEN_SPACE_REFLECTION = self.create_rendertarget(
            "SCREEN_SPACE_REFLECTION",
            Texture2D,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA8,
            texture_format=GL_BGRA,
            data_type=GL_UNSIGNED_BYTE,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        RenderTargets.SSAO = self.create_rendertarget(
            "SSAO",
            Texture2D,
            width=fullsize_x,
            height=fullsize_x,
            internal_format=GL_R16F,
            texture_format=GL_RED,
            data_type=GL_FLOAT,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        texture_size = 4
        texture_data = np.zeros((texture_size * texture_size, 3), dtype=np.float16)
        for i in range(texture_size * texture_size):
            texture_data[i][0] = random.uniform(-1.0, 1.0)
            texture_data[i][1] = 0.0
            texture_data[i][2] = random.uniform(-1.0, 1.0)
            texture_data[i][:] = normalize(texture_data[i])

        RenderTargets.SSAO_ROTATION_NOISE = self.create_rendertarget(
            "SSAO_ROTATION_NOISE",
            Texture2D,
            width=texture_size,
            height=texture_size,
            internal_format=GL_RGB16F,
            texture_format=GL_RGB,
            data_type=GL_FLOAT,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_REPEAT,
            data=texture_data
        )

        RenderTargets.VELOCITY = self.create_rendertarget(
            "VELOCITY",
            Texture2D,
            option=Option.SSAA,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RG32F,
            texture_format=GL_RG,
            data_type=GL_FLOAT,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        RenderTargets.TEMP_RGBA8 = self.create_rendertarget(
            "TEMP_RGBA8",
            Texture2D,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA8,
            texture_format=GL_BGRA,
            data_type=GL_UNSIGNED_BYTE,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        RenderTargets.TEMP_HDR = self.create_rendertarget(
            "TEMP_HDR",
            Texture2D,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA16F,
            texture_format=GL_BGRA,
            data_type=GL_FLOAT,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        RenderTargets.TEMP_MULTISAMPLE_X4 = self.create_rendertarget(
            "TEMP_MULTISAMPLE_X4",
            Texture2DMultiSample,
            multisample_count=4,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA8,
            texture_format=GL_BGRA,
            data_type=GL_UNSIGNED_BYTE,
            min_filter=GL_LINEAR,
            mag_filter=GL_LINEAR,
            wrap=GL_CLAMP
        )

        RenderTargets.TEMP_RENDER_BUFFER_MULTISAMPLE = self.create_rendertarget(
            "TEMP_RENDER_BUFFER_MULTISAMPLE",
            RenderBuffer,
            multisample_count=4,
            width=fullsize_x,
            height=fullsize_y,
            internal_format=GL_RGBA8,
            wrap=GL_CLAMP
        )
