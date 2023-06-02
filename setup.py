from setuptools import setup, find_packages

print("fcs")
print("fcs")
print("fcs")
print("fcs")
print("fcs")

print(find_packages())
      

setup(name='bbquiz',
      version='0.2',
      description="A commonand tool for generating quizzes for BlackBoard and Latex",
      author='Francois Pitie',
      author_email='pitief@tcd.ie',
      license='GPLv3',
      package_dir={'': 'src'},
      package_data={'bbquiz': ['templates/*']},
      packages=['bbquiz', 'bbquiz.bbyaml', 'bbquiz.render', 'bbquiz.markdown'],

      install_requires=[
          'markdown','bs4','strictyaml','rich', 'rich-argparse',
          'jinja2', 'colorama', 'watchdog', 'mistletoe', 'appdirs'
      ],      
      entry_points={
          "console_scripts": [
              "bbquiz = bbquiz.cli:main"
          ]
      },
      python_requires='>3.5',
      )


