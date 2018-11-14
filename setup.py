import sys
from cx_Freeze import setup, Executable

# Dependency list.
build_exe_options = {
    'packages': ['asyncio', 'pygame'], 
    'excludes': ['tkinter', 'numpy'],
    'include_files': ['textures']
}
# Base for GUI apps on Windows.
base = 'Win32GUI' if sys.platform == 'win32' else None

setup(
    name = 'pyPong',
    version = '1.2',
    description = 'Pygame/Asyncio Pong Test',
    url = '',
    author = 'virtuNat',
    author_email = '',
    license = 'GPL',
    options = {'build_exe': build_exe_options},
    executables = [Executable('pyPong.py', base=base)],
    )
        