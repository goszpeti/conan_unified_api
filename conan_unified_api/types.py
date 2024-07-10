from __future__ import annotations
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
import os
import platform
import pprint
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union
from typing_extensions import TypeAlias

from conan_unified_api import conan_version

from conans.errors import ConanException


if conan_version.major == 1:
    from conans.model.ref import ConanFileReference, PackageReference # type: ignore
    from conans.paths.package_layouts.package_editable_layout import PackageEditableLayout
    if platform.system() == "Windows":
        from conans.util.windows import CONAN_REAL_PATH, CONAN_LINK
else:
    from conans.model.recipe_ref import RecipeReference as ConanFileRef  # type: ignore
    from conans.model.package_ref import PkgReference  # type: ignore
    class PackageReference(PkgReference): # type: ignore
        """ Compatibility class for changed package_id attribute """
        ref: ConanRef
        
        @property
        def id(self):
            return self.package_id

        @staticmethod
        def loads(text: str) -> ConanPkgRef:
            pkg_ref = PkgReference.loads(text)
            return PackageReference(pkg_ref.ref, pkg_ref.package_id, 
                                    pkg_ref.revision,pkg_ref.timestamp)

    class ConanFileReference(ConanFileRef):
        name: str
        version: str
        user: Optional[str]
        channel: Optional[str]

        @staticmethod
        def loads(text: str, validate=True) -> ConanRef:
            ref: ConanRef = ConanFileRef().loads(text) # type: ignore
            if validate:
                # validate_ref creates an own output stream which can't log to console
                # if it is running as a gui application
                devnull = open(os.devnull, 'w')
                with redirect_stdout(devnull):
                    with redirect_stderr(devnull):
                        ref.validate_ref(allow_uppercase=True)
            return ref

@dataclass
class Remote():
    name: str
    url: str
    verify_ssl: bool
    disabled: bool
    allowed_packages: Optional[List[str]] = None

from conans.errors import ConanException

ConanRef: TypeAlias = ConanFileReference
ConanPkgRef: TypeAlias = PackageReference
ConanOptions: TypeAlias = Dict[str, Any]
ConanAvailableOptions: TypeAlias = Dict[str, Union[List[Any], Literal["ANY"]]]
ConanSettings: TypeAlias = Dict[str, str]
ConanPackageId: TypeAlias = str
ConanPackagePath: TypeAlias = Path

    
class ConanPkg(TypedDict, total=False):
    """ Dummy class to type conan returned package dicts """

    id: ConanPackageId
    options: ConanOptions
    settings: ConanSettings
    requires: List[Any]
    outdated: bool


@dataclass
class EditablePkg():
    conan_ref: str
    path: str # path to conanfile or folder
    output_folder: Optional[str]

def pretty_print_pkg_info(pkg_info: ConanPkg) -> str:
    return pprint.pformat(pkg_info).translate(
        {ord("{"): None, ord("}"): None, ord("'"): None})


class LoggerWriter:
    """
    Dummy stream to log directly to a logger object, when writing in the stream.
    Used to redirect custom stream from Conan. 
    Adds a prefix to do some custom formatting in the Logger.
    """

    def __init__(self, level, prefix: str):
        self.level = level
        self._prefix = prefix

    def write(self, message: str):
        if message != '\n':
            self.level(self._prefix + message.strip("\n"))

    def flush(self):
        """ For interface compatiblity """
        pass

