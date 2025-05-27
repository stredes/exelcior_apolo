import platform
import sys

def is_windows():
    return platform.system().lower() == "windows"

def is_linux():
    return platform.system().lower() == "linux"

def get_platform_name():
    return platform.system()
