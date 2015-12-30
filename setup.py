from distutils.core import setup
import py2exe

packages = [
    "twisted",
    "netifaces"
]

options = {
    'py2exe': {
        "optimize": 2,
        "packages": ','.join(packages)
    }
}

setup(
    console=['main.py'],
    options=options
)



