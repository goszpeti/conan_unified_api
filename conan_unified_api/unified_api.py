import logging
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union

from typing_extensions import Self, TypeAlias

from .types import (
    ConanAvailableOptions,
    ConanOptions,
    ConanPackageId,
    ConanPackagePath,
    ConanPkg,
    ConanPkgRef,
    ConanRef,
    ConanSettings,
    EditablePkg,
    Remote,
)

if TYPE_CHECKING:
    from conan_unified_api.cache.conan_cache import ConanInfoCache

UserName: TypeAlias = str
IsAuthenticated: TypeAlias = bool
RemoteName: TypeAlias = str

# Interface and docs


class ConanBaseUnifiedApi:
    """
    API abstraction to provide compatibility between ConanV1 and V2 APIs.
    Thin wrapper:
      If possible, the wrapper will just call the same named method in Conan and add type hints.
      For ConanReferences it will always accept str and ConnReference Objects.
      Return types are almost always objects for References and Packages, so that they can be
      used directly in other functions of this API.

    Paths as return values:
      Paths will set an INVALID_PATH value instead of None if the Path can't be determined.
      This is done, because usually there is always an exists check or something similar,
      which then returns naturally False.
      Otherwise can be checked against the "invalid_path" variable from the conan_unified_api
      namespace.
    Type Hints:
      The wrapper will alias most of the built-in types to the same name and add typedict hints.
      Own implementations are only used to ensure a compatible behavior of conan basic classes
      (like adding the loads method to ConanV2 References)
    Version specific methods:
      In case of a version specific function, the interface will still specify it and the other
      version(s) will simply not do anything or return a default value.
    Exception handling:
      All methods can throw unless noted in the docs. Often the wrapper method will raise a
      ConanException and reference the original error in it.
    """

    @abstractmethod
    def __init__(
        self,
        init: bool = True,
        logger: Optional[logging.Logger] = None,
        mute_logging: bool = False,
    ):
        """
        :param init: Calls init_api function directly in the constructor. Can be disabled for
        faster constructor.
        :param logger: A custom logger can be injected here. Otherwise will use default logger.
        :param mute_logging: Disables the logger, regardless if it was injected ot not.
        Can not raise an exception.
        """
        self.info_cache: ConanInfoCache
        ...

    @abstractmethod
    def init_api(self) -> Self:
        """
        Instantiate the internal Conan api. Can be called extra to split up loading.
        Conan 1 can slow down on init with remove locks noticably, if there are several
        hundred local packages.
        """
        raise NotImplementedError

    @abstractmethod
    def mute_logging(self, mute_logging: bool) -> None:
        """
        Can be used to selectively turn on and off logging for methods.
        :param mute_logging: Disables the logger if set to True, enables it again with false
        """
        raise NotImplementedError

    ### Helper commands ###

    @staticmethod
    @abstractmethod
    def generate_canonical_ref(conan_ref: Union[ConanRef, str]) -> str:
        """Creates a full ref from a short ref, e.g. product/1.0.0 -> product/1.0.0@_/_"""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def conan_ref_from_reflike(conan_ref: Union[ConanRef, str]) -> ConanRef:
        """Creates a ref object if it is a string otherwise returns the object"""
        raise NotImplementedError

    ### General commands ###

    @abstractmethod
    def info(self, conan_ref: Union[ConanRef, str]) -> List[Dict[str, Any]]:
        """
        Calls the conan info method on Conan V1 to return all recipe and pacakges metainfo
        (including paths) for the recipe itself and all the dependencies. The order is random.
        For the ConanV2 version it calls graph info, which is the best equivalent method.
        Original remote argument ommitted. To download a conanfile from a specific remote
        please use inspect with remote argument.
        """
        raise NotImplementedError

    @abstractmethod
    def inspect(
        self,
        conan_ref: Union[ConanRef, str],
        attributes: Sequence[str] = [],
        remote_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a field of the selected conanfile. Works currently only with a reference,
        but not with a path. Recreates the ConanV1 behavior for ConanV2.
        If attributes is empty in ConanV1 a chosen default fields are returned, in ConanV2 all
        of them. If attributes is set, only the selected will be returned in the dict.

        """
        raise NotImplementedError

    @abstractmethod
    def alias(
        self,
        conan_ref: Union[ConanRef, str],
        conan_target_ref: Union[ConanRef, str],
    ) -> None:
        """Creates an alias for the target ref with all local packages. For ConanV1 only."""
        raise NotImplementedError

    @abstractmethod
    def remove_locks(self) -> None:
        """Remove local cache locks. For ConanV1 only."""
        raise NotImplementedError

    ### Profile commands ###

    @abstractmethod
    def get_profiles(self) -> List[str]:
        """Return a list of all profiles"""
        raise NotImplementedError

    @abstractmethod
    def get_profile_settings(self, profile_name: str) -> ConanSettings:
        """Return a dict of settings for a profile"""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def build_conan_profile_name_alias(conan_settings: ConanSettings) -> str:
        """Build a human readable pseduo profile name, like Windows_x64_vs16_v142_release"""
        raise NotImplementedError

    @abstractmethod
    def get_default_settings(self) -> ConanSettings:
        """
        Return the settings of the conan default profile.
        This is not necessarily the same as get_profile_settings("default"),
        because the file content can be changed.
        """
        raise NotImplementedError

    @abstractmethod
    def get_profiles_path(self) -> Path:
        """Get the path to the folder where profiles are located"""
        raise NotImplementedError

    ### Config and settings commands ###

    @abstractmethod
    def get_settings_file_path(self) -> Path:
        """Return conan settings file path (settings.yml)"""
        raise NotImplementedError

    @abstractmethod
    def get_config_file_path(self) -> Path:
        """Return conan config file path (conan.conf)"""
        raise NotImplementedError

    @abstractmethod
    def get_config_entry(self, config_name: str) -> Optional[Any]:
        """Return a conan config entry value (conan.conf).
            Returns None if no entry was set.
        For Conan 1 the format is <section>.<setting_name>, e.g. "general.non_interactive".
            Will evaluate environment variables, which is not consistent to the cli behavior,
            but thus return more accurate results.
            Always returns a string, even for bools.
        For Conan 2 the formt is <section>:<setting_name>, e.g. core:non_interactive
            Returns value correctly typed.
        """
        raise NotImplementedError

    @abstractmethod
    def get_revisions_enabled(self) -> bool:
        """Return if revisions are enabled for Conan V1. Always true in V2 mode."""
        raise NotImplementedError

    @abstractmethod
    def get_user_home_path(self) -> Path:
        """Return Conan user home path, where e.g. settings reside"""
        raise NotImplementedError

    @abstractmethod
    def get_storage_path(self) -> Path:
        """Return Conan storage path where packages are saved"""
        raise NotImplementedError

    @abstractmethod
    def get_short_path_root(self) -> Path:
        """Return short path root for Windows for Conan V1.
        Sadly there is no built-in way to do so."""
        raise NotImplementedError

    ### Remotes ###

    @abstractmethod
    def get_remotes(self, include_disabled: bool = False) -> List[Remote]:
        """Return a list of all remotes as objects"""
        raise NotImplementedError

    @abstractmethod
    def get_remote_names(self, include_disabled: bool = False) -> List[str]:
        """Return a list of all remote names"""
        raise NotImplementedError

    @abstractmethod
    def get_remote(self, remote_name: str) -> Optional[Remote]:
        """Get info of one remote. Returns None on not existing remote."""
        raise NotImplementedError

    @abstractmethod
    def add_remote(self, remote_name: str, url: str, verify_ssl: bool) -> None:
        """Add a new remote with the selected options. Disabled is always false."""
        raise NotImplementedError

    @abstractmethod
    def rename_remote(self, remote_name: str, new_name: str) -> None:
        """Rename a remote"""
        raise NotImplementedError

    @abstractmethod
    def remove_remote(self, remote_name: str) -> None:
        """Remove a remote"""
        raise NotImplementedError

    @abstractmethod
    def update_remote(
        self,
        remote_name: str,
        url: str,
        verify_ssl: bool,
        index: Optional[int] = None,
    ) -> None:
        """Update a remote with new information and reorder with index.
        The Remote object is immutable, so we have to get every field separatly.
        The name can't be changed with this, only with rename.
        """
        raise NotImplementedError

    @abstractmethod
    def disable_remote(self, remote_name: str, disabled: bool) -> None:
        """
        Setting disabled to true disables the remote, settings to false enables it.
        """
        raise NotImplementedError

    @abstractmethod
    def login_remote(self, remote_name: str, user_name: str, password: str) -> None:
        """Login to a remote with credentials
        This method will throw if wrong credentials are entered,
        so we can catch the first error, when logging into multiple remotes
        and do not retry, possibly locking the user.
        """
        raise NotImplementedError

    @abstractmethod
    def get_remote_user_info(self, remote_name: str) -> Tuple[UserName, IsAuthenticated]:
        """Get username and authenticated info for a remote."""
        raise NotImplementedError

    ### Install related methods ###

    @abstractmethod
    def install_reference(
        self,
        conan_ref: Union[ConanRef, str],
        conan_settings: Optional[ConanSettings] = None,
        conan_options: Optional[ConanOptions] = None,
        profile: str = "",
        update: bool = True,
        generators: Sequence[str] = [],
        remote_name: Optional[str] = None,
    ) -> Tuple[ConanPackageId, ConanPackagePath]:
        """
        Try to install a conan reference (without id) with the provided extra information.
        Uses plain conan install (No auto determination of best matching package)
        Returns the actual pkg_id and the package path.
        """
        raise NotImplementedError

    @abstractmethod
    def install_package(
        self,
        conan_ref: Union[ConanRef, str],
        package: ConanPkg,
        update: bool = True,
        remote_name: Optional[str] = None,
    ) -> Tuple[ConanPackageId, ConanPackagePath]:
        """
        Try to install a conan package (id) with the provided extra information.
        Returns the installed id and a valid pkg path, if installation was succesfull.
        WARNING: The installed id can differ from the requested one,
        because there is no built-in way in conan to install a specific package id!
        """
        raise NotImplementedError

    @abstractmethod
    def get_path_with_auto_install(
        self,
        conan_ref: Union[ConanRef, str],
        conan_options: Optional[ConanOptions] = None,
        update: bool = False,
    ) -> Tuple[ConanPackageId, ConanPackagePath]:
        """Return the pkg_id and package folder of a conan reference
        and auto-install it with the best matching package, if it is not available"""
        raise NotImplementedError

    @abstractmethod
    def install_best_matching_package(
        self,
        conan_ref: Union[ConanRef, str],
        conan_options: Optional[ConanOptions] = None,
        update: bool = False,
    ) -> Tuple[ConanPackageId, ConanPackagePath]:
        raise NotImplementedError

    @abstractmethod
    def get_options_with_default_values(
        self,
        conan_ref: Union[ConanRef, str],
        remote_name: Optional[str] = None,
    ) -> Tuple[ConanAvailableOptions, ConanOptions]:
        """Return the available options and their default values as dict."""
        raise NotImplementedError

    ### Local References and Packages ###

    @abstractmethod
    def get_export_folder(self, conan_ref: Union[ConanRef, str]) -> Path:
        """Get the export folder form a reference"""
        raise NotImplementedError

    @abstractmethod
    def get_conanfile_path(self, conan_ref: Union[ConanRef, str]) -> Path:
        """Get local conanfile path. If it is not localy available, download it."""
        raise NotImplementedError

    @abstractmethod
    def get_package_folder(
        self,
        conan_ref: Union[ConanRef, str],
        package_id: str,
    ) -> ConanPackagePath:
        "Get the fully resolved pkg path from the ref and the specific package (id)"
        raise NotImplementedError

    @abstractmethod
    def get_conan_buildinfo(
        self,
        conan_ref: Union[ConanRef, str],
        conan_settings: ConanSettings,
        conan_options: Optional[ConanOptions] = None,
    ) -> str:
        """Read conan buildinfo and return as string
        NOTE: Currently not implemented for Conan 2
        """
        raise NotImplementedError

    @abstractmethod
    def remove_reference(
        self,
        conan_ref: Union[ConanRef, str],
        pkg_id: str = "",
    ) -> None:
        """Remove a conan reference and it's package if specified via id"""
        raise NotImplementedError

    @abstractmethod
    def find_best_matching_local_package(
        self,
        conan_ref: Union[ConanRef, str],
        conan_options: Optional[ConanOptions] = None,
    ) -> ConanPkg:
        """Find a package in the local cache"""
        raise NotImplementedError

    @abstractmethod
    def get_best_matching_local_package_path(
        self,
        conan_ref: Union[ConanRef, str],
        conan_options: Optional[ConanOptions] = None,
    ) -> Tuple[ConanPackageId, ConanPackagePath]:
        """Return the pkg_id and pkg folder of a conan reference, if it is installed."""
        raise NotImplementedError

    @abstractmethod
    def get_all_local_refs(self) -> List[ConanRef]:
        """Returns all locally installed conan references"""
        raise NotImplementedError

    @abstractmethod
    def get_local_pkgs_from_ref(self, conan_ref: Union[ConanRef, str]) -> List[ConanPkg]:
        """Returns all installed pkg ids for a reference."""
        raise NotImplementedError

    @abstractmethod
    def get_local_pkg_from_id(self, pkg_ref: ConanPkgRef) -> ConanPkg:
        """Returns an installed pkg from reference and id"""
        raise NotImplementedError

    @abstractmethod
    def get_local_pkg_from_path(
        self,
        conan_ref: Union[ConanRef, str],
        path: Path,
    ) -> Optional[ConanPkg]:
        """For reverse lookup - give info from path"""
        raise NotImplementedError

    ### Editables ###

    @abstractmethod
    def get_editable(self, conan_ref: Union[ConanRef, str]) -> Optional[EditablePkg]:
        """Get an editable object from conan reference.
        Returns None if editable does not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def get_editables_package_path(self, conan_ref: Union[ConanRef, str]) -> Path:
        """Get package path of an editable reference."""
        raise NotImplementedError

    @abstractmethod
    def get_editables_output_folder(self, conan_ref: Union[ConanRef, str]) -> Optional[Path]:
        """Get output folder of an editable reference."""
        raise NotImplementedError

    @abstractmethod
    def get_editable_references(self) -> List[ConanRef]:
        """Get all local editable references."""
        raise NotImplementedError

    @abstractmethod
    def add_editable(
        self,
        conan_ref: Union[ConanRef, str],
        path: Union[Path, str],
        output_folder: Union[Path, str],
    ) -> bool:
        """Add an editable reference."""
        raise NotImplementedError

    @abstractmethod
    def remove_editable(self, conan_ref: Union[ConanRef, str]) -> bool:
        """Remove an editable reference."""
        raise NotImplementedError

    ### Remote References and Packages ###

    @abstractmethod
    def search_recipes_in_remotes(self, query: str, remote_name: str = "all") -> List[ConanRef]:
        """Search in all remotes for a specific query.
        Returns a list of unique and ordered ConanRefs.
        Limitation: Can't handle long canonical refs like mylib/1.0.0@_/_.
        Must use mylib/1.0.0.
        """
        raise NotImplementedError

    @abstractmethod
    def search_recipe_all_versions_in_remotes(
        self,
        conan_ref: Union[ConanRef, str],
    ) -> List[ConanRef]:
        """Search in all remotes for all versions of a conan ref"""
        raise NotImplementedError

    @abstractmethod
    def get_remote_pkgs_from_ref(
        self,
        conan_ref: Union[ConanRef, str],
        remote_name: Optional[str],
        query: Optional[str] = None,
    ) -> List[ConanPkg]:
        """
        Return all packages for a reference in a specific remote with an optional query.
        Can not raise an exception. Returns an empty list if something errors.
        """
        raise NotImplementedError

    @abstractmethod
    def get_remote_pkg_from_id(self, pkg_ref: ConanPkgRef) -> ConanPkg:
        """Returns a remote pkg from reference and id"""
        raise NotImplementedError

    @abstractmethod
    def find_best_matching_package_in_remotes(
        self,
        conan_ref: Union[ConanRef, str],
        conan_options: Optional[ConanOptions] = None,
    ) -> Tuple[List[ConanPkg], RemoteName]:
        """Find a package with options in the remotes"""
        raise NotImplementedError

    @abstractmethod
    def find_best_matching_packages(
        self,
        conan_ref: Union[ConanRef, str],
        conan_options: Optional[ConanOptions] = None,
        remote_name: Optional[str] = None,
    ) -> List[ConanPkg]:
        """
        Tries to find the best matching packages either locally or in a remote,
        based on the users machine and the supplied options.
        """
        raise NotImplementedError
