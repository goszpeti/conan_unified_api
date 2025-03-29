import logging
import os
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union
from unittest.mock import patch

from typing_extensions import Self

from .base import INVALID_PATH_VALUE, Version, conan_version
from .base.helper import create_key_value_pair_list
from .base.logger import Logger
from .base.typing import SignatureCheckMeta
from .common import ConanUnifiedApi
from .types import (
    ConanAvailableOptions,
    ConanException,
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

current_path = Path(__file__).parent

if TYPE_CHECKING:
    from conan.api.conan_api import ConanAPI  # type: ignore
    from conan.internal.cache.cache import PkgCache as ClientCache
    from conan.internal.cache.home_paths import HomePaths  # type: ignore

    from .cache.conan_cache import ConanInfoCache

# FIXME: Many commands spam the log...


class ConanApi(ConanUnifiedApi, metaclass=SignatureCheckMeta):
    """Wrapper around ConanAPIV2"""

    def __init__(
        self,
        init: bool = True,
        logger: Optional[logging.Logger] = None,
        mute_logging: bool = False,
    ):
        self.info_cache: "ConanInfoCache"
        self._conan: "ConanAPI"
        self._client_cache: "ClientCache"
        self._short_path_root = Path("Unknown")
        self._home_paths: "HomePaths"
        super().__init__(init, logger, mute_logging)

    def init_api(self) -> Self:
        from conan.api.conan_api import ConanAPI

        devnull = open(os.devnull, "w")
        with redirect_stdout(devnull), redirect_stderr(devnull):
            self._conan = ConanAPI()
            self._init_client_cache()

        from .cache.conan_cache import ConanInfoCache

        self.info_cache = ConanInfoCache(current_path, self.get_all_local_refs())
        self.logger.debug("Initialized Conan V2 API wrapper")
        return self

    def _init_client_cache(self) -> None:
        if conan_version < Version("2.4.0"):
            from conans.client.cache.cache import ClientCache
        else:
            from conan.internal.cache.cache import PkgCache as ClientCache
        self._client_cache = ClientCache(
            self._conan.cache_folder, self._conan.config.global_conf
        )
        from conan.internal.cache.home_paths import HomePaths

        self._home_paths = HomePaths(self._conan.cache_folder)

    ### General commands ###

    def info(self, conan_ref: Union[ConanRef, str]) -> List[Dict[str, Any]]:
        # TODO: try to merge with install reference code
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        remotes = self._conan.remotes.list(None)
        profiles = []
        profile_host = self._conan.profiles.get_profile(profiles, settings=[], options=[])
        requires = [conan_ref]
        update = "*" if conan_version < Version("2.2") else False

        deps_graph = self._conan.graph.load_graph_requires(
            requires, None, profile_host, profile_host, None, remotes, update
        )
        # this modifies deps_graph
        self._conan.graph.analyze_binaries(
            deps_graph, build_mode=None, remotes=remotes, update=update, lockfile=None
        )

        # prepare output and convert to dict
        nodes = deps_graph.nodes
        nodes.pop(0)  # remove cli node
        results = []
        for node in nodes:
            result_dict = {}
            for attr in dir(node):
                if attr.startswith("_"):  # only public fields
                    continue
                try:
                    result_dict[attr] = getattr(node, attr)
                except Exception:
                    continue
            results.append(result_dict)
        return results

    def inspect(
        self,
        conan_ref: Union[ConanRef, str],
        attributes: Sequence[str] = [],
        remote_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)

        remotes = self.get_remotes()
        if remote_name:
            remotes = [self.get_remote(remote_name)]

        path = self.get_conanfile_path(conan_ref)
        if conan_version < Version("2.4"):
            conanfile = self._conan.local.inspect(str(path), remotes=remotes, lockfile=None)
        else:
            conanfile = self._conan.local.inspect(
                str(path),
                remotes=remotes,
                lockfile=None,
                name=conan_ref.name,
                version=conan_ref.version,
                user=conan_ref.user,
                channel=conan_ref.channel,
            )
        result = {}
        for attr in dir(conanfile):
            if attr.startswith("_"):  # only public fields
                continue
            if attributes:
                if attr not in attributes:
                    continue
            try:
                result[attr] = getattr(conanfile, attr)
            except Exception:
                continue
        # no serialization, like in ConanV1
        return result

    # def alias(self, conan_ref: Union[ConanRef, str], conan_target_ref: Union[ConanRef, str]):
    #     # TODO does not seem to copy the package yet
    #     conan_ref = self.conan_ref_from_reflike(conan_ref)
    #     conan_target_ref = self.conan_ref_from_reflike(conan_target_ref)

    #     template = self._conan.new.get_builtin_template("alias")
    #     content = self._conan.new.render(template, {
    #         "name": conan_ref.name,
    #         "version": conan_ref.version,
    #         "target": conan_target_ref.version})
    #     conanfile_path = Path(mkdtemp()) / "conanfile_temp.py"
    #     conanfile_path.write_text(content.get("conanfile.py", ""))
    #     self._conan.export.export(str(conanfile_path), conan_ref.name,
    #                               conan_ref.version, conan_ref.user, conan_ref.channel)

    def remove_locks(self) -> None:
        pass  # command does not exist

    def get_profiles(self) -> List[str]:
        return self._conan.profiles.list()

    def get_profile_settings(self, profile_name: str) -> ConanSettings:
        if conan_version < Version("2.6.0"):
            from conans.client.profile_loader import ProfileLoader
        else:
            from conan.internal.api.profile.profile_loader import ProfileLoader

        try:
            profile = ProfileLoader(self._conan.cache_folder).load_profile(profile_name)
            return profile.settings
        except Exception as e:
            raise ConanException(f"Can't get profile {profile_name} settings: {str(e)}")

    def get_package_folder(self, conan_ref: Union[ConanRef, str], package_id: str) -> Path:
        if not package_id:  # will give the base path ortherwise
            return Path(INVALID_PATH_VALUE)
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        try:
            latest_rev_ref = self._conan.list.latest_recipe_revision(conan_ref)
            latest_rev_pkg = self._conan.list.latest_package_revision(
                ConanPkgRef(latest_rev_ref, package_id)
            )
            layout = self._client_cache.pkg_layout(latest_rev_pkg)
            return Path(layout.package())
        except Exception:  # gotta catch 'em all!
            return Path(INVALID_PATH_VALUE)

    def get_export_folder(self, conan_ref: Union[ConanRef, str]) -> Path:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        return Path(self._conan.cache.export_path(conan_ref))

    def get_conanfile_path(self, conan_ref: Union[ConanRef, str]) -> Path:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        try:
            if conan_ref not in self.get_all_local_refs():
                for remote in self.get_remotes():
                    result = None
                    try:
                        result = self.search_recipes_in_remotes(
                            str(conan_ref), remote_name=remote.name
                        )
                    except Exception:
                        continue  # next
                    if result:
                        latest_rev: ConanRef = self._conan.list.latest_recipe_revision(
                            conan_ref, remote
                        )
                        self._conan.download.recipe(latest_rev, remote)  # type: ignore
                        break
            path = self._conan.local.get_conanfile_path(
                self._conan.cache.export_path(conan_ref), os.getcwd(), py=True
            )
            if not path:
                return Path(INVALID_PATH_VALUE)
            return Path(path)
        except Exception as e:
            Logger().error(f"Can't get conanfile: {str(e)}")
        return Path(INVALID_PATH_VALUE)

    def get_default_settings(self) -> ConanSettings:
        if conan_version < Version("2.6.0"):
            from conans.client.profile_loader import ProfileLoader
        else:
            from conan.internal.api.profile.profile_loader import ProfileLoader

        profile = ProfileLoader(self._conan.cache_folder).load_profile(
            Path(self._conan.profiles.get_default_host()).name
        )

        return dict(profile.settings)

    # user_name, authenticated
    def get_remote_user_info(self, remote_name: str) -> Tuple[str, bool]:
        try:
            info = self._conan.remotes.user_info(self._conan.remotes.get(remote_name))
        except Exception as e:
            raise ConanException(f"Can't get remote {remote_name} user info: {str(e)}")
        return str(info.get("user_name", "")), info.get("authenticated", False)

    def get_config_file_path(self) -> Path:
        return Path(self._home_paths.global_conf_path)

    def get_config_entry(self, config_name: str) -> Optional[Any]:
        return self._conan.config.get(config_name, None)

    def get_revisions_enabled(self) -> bool:
        return True  # always on in 2

    def get_settings_file_path(self) -> Path:
        return Path(self._home_paths.settings_path)

    def get_profiles_path(self) -> Path:
        return Path(self._home_paths.profiles_path)

    def get_user_home_path(self) -> Path:
        return Path(self._conan.cache_folder)

    def get_storage_path(self) -> Path:
        return Path(str(self._client_cache.store))

    def get_short_path_root(self) -> Path:
        # there is no short_paths feature in conan 2
        return Path(INVALID_PATH_VALUE)

    # Remotes

    def get_remotes(self, include_disabled=False) -> List[Remote]:
        remotes = []
        try:
            remotes = self._conan.remotes.list(None, only_enabled=not include_disabled)
        except Exception as e:
            raise ConanException(f"Error while reading remotes: {str(e)}")
        return remotes  # type: ignore

    def add_remote(self, remote_name: str, url: str, verify_ssl: bool) -> None:
        if conan_version < Version("2.1"):
            from conans.client.cache.remote_registry import Remote as ConanRemote
        else:
            from conan.api.model import Remote as ConanRemote
        remote = ConanRemote(remote_name, url, verify_ssl, False)
        self._conan.remotes.add(remote)

    def rename_remote(self, remote_name: str, new_name: str) -> None:
        self._conan.remotes.rename(remote_name, new_name)

    def remove_remote(self, remote_name: str) -> None:
        self._conan.remotes.remove(remote_name)

    def disable_remote(self, remote_name: str, disabled: bool) -> None:
        if disabled:
            self._conan.remotes.disable(remote_name)
        else:
            self._conan.remotes.enable(remote_name)

    def update_remote(
        self, remote_name: str, url: str, verify_ssl: bool, index: Optional[int] = None
    ) -> None:
        self._conan.remotes.update(
            remote_name,
            url,
            verify_ssl,
            self._conan.remotes.get(remote_name).disabled,
            index,
        )

    def login_remote(self, remote_name: str, user_name: str, password: str) -> None:
        if conan_version < Version("2.1"):
            self._conan.remotes.login(self._conan.remotes.get(remote_name), user_name, password)
        else:
            self._conan.remotes.user_login(
                self._conan.remotes.get(remote_name), user_name, password
            )

    ### Install related methods ###
    def install_reference(
        self,
        conan_ref: Union[ConanRef, str],
        conan_settings: Optional[ConanSettings] = None,
        conan_options: Optional[ConanOptions] = None,
        profile: str = "",
        update: bool = True,
        generators: List[str] = [],
        remote_name: Optional[str] = None,
    ) -> Tuple[ConanPackageId, ConanPackagePath]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        pkg_id = ""
        if conan_options is None:
            conan_options = {}
        if conan_settings is None:
            conan_settings = {}
        options_list = create_key_value_pair_list(conan_options)
        settings_list = create_key_value_pair_list(conan_settings)
        install_message = (
            f"Installing '{str(conan_ref)}' with profile: {profile}, "
            f"settings: {str(settings_list)}, "
            f"options: {str(options_list)} and update={update}\n"
        )
        Logger().info(install_message)
        from conan.cli.printers.graph import print_graph_basic, print_graph_packages

        try:
            # Basic collaborators, remotes, lockfile, profiles
            remotes = self._conan.remotes.list(None)
            if remote_name:
                remotes = [self.get_remote(remote_name)]
            profiles = [profile] if profile else []
            profile_host = self._conan.profiles.get_profile(
                profiles, settings=settings_list, options=options_list
            )
            requires = [conan_ref]
            if conan_version > Version("2.0"):
                update = "*" if update else ""
            deps_graph = self._conan.graph.load_graph_requires(
                requires, None, profile_host, profile_host, None, remotes, update
            )
            print_graph_basic(deps_graph)
            deps_graph.report_graph_error()
            self._conan.graph.analyze_binaries(
                deps_graph,
                build_mode=None,
                remotes=remotes,
                update=update,
                lockfile=None,
            )
            print_graph_packages(deps_graph)

            # Try to redirect custom streams in conanfile, to avoid missing flush method
            devnull = open(os.devnull, "w")
            # also spoof os.terminal_size(
            spoof_size = os.terminal_size([80, 20])
            patched_tersize = patch("os.get_terminal_size")
            with redirect_stdout(devnull), redirect_stderr(devnull):
                mock = patched_tersize.start()
                mock.return_value = spoof_size

                self._conan.install.install_binaries(deps_graph=deps_graph, remotes=remotes)
                # Currently unused
                self._conan.install.install_consumer(
                    deps_graph=deps_graph,
                    generators=generators,
                    output_folder=None,
                    source_folder=gettempdir(),
                )

                patched_tersize.stop()

            info = None
            for node in deps_graph.nodes:
                if node.ref == conan_ref:
                    info = node
                    break
            if info is None:
                raise ConanException("Can't read information of installed recipe from graph.")
            pkg_id = info.package_id
            Logger().info(f"Installation of '{str(conan_ref)}' finished")
            return (pkg_id, self.get_package_folder(conan_ref, pkg_id))
        except ConanException as error:
            raise ConanException(f"Can't install reference '{str(conan_ref)}': {str(error)}")

    def get_options_with_default_values(
        self, conan_ref: Union[ConanRef, str], remote_name: Optional[str] = None
    ) -> Tuple[ConanAvailableOptions, ConanOptions]:
        # this calls external code of the recipe
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        default_options: ConanOptions = {}
        available_options: ConanAvailableOptions = {}
        try:
            self.inspect(conan_ref, remote_name=remote_name)
            path = self.get_conanfile_path(conan_ref)
            from conan.internal.conan_app import ConanApp

            if conan_version < Version("2.1"):
                app = ConanApp(self._conan.cache_folder, self._conan.config.global_conf)
            else:
                app = ConanApp(self._conan)
            conanfile = app.loader.load_conanfile(path, conan_ref)
            default_options = {}
            if conanfile.default_options is not None:
                default_options = conanfile.default_options
            default_options = self._resolve_default_options(default_options)
            available_options = conanfile.options.possible_values
        except Exception as e:  # silent error - if we have no options don't spam the user
            Logger().debug(
                f"Error while getting default options for {str(conan_ref)}: {str(e)}"
            )
        return available_options, default_options

    ### Local References and Packages ###

    def get_conan_buildinfo(
        self,
        conan_ref: Union[ConanRef, str],
        conan_settings: ConanSettings,
        conan_options: Optional[ConanOptions] = None,
    ) -> str:
        """TODO: Currently there is no equivalent to txt generator from ConanV1"""
        raise NotImplementedError

    def get_editable(self, conan_ref: Union[ConanRef, str]) -> Optional[EditablePkg]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        self.__reload_conan_api()
        editables_dict = self._conan.local.editable_list()
        editable_dict = editables_dict.get(conan_ref, {})
        if not editable_dict:
            return None
        return EditablePkg(
            str(conan_ref),
            editable_dict.get("path", INVALID_PATH_VALUE),
            editable_dict.get("output_folder"),
        )

    def get_editables_package_path(self, conan_ref: Union[ConanRef, str]) -> Path:
        """Get package path of an editable reference. Can be a folder or conanfile.py"""
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        self.__reload_conan_api()
        editables_dict = self._conan.local.editable_list()
        return Path(editables_dict.get(conan_ref, {}).get("path", INVALID_PATH_VALUE))

    def get_editables_output_folder(self, conan_ref: Union[ConanRef, str]) -> Optional[Path]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        self.__reload_conan_api()
        editables_dict = self._conan.local.editable_list()
        output_folder = editables_dict.get(conan_ref, {}).get("output_folder")
        if not output_folder:
            return None
        return Path(str(output_folder))

    def get_editable_references(self) -> List[ConanRef]:
        """Get all local editable references."""
        self.__reload_conan_api()
        editables_dict = self._conan.local.editable_list()
        return list(editables_dict.keys())

    def __reload_conan_api(self) -> None:
        from conan.api.conan_api import ConanAPI

        self._conan = ConanAPI()  # reload editables only possible like this

    def add_editable(
        self,
        conan_ref: Union[ConanRef, str],
        path: Union[Path, str],
        output_folder: Union[Path, str],
    ) -> bool:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        try:
            self._conan.local.editable_add(
                str(path),
                conan_ref.name,
                conan_ref.version,
                conan_ref.user,
                conan_ref.channel,
                output_folder=str(output_folder),
            )
        except Exception as e:
            raise ConanException("Error adding editable: " + str(e))
        return True

    def remove_editable(self, conan_ref: Union[ConanRef, str]) -> bool:
        try:
            if isinstance(conan_ref, str):
                conan_ref = ConanRef.loads(conan_ref)
            self._conan.local.editable_remove(None, [str(conan_ref)])
        except Exception as e:
            raise ConanException("Error removing editable: " + str(e))
        return True

    def remove_reference(self, conan_ref: Union[ConanRef, str], pkg_id: str = "") -> None:
        if pkg_id:
            conan_pkg_ref = ConanPkgRef.loads(str(conan_ref) + ":" + pkg_id)
            latest_rev = self._conan.list.latest_package_revision(conan_pkg_ref)
            self._conan.remove.package(latest_rev, remote=None)  # type: ignore
        else:
            conan_ref = self.conan_ref_from_reflike(conan_ref)
            latest_rev = self._conan.list.latest_recipe_revision(conan_ref)
            self._conan.remove.recipe(latest_rev, remote=None)  # type: ignore

    def get_all_local_refs(self) -> List[ConanRef]:
        if conan_version < Version("2.6"):
            return self._client_cache.all_refs()
        return self._client_cache._db.list_references()

    def get_local_pkgs_from_ref(self, conan_ref: Union[ConanRef, str]) -> List[ConanPkg]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        result: List[ConanPkg] = []

        if conan_ref.user == "_":
            conan_ref.user = None
        if conan_ref.channel == "_":
            conan_ref.channel = None
        if not conan_ref.revision:
            try:
                conan_ref_latest: ConanRef = self._conan.list.latest_recipe_revision(conan_ref)
            except Exception as e:
                Logger().error(
                    f"Error while getting latest recipe for {str(conan_ref)}: {str(e)}"
                )
                return result
            if not conan_ref_latest:
                return result
        else:
            conan_ref_latest = conan_ref
        try:  # errors with invalid pkg
            refs = self._conan.list.packages_configurations(conan_ref_latest)
        except Exception as e:
            Logger().error(
                f"Error while getting packages for recipe {str(conan_ref)}: {str(e)}"
            )
            return result
        for ref, pkg_info in refs.items():
            pkg = ConanPkg()
            pkg["id"] = str(ref.package_id)
            pkg["options"] = pkg_info.get("options", {})
            pkg["settings"] = pkg_info.get("settings", {})
            pkg["requires"] = []
            pkg["outdated"] = False
            result.append(pkg)
        return result

    ### Remote References and Packages ###

    def search_recipes_in_remotes(self, query: str, remote_name: str = "all") -> List[ConanRef]:
        search_results = []
        remotes = []
        if remote_name == "all":
            remotes = self.get_remotes()
        else:
            remotes = [self.get_remote(remote_name)]
            if not remotes:
                raise ConanException(
                    f"Error while searching for recipe: remote {remote_name} does not exist"
                )
        for remote in remotes:
            try:
                # no query possible with pattern
                search_results: List["ConanRef"] = self._conan.search.recipes(
                    query, remote=remote
                )
            except Exception as e:
                raise ConanException(f"Error while searching for recipe: {str(e)}")

        search_results = list(set(search_results))  # make unique
        search_results.sort()
        return search_results

    def search_recipe_all_versions_in_remotes(
        self, conan_ref: Union[ConanRef, str]
    ) -> List[ConanRef]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        search_results = []
        search_results: List = self.search_recipes_in_remotes(
            f"{conan_ref.name}/*", remote_name="all"
        )

        self.info_cache.update_remote_package_list(search_results)
        return search_results

    def get_remote_pkgs_from_ref(
        self,
        conan_ref: Union[ConanRef, str],
        remote_name: Optional[str],
        query: Optional[str] = None,
    ) -> List[ConanPkg]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)

        found_pkgs: List[ConanPkg] = []
        try:
            from conan.api.model import ListPattern

            pattern = ListPattern(str(conan_ref) + ":*", rrev="", prev="")
            search_results = None
            remote_obj = None
            if remote_name:
                for remote_obj in self.get_remotes():
                    if remote_obj.name == remote_name:
                        break
            search_results = self._conan.list.select(
                pattern, remote=remote_obj, package_query=query
            )
            if search_results:
                latest_rev = self._conan.list.latest_recipe_revision(conan_ref, remote_obj)
                if latest_rev:
                    found_pkgs_dict = (
                        search_results.recipes.get(str(conan_ref), {})
                        .get("revisions", {})
                        .get(latest_rev.revision, {})
                        .get("packages", {})
                    )
                    for id, info in found_pkgs_dict.items():
                        found_pkgs.append(
                            ConanPkg(
                                id=id,
                                options=info.get("info", {}).get("options", {}),
                                settings=info.get("info", {}).get("settings", {}),
                                requires=[],
                                outdated=False,
                            )
                        )
            Logger().debug(str(found_pkgs))
        except ConanException as e:
            error_message = f"Can not get Conan packages for reference {conan_ref}: {e!s}"
            Logger().error(str(error_message))
        return found_pkgs
