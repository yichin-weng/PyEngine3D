import os, glob, configparser

from OpenGL.GL import *
from OpenGL.GL.shaders import *
from OpenGL.GL.shaders import glDetachShader

from Render import *
from Core import logger
from Utilities import Singleton
from Render import Shader, Material
from Object import Triangle, Quad, Mesh

#------------------------------#
# CLASS : ShaderLoader
#------------------------------#
class ShaderLoader(Singleton):
    def __init__(self):
        self.vertexShaders = {}
        self.fragmentShader = {}
        self.shaders = {GL_VERTEX_SHADER:self.vertexShaders, GL_FRAGMENT_SHADER:self.fragmentShader}

    def initialize(self):
        logger.info("initialize " + self.__class__.__name__)

        # collect shader files
        for filename in glob.glob(os.path.join(PathShaders, '*.*')):
            shaderFile = os.path.split(filename)[1]
            shaderName, ext = os.path.splitext(shaderFile)
            if ext == '.vs':
                shaderType = GL_VERTEX_SHADER
            elif ext == '.fs':
                shaderType = GL_FRAGMENT_SHADER
            else:
                logger.warn("Shader error : %s is invalid shader. Shader file extension must be one of '.vs', '.ps', '.cs'..." % filename)
                continue

            try:
                # create shader
                f = open(filename, 'r')
                shaderSource = f.read()
                f.close()
                shader = Shader(shaderName, shaderSource, shaderType)
                # regist shader. self.shaders include self.vertexShaders, self.fragmentShaders as dict.
                self.shaders[shaderType][shaderName] = shader
            except BaseException("Shader error."):
                logger.error(traceback.format_exc())

    def close(self):
        for shaders in self.shaders.values():
            for shaderName in shaders:
                shaders[shaderName].delete()

    def getVertexShader(self, shaderName):
        return self.vertexShaders[shaderName] if shaderName in self.vertexShaders else None

    def getFragmentShader(self, shaderName):
        return self.fragmentShader[shaderName] if shaderName in self.fragmentShader else None


#------------------------------#
# CLASS : MaterialLoader
#------------------------------#
class MaterialLoader(Singleton):
    def __init__(self):
        self.materials = {}
        self.default_material = None

    def initialize(self):
        logger.info("initialize " + self.__class__.__name__)
        shaderLoader = ShaderLoader.instance()

        # create materials
        for filename in glob.glob(os.path.join(PathMaterials, "*.*")):
            if os.path.splitext(filename)[1].lower() == ".material":
                materialFile = configparser.ConfigParser()
                materialFile.read(filename)
                vs = shaderLoader.getVertexShader(materialFile.get("VertexShader", "shaderName"))
                fs = shaderLoader.getFragmentShader(materialFile.get("FragmentShader", "shaderName"))
                materialName = os.path.splitext(os.path.split(filename)[1])[0]
                material = self.createMaterial(name=materialName, vs=vs, fs=fs)
                self.materials[materialName] = material
        self.default_material = self.getMaterial('default')

    def createMaterial(self, name, vs, fs):
        if name in self.materials:
            raise BaseException("There is same material.")
        material = Material(name=name, vs=vs, fs=fs)
        self.materials[name] = material
        return material

    def getDefaultMaterial(self):
        return self.default_material

    def getMaterial(self, name):
        return self.materials[name]


#------------------------------#
# CLASS : MeshLoader
#------------------------------#
class MeshLoader(Singleton):
    def __init__(self):
        self.meshes = {}

    def initialize(self):
        logger.info("initialize " + self.__class__.__name__)

        # Regist meshs
        self.meshes['Triangle'] = Triangle()
        self.meshes['Quad'] = Quad()
        # regist obj files
        for filename in glob.glob(os.path.join(PathMeshes, '*.mesh')):
            name = os.path.splitext(os.path.split(filename)[1])[0]
            name = name[0].upper() + name[1:]
            self.meshes[name] = Mesh(name, filename)

    def getMeshNameList(self):
        return list(self.meshes.keys())

    def getMeshByName(self, meshName):
        return self.meshes[meshName] if meshName in self.meshes else None


#------------------------------#
# CLASS : ResourceManager
#------------------------------#
class ResourceManager(Singleton):
    def __init__(self):
        self.shaderLoader = ShaderLoader.instance()
        self.materialLoader = MaterialLoader.instance()
        self.meshLoader = MeshLoader.instance()

    def initialize(self):
        self.shaderLoader.initialize()
        self.materialLoader.initialize()
        self.meshLoader.initialize()

    def close(self):
        self.shaderLoader.close()

    #------------------------------#
    # FUNCTIONS : Material
    #------------------------------#
    def getMaterial(self, name):
        return self.materialLoader.getMaterial(name)

    def getDefaultMaterial(self):
        return self.materialLoader.getDefaultMaterial()

    #------------------------------#
    # FUNCTIONS : Mesh
    #------------------------------#
    def getMeshNameList(self):
        return self.meshLoader.getMeshNameList()

    def getMeshByName(self, meshName):
        return self.meshLoader.getMeshByName(meshName)