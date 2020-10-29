from setuptools import setup, find_packages

VERSION = "0.1.6"
DESCRIPTION = "A Python package to run, control/manipulate and analyse SWAT2012 models"
LONG_DESCRIPTION = "a set of python modules to work with the Soil and Water Assessment Tool (SWAT2012), including model run, programmatic config edits, simulation readouts and calibration with the fantastic SPOTPY package - more info to come!"

# Setting up
setup(
    # the name must match the folder name 'swatpy'
    name="swatpy",
    version=VERSION,
    author="Alexander Kmoch",
    author_email="<alexander.kmoch@ut.ee>",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=[
        "numpy",
        "pandas",
        "spotpy",
        "scipy",
    ],  # add any additional packages that
    # needs to be installed along with your package. Eg: 'caer'
    keywords=["python", "SWAT", "hydrology"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Scientific/Engineering :: GIS",
    ],
)
