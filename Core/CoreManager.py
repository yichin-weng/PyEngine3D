import ctypes
import platform as libPlatform
import sys
import time
import re
import traceback
import threading

import numpy as np
import pygame
from pygame.locals import *
from OpenGL.GL import *

from Core import *
from Object import ObjectManager, primitives
from Render import Renderer, ShaderManager, MaterialManager, CameraManager
from Utilities import *


#------------------------------#
# Function : IsExtensionSupported
# NeHe Tutorial Lesson: 45 - Vertex Buffer Objects
#------------------------------#
reCheckGLExtention = re.compile("GL_(.+?)_(.+)")

def IsExtensionSupported (TargetExtension):
    """ Accesses the rendering context to see if it supports an extension.
        Note, that this test only tells you if the OpenGL library supports
        the extension. The PyOpenGL system might not actually support the extension.
    """
    Extensions = glGetString (GL_EXTENSIONS)
    Extensions = Extensions.split ()
    bTargetExtension = str.encode(TargetExtension)
    for extension in Extensions:
        if extension == bTargetExtension:
            break
    else:
        # not found surpport
        msg = "OpenGL rendering context does not support '%s'" % TargetExtension
        logger.error(msg)
        raise BaseException(msg)

    # Now determine if Python supports the extension
    # Exentsion names are in the form GL_<group>_<extension_name>
    # e.g.  GL_EXT_fog_coord
    # Python divides extension into modules
    # g_fVBOSupported = IsExtensionSupported ("GL_ARB_vertex_buffer_object")
    # from OpenGL.GL.EXT.fog_coord import *
    m = re.match(reCheckGLExtention, TargetExtension)
    if m:
        group_name =  m.groups()[0]
        extension_name = m.groups()[1]
    else:
        msg = "GL unsupport error, %s" % TargetExtension
        logger.error(msg)
        raise BaseException(msg)

    extension_module_name = "OpenGL.GL.%s.%s" % (group_name, extension_name)

    try:
        __import__ (extension_module_name)
        logger.info("PyOpenGL supports '%s'" % TargetExtension)
    except:
        msg = 'Failed to import', extension_module_name
        logger.error(msg)
        raise BaseException(msg)
    return True


