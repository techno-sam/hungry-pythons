# Hungry Pythons
A game similar to slither.io, written in Python 3.6

## How you can help
See projects tab.

## Downloading Pre-built Binaries
1. Go to the [Releases](https://github.com/techno-sam/hungry-pythons/releases) tab
1. Open the development bulid for your operating system
1. Download the \<OS\>\_binaries.zip file (for example, linux_binaries.zip) in the Assets section
1. Unzip the downloaded archive
1. See the [Recommended Parameters](#recommended-parameters) section of this readme for more information

## Building
1. Clone or download this repository.
1. Install Python 3.6
1. Execute the following commands in the directory this README file is in.
    1. python3 -m pip install --upgrade pip
    1. python3 -m pip install pygame==1.9.6
    1. pip install -r src/requirements.txt
    1. python3 -m PyInstaller src/client2.spec
    1. python3 -m PyInstaller src/server.spec
1. Find the binaries in ./dists/

## Recommended Parameters
For client:
```shell
/path/to/client2 --host 127.0.0.1 --port 9999 --view_dist 475
```
For server:
```shell
/path/to/server --host 127.0.0.1 --port 9999 --border 2000 --timeout 15
```

## Licensing
This project is licensed under the GNU General Public License v3.0.
For more information, see [license](LICENSE).
