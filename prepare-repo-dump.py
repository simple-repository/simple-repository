from pathlib import Path
import shutil

import tomlkit

here = Path(__file__).parent

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
