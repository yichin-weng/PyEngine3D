import os

from Utilities import Logger

log_level = Logger.INFO  # Logger.DEBUG, Logger.INFO, Logger.WARNING, Logger.ERROR
logger = Logger.getLogger(level=log_level)

from .Command import COMMAND, get_command_name, CustomPipe, CustomQueue
from .CoreManager import CoreManager
from .SceneManager import SceneManager
from .ProjectManager import ProjectManager