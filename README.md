# Docmaker Robot

This robot can parse Robot Framework and Python source files and create a documentation website based on the documentation written into those source files. The most basic way to utilize this bot is to create a folder within your robot called `docmaker` and then `cd` into it. You would then use the following `rcc` command to pull this robot and run it. It will attempt to create a documentation website based on your robot repo.

```shell
rcc pull github.com/robocorp/docmaker
rcc run
```

There are several more advanced ways to configure this bot or even utilize the code as a standalone `invoke` task within your own project directly, read on for more!

## Using Parameters to Control Parsing

The underlying task allows for several parameters which you can use to control the specific files you wish to parse. Parameters can be passed to the robot by appending `--` after `rcc run`, like so:

```shell
rcc run -- --source-path path/to/source/file.py
```

* `--source-path`: Optional. Defines a path to source files. All
    files within this path will be parsed for documentation. Defaults
    to local directory ``source`` in robot's root folder, or the
    parent of the robot's root folder, if local ``source`` is empty.
* `--source-robot`: Optional. Defines the ``robot.yaml`` file to
    reference from the provided source path. Defaults to ``robot.yaml``.
* `--include`: Optional. List of source files to parse from
    ``source-path``. If not included, all source files will be parsed for
    documentation. These can be provided using Python dot-notation
    or as paths to the individual source files. They must be relative
    to ``source-path``.
* `--exclude`: Optional. List of source files to be excluded
    from parsing. These can be provided using Python dot-notation
    or as paths to the individual source files. They must be relative
    to ``source-path``.
* `--project-title`: If provided, the documentation will use this
    string as it's main title, otherwise it will Titleize the name
    of the source path's root folder.
* `--language`: Defaults to ``rfw`` for Robot Framework. This
    will read the source files as Robot Framework libraries. Allowed
    values are:

    - ``rfw``: interprets modules and classes as Robot Framework
    libraries and generated keyword documentation.
    - ``python``: interprets modules as Python modules and
    documents them as programmatic APIs.

* `--in-project`: Optional flag. Set this flag if you are invoking
    this package from inside your own robot/project and have installed
    all of this project's dependencies in your own conda.yaml.

## Dependency Management

In order to successfully parse custom Python classes which use dependencies outside of the built in libraries, you will need to manage your dependencies to allow this robot and your own code to run simultaneously. If your `source-path` is a directory that includes a `robot.yaml` and `conda.yaml` this robot will attempt to create a combined temporary `temp_conda.yaml` which it then uses to execute the parse within. In some cases, this may fail, especially if your source utilizes the similar dependencies as this robot but with different version numbers. In that case, you should execute this robot `in-project` by creating a new `conda.yaml` that includes all dependencies from this robot's `conda.yaml` and then updating this robot's `robot.yaml` to point to this new `conda.yaml` by updating the `condaConfigFile` node and deleting all of the `environmentConfigs`.

For example, if your robot has the following `conda.yaml`:

```yaml
channels:
  - conda-forge

dependencies:
  - python=3.9.13               # https://pyreadiness.org/3.9/ 
  - pip=22.1.2                  # https://pip.pypa.io/en/stable/news/
  - pip:
      - rpaframework==17.4.0    # https://rpaframework.org/releasenotes.html
      - undetected-chromedriver==3.1.5.post4
```

Then you would need to create a new `combined_conda.yaml` like the following:

```yaml
channels:
  - conda-forge

dependencies:
  - python=3.9.13               # https://pyreadiness.org/3.9/ 
  - sphinx=5.3.0                # https://github.com/conda-forge/sphinx-feedstock
  - invoke=1.7.3                # https://www.pyinvoke.org/changelog.html#{}
  - pyyaml=5.4.1                # https://pyyaml.org/wiki/PyYAML
  - pip=22.1.2                  # https://pip.pypa.io/en/stable/news/
  - pip:
      - rpaframework==17.4.0    # https://rpaframework.org/releasenotes.html
      - undetected-chromedriver==3.1.5.post4
      - robotframework-docgen==0.15.0    # https://github.com/robocorp/robotframework-docgen
      - robotframeworklexer==1.1         # https://github.com/robotframework/pygmentslexer
      - inflection==0.5.1                # https://inflection.readthedocs.io/en/latest/#changelog
```

Finally, you would update this robot's `robot.yaml` to look something like this:

```yaml
tasks:
  Build documentation:
    shell: invoke generate-documentation 

devTasks:
  Use config:
    # You can pass a path by appending `-- path/to/config` after the rcc command.
    shell: invoke parse-yaml-config-and-run

  Host documentation:
    shell: python -u -m http.server -d output

  Clean local repo:
    shell: invoke clean

condaConfigFile: ../relative/path/to/source/combined_conda.yaml

artifactsDir: output  

PATH:
  - .
  - libs
  - ../relative/path/from/source/robot
PYTHONPATH:
  - .
  - libs
  - ../relative/path/from/source/robot
ignoreFiles:
  - .gitignore
```

You may also need to combined the entries from your `PATH` and `PYTHONPATH` as well so that this robot can find custom files. Please use **RELATIVE** paths here because `rcc` expects all paths in config files to be relative.

## Advanced Invocations

The above section can be used as a starting point if you want to include this robot's `tasks.py` as an [Invoke](https://www.pyinvoke.org/) script within your project. If you include this robot's dependencies in your project and then include the `tasks.py` in your project's root folder and `documenter.py` file within your project's `libs` folder, you are able to execute the task directly from your robot's directory via the command `invoke generate-documentation`.