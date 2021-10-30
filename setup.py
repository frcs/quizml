from setuptools import setup

setup(name='bbquiz',
      version='0.1',
      author='Francois Pitie',
      packages=['bbquiz'],
      entry_points={
          "console_scripts": [
              "bbquiz = bbquiz.__main__:main"
          ]
      }
      )


