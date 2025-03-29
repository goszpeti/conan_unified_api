import logging
import os
import platform
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union
from unittest.mock import patch

from typing_extensions import Self

from conan_unified_api.base.helper import create_key_value_pair_list, delete_path, save_sys_path
from conan_unified_api.base.typing import SignatureCheckMeta

try:
    from contextlib import chdir
except ImportError:
    from contextlib_chdir import chdir  # type: ignore

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
    LoggerWriter,
    Remote,
)

if TYPE_CHECKING:
    from conans.client.conan_api import ClientCache, ConanAPIV1

    from .cache.conan_cache import ConanInfoCache

from conan_unified_api.base import CONAN_LOG_PREFIX, INVALID_PATH_VALUE, invalid_path

current_path = Path(__file__).parent


class ConanApi(ConanUnifiedApi, metaclass=SignatureCheckMeta):
    """Wrapper around ConanAPIV1"""

    def __init__(
        self,
        init: bool = True,
        logger: Optional[logging.Logger] = None,
        mute_logging: bool = False,
    ):
        self._conan: ConanAPIV1
        self._client_cache: ClientCache
        self._short_path_root = Path("Unknown")
        self.info_cache: ConanInfoCache
        super().__init__(init, logger, mute_logging)

    def init_api(self) -> Self:
        """Instantiate the internal Conan api."""
        from conans.client.conan_api import ConanAPIV1, ConanApp, UserIO
        from conans.client.output import ConanOutput

        self._fix_editable_file()

        self._conan = ConanAPIV1(
            output=ConanOutput(
                LoggerWriter(self.logger.info, CONAN_LOG_PREFIX),
                LoggerWriter(self.logger.error, CONAN_LOG_PREFIX),
            )
        )
        self._conan.user_io = UserIO(
            out=ConanOutput(
                LoggerWriter(self.logger.info, CONAN_LOG_PREFIX),
                LoggerWriter(self.logger.error, CONAN_LOG_PREFIX),
            )
        )
        self._conan.create_app()
        self._conan.user_io.disable_input()  # error on inputs - nowhere to enter
        if self._conan.app:
            self._client_cache = self._conan.app.cache
        else:
            raise NotImplementedError

        def create_app(self, quiet_output=None, force: bool = False):
            if self.app and not force:
                return self.app
            self.app = ConanApp(  # noqa: RET503
                self.cache_folder,
                self.user_io,
                self.http_requester,
                self.runner,
                quiet_output=quiet_output,
            )

        patch("conans.client.conan_api.ConanAPIV1.create_app", create_app).start()

        # don't hang on startup
        try:  # use try-except because of Conan 1.24 envvar errors in tests
            self.remove_locks()
        except Exception as e:
            self.logger.debug(str(e), exc_info=True)
        from .cache.conan_cache import ConanInfoCache

        self.info_cache = ConanInfoCache(current_path, self.get_all_local_refs())
        self.logger.debug("Initialized Conan V1 API wrapper")

        return self

    def _fix_editable_file(self) -> None:
        """Ensure editables json is valid (Workaround for empty json bug)
        Must work without using ConanAPIV1, because it can't be called without this
        """
        from conans.client.cache.editable import EDITABLE_PACKAGES_FILE
        from conans.paths import get_conan_user_home  # use internal fnc

        try:
            editable_file_path = Path(get_conan_user_home()) / ".conan" / EDITABLE_PACKAGES_FILE
            if not editable_file_path.exists():
                editable_file_path.write_text("{}")
            content = editable_file_path.read_text()
            if not content:
                editable_file_path.write_text("{}")
        except Exception:
            self.logger.debug("Reinit editable file package")

    ### General commands ###

    def remove_locks(self) -> None:
        self._conan.remove_locks()
        self.logger.debug("Removed Conan cache locks.")

    def info(self, conan_ref: Union[ConanRef, str]) -> List[Dict[str, Any]]:
        with save_sys_path():  # can change path or run arbitrary code and thus break things
            canonical_ref = self.generate_canonical_ref(conan_ref)
            deps_graph = self._conan.info(canonical_ref)
            # ugly hack, but sadly no other way to do this
            from conans.client.command import CommandOutputer

            infos: List[Dict[str, Any]] = CommandOutputer(
                self._conan.out, self._client_cache
            )._grab_info_data(deps_graph[0], grab_paths=True)
            # insert original ref as 0th element
            own_info = {}
            for info in infos:
                if canonical_ref == self.generate_canonical_ref(
                    ConanRef.loads(info.get("reference", ""))
                ):
                    own_info = info
                    break
            if not own_info:
                raise ConanException("Can't find own reference in info list!")
            infos.remove(own_info)
            infos.insert(0, own_info)
            return infos

    def inspect(
        self,
        conan_ref: Union[ConanRef, str],
        attributes: Sequence[str] = [],
        remote_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        with save_sys_path():  # can change path or run arbitrary code and thus break things
            # cast from ordered dict
            return dict(
                self._conan.inspect(
                    str(conan_ref), attributes=attributes, remote_name=remote_name
                )
            )

    def alias(
        self, conan_ref: Union[ConanRef, str], conan_target_ref: Union[ConanRef, str]
    ) -> None:
        self._conan.export_alias(str(conan_ref), conan_target_ref)

    def get_profiles(self) -> List[str]:
        return self._conan.profile_list()

    def get_profile_settings(self, profile_name: str) -> ConanSettings:
        profile = self._conan.read_profile(profile_name)
        if not profile:
            return {}
        return dict(profile.settings)

    def get_default_settings(self) -> ConanSettings:
        default_profile = self._client_cache.default_profile
        if not default_profile:
            return {}
        return dict(default_profile.settings)

    # user_name, authenticated
    def get_remote_user_info(self, remote_name: str) -> Tuple[str, bool]:
        user_info = self._conan.users_list(remote_name).get("remotes", {})
        if len(user_info) < 1:
            return ("", False)
        try:
            return (
                str(user_info[0].get("user_name", "")),
                user_info[0].get("authenticated", False),
            )
        except Exception:
            self.logger.warning("Can't get user info for %s", remote_name)
            return ("", False)

    def get_config_file_path(self) -> Path:
        return Path(self._client_cache.conan_conf_path)

    def get_config_entry(self, config_name: str) -> Optional[Any]:
        """Will always return str, but 2 will return correct type TODO: implement this?"""
        try:
            self._conan.out._stream.disabled = True  # type: ignore
            config_value = self._conan.config_get(config_name)  # mute this output
            self._conan.out._stream.disabled = False  # type: ignore
            return config_value
        except Exception:
            try:
                config_entry_suffix = config_name.split(".")[1]
                config_value = self._client_cache.config.env_vars.get(
                    "CONAN_" + config_entry_suffix.upper(), None
                )
                return config_value
            except Exception:
                return None

    def get_revisions_enabled(self) -> bool:
        return self._client_cache.config.revisions_enabled

    def get_settings_file_path(self) -> Path:
        return Path(self._client_cache.settings_path)

    def get_profiles_path(self) -> Path:
        return Path(str(self._client_cache.default_profile_path)).parent

    def get_user_home_path(self) -> Path:
        return Path(self._client_cache.cache_folder)

    def get_storage_path(self) -> Path:
        return Path(str(self._client_cache.store))

    def get_editable_references(self) -> List[ConanRef]:
        try:
            self._conan.create_app(force=True)  # type: ignore # need to possibly reload editables
            return list(map(ConanRef.loads, self._conan.editable_list().keys()))
        except Exception:
            self._fix_editable_file()  # to not crash conan without this
            return []

    def get_editable(self, conan_ref: Union[ConanRef, str]) -> Optional[EditablePkg]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        self._conan.create_app(force=True)  # type: ignore # need to possibly reload editables

        editable_dict = self._conan.editable_list().get(str(conan_ref), {})
        if not editable_dict:
            return None
        return EditablePkg(
            str(conan_ref),
            editable_dict.get("path", INVALID_PATH_VALUE),
            editable_dict.get("output_folder"),
        )

    def get_editables_package_path(self, conan_ref: Union[ConanRef, str]) -> Path:
        self._conan.create_app(force=True)  # type: ignore # need to possibly reload editables
        editable_dict = self._conan.editable_list().get(str(conan_ref), {})
        return Path(str(editable_dict.get("path", INVALID_PATH_VALUE)))

    def get_editables_output_folder(self, conan_ref: Union[ConanRef, str]) -> Optional[Path]:
        self._conan.create_app(force=True)  # type: ignore # need to possibly reload editables
        editable_dict = self._conan.editable_list().get(str(conan_ref), {})
        output_folder = editable_dict.get("output_folder")
        if not output_folder:
            return None
        return Path(str(output_folder))

    def add_editable(
        self,
        conan_ref: Union[ConanRef, str],
        path: Union[Path, str],
        output_folder: Union[Path, str],
    ) -> bool:
        try:
            self._conan.editable_add(str(path), str(conan_ref), None, str(output_folder), None)
        except Exception as e:
            self.logger.error("Error adding editable: %s", str(e))
            return False
        return True

    def remove_editable(self, conan_ref: Union[ConanRef, str]) -> bool:
        try:
            self._conan.editable_remove(str(conan_ref))
        except Exception as e:
            self.logger.error("Error removing editable: %s", str(e))
            return False
        return True

    def get_short_path_root(self) -> Path:
        # only need to get once
        if self._short_path_root.exists() or platform.system() != "Windows":
            return self._short_path_root
        short_home = self._client_cache.config.short_paths_home
        if not short_home:
            drive = os.path.splitdrive(self._client_cache.cache_folder)[0].upper()
            short_home = os.path.join(drive, os.sep, ".conan")
        else:
            short_home = str(short_home)
        os.makedirs(short_home, exist_ok=True)
        return Path(short_home)

    def get_package_folder(self, conan_ref: Union[ConanRef, str], package_id: str) -> Path:
        if not package_id:  # will give the base path otherwise
            return invalid_path
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        try:
            layout = self._client_cache.package_layout(conan_ref)
            return Path(layout.package(ConanPkgRef(conan_ref, package_id)))
        except Exception:  # gotta catch 'em all!
            return invalid_path

    def get_export_folder(self, conan_ref: Union[ConanRef, str]) -> Path:
        layout = self._client_cache.package_layout(self.conan_ref_from_reflike(conan_ref))
        if layout:
            return Path(layout.export())
        return invalid_path

    def get_conanfile_path(self, conan_ref: Union[ConanRef, str]) -> Path:
        try:
            if conan_ref not in self.get_all_local_refs():
                self.inspect(conan_ref)
            layout = self._client_cache.package_layout(self.conan_ref_from_reflike(conan_ref))
            if layout:
                return Path(layout.conanfile())
        except Exception as e:
            raise ConanException(f"Can't get conanfile: {e!s}")
        return invalid_path

    # Remotes

    def get_remotes(self, include_disabled: bool = False) -> List[Remote]:
        remotes = []
        try:
            if include_disabled:
                remotes = self._conan.remote_list()
            else:
                remotes = self._client_cache.registry.load_remotes().values()
        except Exception as e:
            raise ConanException(f"Error while reading remotes file: {e!s}")
        return remotes  # type: ignore

    def add_remote(self, remote_name: str, url: str, verify_ssl: bool) -> None:
        self._conan.remote_add(remote_name, url, verify_ssl)

    def rename_remote(self, remote_name: str, new_name: str) -> None:
        self._conan.remote_rename(remote_name, new_name)

    def remove_remote(self, remote_name: str) -> None:
        self._conan.remote_remove(remote_name)

    def disable_remote(self, remote_name: str, disabled: bool) -> None:
        self._conan.remote_set_disabled_state(remote_name, disabled)

    def update_remote(
        self, remote_name: str, url: str, verify_ssl: bool, index: Optional[int] = None
    ) -> None:
        self._conan.remote_update(remote_name, url, verify_ssl, index)

    def login_remote(self, remote_name: str, user_name: str, password: str) -> None:
        self._conan.authenticate(user_name, password, remote_name)

    ### Install related methods ###

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
        package_id = ""
        if conan_options is None:
            conan_options = {}
        if conan_settings is None:
            conan_settings = {}
        options_list = create_key_value_pair_list(conan_options)
        settings_list = create_key_value_pair_list(conan_settings)
        install_message = (
            f"Installing '{conan_ref!s}' with profile: {profile}, "
            f"settings: {settings_list!s}, "
            f"options: {options_list!s} and update={update}\n"
        )
        self.logger.info(install_message)
        profile_names = None
        if profile:
            profile_names = [profile]
        try:
            # Try to redirect custom streams in conanfile, to avoid missing flush method
            devnull = open(os.devnull, "w")
            # also spoof os.terminal_size(
            spoof_size = os.terminal_size([80, 20])
            patched_tersize = patch("os.get_terminal_size")
            with redirect_stdout(devnull), redirect_stderr(devnull):
                mock = patched_tersize.start()
                mock.return_value = spoof_size

                infos = self._conan.install_reference(
                    conan_ref,
                    settings=settings_list,
                    options=options_list,
                    update=update,
                    profile_names=profile_names,
                    generators=generators,
                    remote_name=remote_name,
                )

                patched_tersize.stop()
            if not infos.get("error", True):
                package_id = (
                    infos.get("installed", [{}])[0].get("packages", [{}])[0].get("id", "")
                )
            self.logger.info("Installation of '%s' finished", str(conan_ref))
            return package_id, self.get_package_folder(conan_ref, package_id)
        except ConanException as error:
            raise ConanException(f"Can't install reference {conan_ref}': {error!s}")

    def get_conan_buildinfo(
        self,
        conan_ref: Union[ConanRef, str],
        conan_settings: ConanSettings,
        conan_options: Optional[ConanOptions] = None,
    ) -> str:
        # install ref to temp dir and use generator
        temp_path = Path(gettempdir()) / "cal_cuild_info"
        temp_path.mkdir(parents=True, exist_ok=True)
        generated_file = temp_path / "conanbuildinfo.txt"
        # clean up possible last run
        delete_path(generated_file)

        # use cli here, API cannnot do job easily and we wan to parse the file output
        with chdir(temp_path):
            self.install_reference(
                conan_ref,
                conan_settings=conan_settings,
                conan_options=conan_options,
                generators=["txt"],
            )
        content = ""
        try:
            content = generated_file.read_text()
        except Exception as e:
            raise ConanException(f"Can't read conanbuildinfo.txt for '{conan_ref}': {e!s}")
        return content

    def get_options_with_default_values(
        self, conan_ref: Union[ConanRef, str], remote_name: Optional[str] = None
    ) -> Tuple[ConanAvailableOptions, ConanOptions]:
        # this calls external code of the recipe
        default_options = {}
        available_options = {}
        try:
            inspect = self.inspect(
                self.generate_canonical_ref(conan_ref), remote_name=remote_name
            )
            default_options = inspect.get("default_options", {})
            available_options = inspect.get("options", {})
        except Exception as e:
            self.logger.error(
                "Error while getting default options for %s: %s", str(conan_ref), str(e)
            )
        return available_options, default_options

    # Local References and Packages

    def remove_reference(self, conan_ref: Union[ConanRef, str], pkg_id: str = "") -> None:
        pkg_ids = [pkg_id] if pkg_id else None
        self._conan.remove(str(conan_ref), packages=pkg_ids, force=True)

    def get_all_local_refs(self) -> List[ConanRef]:
        return self._client_cache.all_refs()  # type: ignore

    def get_local_pkgs_from_ref(self, conan_ref: Union[ConanRef, str]) -> List[ConanPkg]:
        result: List[ConanPkg] = []
        response = {}
        try:
            response = self._conan.search_packages(self.generate_canonical_ref(conan_ref))
        except Exception as e:
            raise ConanException(f"Error while getting local packages for recipe: {e!s}")
        if not response.get("error", True):
            try:
                result = (
                    response.get("results", [{}])[0].get("items", [{}])[0].get("packages", [{}])
                )
            except Exception:
                raise ConanException(
                    f"Received invalid package response format for {conan_ref!s}"
                )
        return result

    # Remote References and Packages

    def search_recipes_in_remotes(self, query: str, remote_name: str = "all") -> List[ConanRef]:
        result_recipes: List[ConanRef] = []
        remote_results = []
        try:
            # no query possible with pattern
            remote_results = self._conan.search_recipes(
                query, remote_name=remote_name, case_sensitive=False
            ).get("results", None)
        except Exception as e:
            raise ConanException(f"Error while searching for recipe: {e!s}")
        if not remote_results:
            return result_recipes

        for remote_search_res in remote_results:
            result_recipes += [
                ConanRef.loads(item.get("recipe", {}).get("id", ""))
                for item in remote_search_res.get("items", [])
            ]
        result_recipes = list(set(result_recipes))  # make unique
        result_recipes.sort()
        self.info_cache.update_remote_package_list(result_recipes)
        return result_recipes

    def search_recipe_all_versions_in_remotes(
        self, conan_ref: Union[ConanRef, str]
    ) -> List[ConanRef]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)

        remote_results: List[Dict[str, Any]] = []
        local_results: List[Dict[str, Any]] = []
        try:
            # no query possible with pattern
            remote_results = self._conan.search_recipes(
                f"{conan_ref.name}/*@*/*", remote_name="all"
            ).get("results", None)
        except Exception as e:
            self.logger.warning(str(e))
        try:
            local_results = self._conan.search_recipes(
                f"{conan_ref.name}/*@*/*", remote_name=None
            ).get("results", None)
        except Exception as e:
            self.logger.warning(str(e))
            return []

        res_list: List[ConanRef] = []
        for remote_search_res in local_results + remote_results:
            res_list += [
                ConanRef.loads(item.get("recipe", {}).get("id", ""))
                for item in remote_search_res.get("items", [])
            ]
        res_list = list(set(res_list))  # make unique
        res_list.sort()
        # update cache
        self.info_cache.update_remote_package_list(res_list)
        return res_list

    def get_remote_pkgs_from_ref(
        self,
        conan_ref: Union[ConanRef, str],
        remote_name: Optional[str],
        query: Optional[str] = None,
    ) -> List[ConanPkg]:
        conan_ref = self.conan_ref_from_reflike(conan_ref)
        found_pkgs: List[ConanPkg] = []
        try:
            search_results = self._conan.search_packages(
                conan_ref.full_str(), query=query, remote_name=remote_name
            ).get("results", None)
        except Exception as e:
            self.logger.debug(
                "Error while searching for %s in %s: %s", conan_ref, remote_name, str(e)
            )
            return []
        if search_results:
            found_pkgs = search_results[0].get("items")[0].get("packages")

        return found_pkgs
