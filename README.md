# conan_unified_api
Compatibility layer for Conan 1 and 2 for Python.

![https://pypi.org/project/conan-unified_api/](https://img.shields.io/pypi/v/conan-unified_api?logo=pypi)
![PyPI Python versions](https://img.shields.io/pypi/pyversions/conan-unified_api?logo=python)
![Python Tests](https://github.com/goszpeti/conan_unified_api/actions/workflows/test.yml/badge.svg)
![SonarStatus](https://sonarcloud.io/api/project_badges/measure?project=goszpeti_conan_unified_api&metric=alert_status)

## Supported Conan versions
 
* 1.X: from 1.48 to latest
* 2.X from 2.0.14 to 2.7

## Supported APIs

* Local package handling and path queries
* Remote package queries and installation
* Editable handling
* Remotes handling

## Test matrix

Tested Conan 1 versions: 1.48, 1.59.0 and latest
Tested Conan 2 versions: all minor versions until latest

 **Python/OS.** | **3.8** | **3.9** | **3.10** | **3.11** | **3.12** 
----------------|---------|---------|----------|----------|----------
 **u20**        | conan1  |conan1   |conan1&2  |conan1    |          
 **u22**        |         |         |          |          |conan1&2
 **win**        |         |         |          |conan1    |conan2
