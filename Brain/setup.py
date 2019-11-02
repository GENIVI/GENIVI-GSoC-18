from setuptools import setup

setup(name='emucorebrain',
      version='0.5.6',
      description='Brain of EmulationCore',
      url='https://github.com/GENIVI/GENIVI-GSoC-18/tree/master/Brain/core',
      author='Chandeepa Dissanayake',
      author_email='chandeepadissanayake@gmail.com',
      license='Mozilla Public License 2.0',
      packages=['emucorebrain.consts', 'emucorebrain.core', 'emucorebrain.data', 'emucorebrain.data.abstracts',
                'emucorebrain.data.carriers', 'emucorebrain.data.containers', 'emucorebrain.data.models',
                'emucorebrain.io', 'emucorebrain.io.mechanisms', 'emucorebrain.keywords', 'emucorebrain.processes'],
      install_requires=["nltk==3.4.5"],
      zip_safe=False
      )
