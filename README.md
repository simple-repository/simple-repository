# simple-repository

The core simple repository (PEP-503) interface, including powerful component implementations suitable for use in repository clients and servers.

## About

The ``simple-repository`` core library provides a base ``SimpleRepository`` class, with interfaces for
each of the endpoints of the PEP-503 simple repository, namely ``get_project_list`` and ``get_project_page``.
Furthermore, it exposes an interface for resource retrieval (``get_resource``), offering the possibility to dynamically
control the entire repository interaction from tools such as ``pip``.

Subclasses of the ``SimpleRepository``, commonly referred to as repository "components", are free to specialise the
repository behaviour according to their function. Components may contain other components, and in doing so, a
directed acyclic graph of repositories can be built-up:

![example project page](https://raw.githubusercontent.com/simple-repository/simple-repository/main/.content/flow.png)

The resulting ``SimpleRepository`` allows repository consumers (either clients or servers) to query the
"virtual repository" definition as if it were a traditional file or http based repository.

Some of the implemented components in this repository include:

* ``HTTPRepository``: represents a http-based PEP-503 compatible simple repository
* ``LocalRepository``: represents a directory containing many project directories, each with its own files/distributions
* ``PrioritySelectedProjectsRepository``: represents the combination of an ordered set of repositories, merged
  such that when choosing a project, the first repository to contain the project will be used.
  This component is designed to mitigate the [dependency confusion](https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610) attack.
* ``MetadataInjectorRepository``: with the advent of PEP-658, installers no longer need to download the whole distribution in order to determine
  a project's metadata (e.g. its dependencies). This repository will compute the metadata on the fly by inspecting the distribution (e.g. a wheel).
  The component allows downstream consumers (both clients and servers) to assume the existence of metadata, even though the originating
  repository may not itself provide any.
* ```AllowListedRepository```: represents a repository which only permits projects to be accessed from a defined list of allowed projects.

There are many such components in this library. In the case that a desired component doesn't already exist, implementing a new one is a matter of
implementing a small number of methods. The resulting implementations are reusable, concise, and are easy to validate and test.

## Known usage

Here are some of the known uses of the ``simple-repository`` core library:

* [``simple-repository-server``](https://github.com/simple-repository/simple-repository-server): A tool for running a PEP-503 simple Python package repository, including features such as dist metadata (PEP-658) and JSON API (PEP-691)
* [``simple-repository-browser``](https://github.com/simple-repository/simple-repository-browser): A web interface to browse and search packages in any simple package repository (PEP-503), inspired by PyPI / warehouse
* [``pypi-timemachine``](https://github.com/astrofrog/pypi-timemachine): Install packages with pip as if you were in the past! pypi-timemachine allows you to see a package repository as it would have been at any given time

If you know of other uses of ``simple-repository``, please submit a PR to add them to the list.


## License and Support

This code has been released under the MIT license.
It is an initial prototype which is developed in-house, and _not_ currently openly developed.

It is hoped that the release of this prototype will trigger interest from other parties that have similar needs.
With sufficient collaborative interest there is the potential for the project to be openly
developed, and to power Python package repositories across many domains.

Please get in touch at https://github.com/orgs/simple-repository/discussions to share how
this project may be useful to you. This will help us to gauge the level of interest and
provide valuable insight when deciding whether to commit future resources to the project.
