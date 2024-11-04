from __future__ import annotations

import os
import platform
import pprint
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict, Union

from conans.errors import ConanException  # noqa: F401
from typing_extensions import TypeAlias

from conan_unified_api import conan_version

if conan_version.major == 1:
    from conans.model.ref import ConanFileReference, PackageReference
    from conans.paths.package_layouts.package_editable_layout import (
        PackageEditableLayout,  # noqa: F401
    )

    if platform.system() == "Windows":
        from conans.util.windows import CONAN_LINK, CONAN_REAL_PATH
else:
    from conans.model.package_ref import PkgReference
    from conans.model.recipe_ref import RecipeReference as ConanFileRef

    class PackageReference(PkgReference):
        """Compatibility class for changed package_id attribute"""

        ref: ConanRef

        @property
        def id(self) -> str:
            return self.package_id

        @staticmethod
        def loads(text: str) -> ConanPkgRef:
            pkg_ref = PkgReference.loads(text)
            return PackageReference(
                pkg_ref.ref, pkg_ref.package_id, pkg_ref.revision, pkg_ref.timestamp
            )

    class ConanFileReference(ConanFileRef):
        """Compatibility class for validation in loads method"""

        name: str
        version: str
        user: Optional[str]
        channel: Optional[str]

        @staticmethod
        def loads(text: str, validate: bool = True) -> ConanRef:  # type: ignore
            # add back support for @_/_ canonical refs to handle this uniformly
            # Simply remove it before passing it to ConanFileRef
            if text.endswith("@_/_"):
                text = text.replace("@_/_", "")
            ref: ConanRef = ConanFileRef().loads(text)  # type: ignore
            if validate:
                # validate_ref creates an own output stream which can't log to console
                # if it is running as a gui application
                with open(os.devnull, "w") as devnull:
                    with redirect_stdout(devnull), redirect_stderr(devnull):
                        ref.validate_ref(allow_uppercase=True)
            return ref


@dataclass
class Remote:
    name: str
    url: str
    verify_ssl: bool
    disabled: bool
    allowed_packages: Optional[List[str]] = None


ConanRef: TypeAlias = ConanFileReference
ConanPkgRef: TypeAlias = PackageReference
ConanOptions: TypeAlias = Dict[str, Any]
ConanAvailableOptions: TypeAlias = Dict[str, Union[List[Any], Literal["ANY"]]]
ConanSettings: TypeAlias = Dict[str, str]
ConanPackageId: TypeAlias = str
ConanPackagePath: TypeAlias = Path


class ConanPkg(TypedDict, total=False):
    """Dummy class to type conan returned package dicts"""

    id: ConanPackageId
    options: ConanOptions
    settings: ConanSettings
    requires: List[Any]
    outdated: bool


@dataclass
class EditablePkg:
    conan_ref: str
    path: str  # path to conanfile or folder
    output_folder: Optional[str]


def pretty_print_pkg_info(pkg_info: ConanPkg) -> str:
    return pprint.pformat(pkg_info).translate({ord("{"): None, ord("}"): None, ord("'"): None})


class LoggerWriter:
    """
    Dummy stream to log directly to a logger object, when writing in the stream.
    Used to redirect custom stream from Conan.
    Adds a prefix to do some custom formatting in the Logger.
    """

    disabled = False

    def __init__(self, level: Callable, prefix: str):
        self.level = level
        self._prefix = prefix

    def write(self, message: str) -> None:
        if self.disabled:
            return
        if message != "\n":
            self.level(self._prefix + message.strip("\n"))

    def flush(self) -> None:
        """For interface compatiblity"""
