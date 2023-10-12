import shutil
from pathlib import Path

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


for file in [here / 'setup.py', here / 'pyproject.toml']:
    shutil.copy(file, build)

content = (build/'setup.py').read_text()
new_content = []
for line in content.split('\n'):
    indent = line.split('author=')[0]
    indent = ' ' * (len(line) - len(line.lstrip()))
    if 'author=' in line:
        line = f'{indent}author="CERN, BE-CSS-SET",'
        new_content.append(line)
        continue

    if 'author' in line:
        continue
    if 'maintainer' in line:
        continue
    if 'url' in line:
        line = f'{indent}url="https://github.com/simple-repository/simple-repository",'
    new_content.append(line)

content = '\n'.join(new_content)
content = content.replace('acc-py-index~=3.0', 'simple-repository')
(build/'setup.py').write_text(content)


for file in build.glob('**/templates/base/*'):
    if not file.is_file():
        continue
    content = file.read_text()
    content = content.replace(
        'https://gitlab.cern.ch/acc-co/devops/python/prototypes/simple-pypi-frontend',
        'https://github.com/simple-repository/simple-repository-browser',
    )
    file.write_text(content)