#------------------------------#
# CLASS : CoreManager
#------------------------------#
class CoreManager(Singleton):
    """
    Manager other mangers classes. ex) shader manager, material manager...
    CoreManager usage for debug what are woring manager..
    """
    def __init__(self, cmdQueue, uiCmdQueue, cmdPipe):
        self.running = False

        # command
        self.cmdQueue = cmdQueue
        self.uiCmdQueue = uiCmdQueue
        self.cmdPipe = cmdPipe

        # timer
        self.fpsLimit = 1.0 / 60.0
        self.fps = 0.0
        self.delta = 0.0
        self.currentTime = 0.0

        # mouse
        self.mousePos = np.zeros(2)
        self.mouseOldPos = np.zeros(2)
        self.mouseDelta = np.zeros(2)
        self.wheelUp = False
        self.wheelDown = False

        # managers
        self.renderer = Renderer.instance()
        self.console = self.renderer.console
        self.camera = None
        self.cameraManager = CameraManager.instance()
        self.objectManager = ObjectManager.instance()
        self.shaderManager = ShaderManager.instance()
        self.materialManager = MaterialManager.instance()

    def initialize(self):
        # process start
        logger.info('Platform : %s' % libPlatform.platform())
        logger.info("Process Start : %s" % self.__class__.__name__)

        # pygame init
        pygame.init()

        # initalize managers
        self.renderer = Renderer.instance()
        self.renderer.initialize(self)

        # ready to launch - send message to ui
        PipeSendRecv(self.cmdPipe, CMD_UI_RUN, CMD_UI_RUN_OK)


    def run(self):
        # main loop
        self.update()

        # send a message to close ui
        if self.uiCmdQueue:
            self.uiCmdQueue.put(CMD_CLOSE_UI)

        # close renderer
        self.renderer.close()

        # save config
        config.save()
        logger.info("Save renderer config file - " + config.getFilename())

        # process stop
        logger.info("Process Stop : %s" % self.__class__.__name__)

        # quit
        pygame.quit()

    def error(self, msg):
        logger.error(msg)
        self.close()

    def close(self):
        self.running = False

    #---------------------------#
    # receive and send messages
    #---------------------------#
    def sendPrimitiveName(self, obj):
        # send object name to GUI
        self.uiCmdQueue.put((CMD_SEND_PRIMITIVENAME, obj.name))

    def sendPrimitiveInfo(self, obj):
        # send object infomation to GUI
        objInfos = self.objectManager.getObjectInfos(obj)
        self.uiCmdQueue.put((CMD_SEND_PRIMITIVEINFOS, objInfos))


    #---------------------------#
    # update functions
    #---------------------------#
    def updateCommand(self):
        while self.cmdQueue and not self.cmdQueue.empty():
            cmd = self.cmdQueue.get()
            value = None

            # check type for tuple - (cmd, value)
            if type(cmd) is tuple:
                cmd, value = cmd

            logger.info("Core CommandQueue (%d, %s)" % (cmd, value))

            # close app
            if cmd == CMD_CLOSE_APP:
                self.close()
                return
            # received request pipe
            elif cmd > CMD_ADD_PRIMITIVE_START and cmd < CMD_ADD_PRIMITIVE_END:
                camera = self.cameraManager.getMainCamera()
                pos = camera.pos + camera.front * -10.0
                primitive = primitives[cmd - CMD_ADD_TRIANGLE]
                obj = self.renderer.objectManager.addPrimitive(primitive, name="", pos=pos)
                obj.updateTransform()
                # send object name to GUI
                self.sendPrimitiveName(obj)
            elif cmd == CMD_REQUEST_PRIMITIVEINFOS:
                # send object infomation to GUI
                obj = self.objectManager.getObject(value)
                self.sendPrimitiveInfo(obj)
            elif cmd == CMD_SET_PRIMITIVEINFO:
                objectName, propertyName, propertyValue = value
                self.objectManager.setObjectData(objectName, propertyName, propertyValue)

    def updateEvent(self):
        # set pos
        self.mouseDelta[:] = self.mousePos - self.mouseOldPos
        self.mouseOldPos[:] = self.mousePos
        self.wheelUp, self.wheelDown = False, False

        for event in pygame.event.get():
            eventType = event.type
            if eventType == QUIT:
                self.close()
            elif eventType == VIDEORESIZE:
                self.renderer.resizeScene(*event.dict['size'])
            elif eventType == KEYDOWN:
                keyDown = event.key
                if keyDown == K_ESCAPE:
                    self.close()
                elif keyDown == K_BACKQUOTE:
                    self.console.toggle()
                elif keyDown == K_1:
                    for i in range(100):
                        pos = [np.random.uniform(-10,10) for i in range(3)]
                        primitive = primitives[np.random.randint(3)]
                        obj = self.renderer.objectManager.addPrimitive(primitive, name="", pos=pos)
                        # send object name to GUI
                        self.sendPrimitiveName(obj)
            elif eventType == MOUSEMOTION:
                self.mousePos[:] = pygame.mouse.get_pos()
            elif eventType == MOUSEBUTTONDOWN:
                self.wheelUp = event.button == 4
                self.wheelDown = event.button == 5

    def updateCamera(self):
        # get pressed key and mouse buttons
        keydown = pygame.key.get_pressed()
        btnL, btnM, btnR = pygame.mouse.get_pressed()

        # get camera
        self.camera = self.cameraManager.getMainCamera()
        moveSpeed = self.delta * 5.0
        rotSpeed = 0.03

        # camera move pan
        if btnL and btnR or btnM:
            self.camera.move(self.camera.right * self.mouseDelta[0] * 0.01)
            self.camera.move(-self.camera.up * self.mouseDelta[1] * 0.01)
        # camera rotation
        elif btnL or btnR:
            self.camera.rotationPitch(-self.mouseDelta[1] * 0.03)
            self.camera.rotationYaw(-self.mouseDelta[0] * 0.03)

        # camera move front/back
        if self.wheelUp:
            self.camera.move(self.camera.front * 5.0)
        elif self.wheelDown:
            self.camera.move(-self.camera.front * 5.0)

        # update camera transform
        if keydown[K_w]:
            self.camera.move(self.camera.front * moveSpeed)
        elif keydown[K_s]:
            self.camera.move(-self.camera.front * moveSpeed)

        if keydown[K_a]:
            self.camera.move(self.camera.right * moveSpeed)
        elif keydown[K_d]:
            self.camera.move(-self.camera.right * moveSpeed)

        if keydown[K_q]:
            self.camera.move(-self.camera.up * moveSpeed)
        elif keydown[K_e]:
            self.camera.move(self.camera.up * moveSpeed)

        if keydown[K_SPACE]:
            self.camera.resetTransform()

        # update camera
        self.camera.updateTransform()

    def update(self):
        self.currentTime = time.time()
        self.running = True
        while self.running:
            currentTime = time.time()
            delta = currentTime - self.currentTime
            updateTime = currentTime

            if delta < self.fpsLimit:
                continue

            # set timer
            self.currentTime = currentTime
            self.delta = delta
            self.fps = 1.0 / delta

            # update
            self.updateCommand() # update command queue
            self.updateEvent() # update keyboard and mouse events
            self.updateCamera() # update camera

            # update time
            updateTime = time.time() - updateTime

            # render scene
            renderTime = time.time()
            self.renderer.renderScene()
            renderTime = time.time() - renderTime

            # render text
            self.console.info("%.2f ms" % (self.delta*1000))
            self.console.info("%.2f fps" % self.fps)
            self.console.info("CPU : %.2f ms" % (updateTime * 1000.0))
            self.console.info("GPU : %.2f ms" % (renderTime * 1000.0))
            self.console.info(self.camera.getTransformInfos())