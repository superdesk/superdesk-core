.
# Superdesk Core library
[![Test](https://github.com/superdesk/superdesk-core/actions/workflows/tests.yml/badge.svg)](https://github.com/superdesk/superdesk-core/actions/workflows/tests.yml)
[![Lint](https://github.com/superdesk/superdesk-core/actions/workflows/lint.yml/badge.svg)](https://github.com/superdesk/superdesk-core/actions/workflows/lint.yml)
[![Documentation Status](https://readthedocs.org/projects/superdesk/badge/?version=latest)](https://superdesk.readthedocs.io/en/latest/?badge=latest)

Utilities for building Superdesk applications.

### Installation

For installation instructions, please refer to the README file at: [https://github.com/superdesk/superdesk/](https://github.com/superdesk/superdesk/ "")

#### Linux: `pyexiv2` requirements

Superdesk Core installs `pyexiv2` by default on Linux, including on CI and
deployments that do not process images. It is not installed automatically on
other platforms.

The upstream Linux wheels for x86-64 and ARM64 bundle `libexiv2`, so a separate
system Exiv2 package is not needed when using a compatible wheel. These wheels
require a glibc-based image and the C++ runtime. On minimal Debian/Ubuntu
images, make sure `libstdc++6` is installed in the runtime image.

If `pip` cannot find a compatible wheel for your Python version, architecture,
or libc (for example, on Alpine's musl), use a glibc-based image with a matching
wheel or follow the [upstream build instructions](https://github.com/LeoHsiao1/pyexiv2/blob/master/pyexiv2/lib/README.md).
A manual build requires a C++ compiler, Python development headers, `pybind11`,
and matching Exiv2 headers and libraries. On Debian/Ubuntu, these are provided
by `build-essential`, the development package for the Python version in use
(for example, `python3-dev`), and `libexiv2-dev`; install `libstdc++6` in the
runtime image as well.

Workers that process staged media uploads also need the separate `exiftool`
executable (`libimage-exiftool-perl` on Debian/Ubuntu).

### Translations

#### Extracting messages

You can run `python setup.py extract_messages` to update `server.pot` file and commit changes to github.
Transifex will automatically fetch it and update the source.
