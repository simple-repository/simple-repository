import pathlib
import shutil

import tomlkit

here = pathlib.Path(__file__).parent

build = here / 'built-repo'
if build.is_dir():
    shutil.rmtree(build)
build.mkdir()

srb = build / 'simple_repository'
shutil.copytree(here / 'simple_repository', srb)

for pcache in build.glob('**/__pycache__'):
    shutil.rmtree(pcache)

(srb / '_version.py').unlink()

for file in [here / 'pyproject.toml']:
    shutil.copy(file, build)

pyproject_path = build / 'pyproject.toml'
pyproject_content = tomlkit.parse(pyproject_path.read_text())
del pyproject_content['project']['maintainers']
pyproject_content['project']['urls']['Homepage'] = (
    "https://github.com/simple-repository/simple-repository"
)
pyproject_path.write_text(tomlkit.dumps(pyproject_content) + '\n')

for path in build.glob('**/*.py'):
    content = path.read_text()
    content = '\n'.join([
        '# Copyright (C) 2023, CERN',
        '# This software is distributed under the terms of the MIT',
        '# licence, copied verbatim in the file "LICENSE".',
        '# In applying this license, CERN does not waive the privileges and immunities',
        '# granted to it by virtue of its status as Intergovernmental Organization',
        '# or submit itself to any jurisdiction.',
        '',
    ]) + '\n' + content.lstrip()
    content = content.rstrip() + '\n'
    path.write_text(content, 'utf-8')
