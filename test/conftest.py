import configparser
import ctypes
from datetime import datetime, timedelta
import os
import platform
import shutil
import sys
import time
from pathlib import Path
from subprocess import CalledProcessError, check_output
from threading import Thread
from typing import Generator

import psutil
import pytest
from conan_unified_api import base_path, ConanInfoCache, ConanApiFactory as ConanApi
from conan_unified_api.base.helper import str2bool
from conan_unified_api.types import ConanRef
from conan_unified_api import conan_version

exe_ext = ".exe" if platform.system() == "Windows" else ""
conan_server_thread = None
# setup conan test server
TEST_REF = "example/9.9.9@local/testing"
TEST_REF_OFFICIAL = "example/1.0.0@_/_"
SKIP_CREATE_CONAN_TEST_DATA = str2bool(os.getenv("SKIP_CREATE_CONAN_TEST_DATA", "False"))
TEST_REMOTE_NAME = "local"
TEST_REMOTE_URL = "http://127.0.0.1:9300/"


def is_ci_job():
    """ Test runs in CI environment """
    if os.getenv("GITHUB_WORKSPACE"):
        return True
    return False

class PathSetup():
    """ Get the important paths form the source repo. """

    def __init__(self):
        self.test_path = Path(os.path.dirname(__file__))
        self.core_path = self.test_path.parent
        self.testdata_path = self.test_path / "testdata"


def check_if_process_running(process_name, kill=False, cmd_narg=1, timeout_s=10) -> bool:
    start_time = datetime.now()
    while datetime.now() - start_time < timedelta(seconds=timeout_s) or timeout_s == 0:
        for process in psutil.process_iter():
            try:
                if process_name.lower() in process.name().lower():
                    if kill:
                        try:
                            # or parent.children() for recursive=False
                            for child in process.children(recursive=True):
                                child.terminate()
                            process.terminate()
                        except:
                            process.kill()
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, IndexError):
                pass
        print(f"Not found process {process_name}, keep looking...")
        if timeout_s == 0:
            return False
        time.sleep(1)
    return False

def conan_install_ref(ref, args="", profile=None):
    paths = PathSetup()
    profiles_path = paths.testdata_path / "conan" / "profile"
    extra_cmd = ""
    if conan_version.major == 2:
        extra_cmd = "--requires"
        if not profile:
            profile = platform.system().lower()
        profile = "windowsV2" if profile == "windows" else "linuxV2"
    if profile:
        args += " -pr " + str(profiles_path / profile)
    assert os.system(f"conan install {extra_cmd} {ref} {args}") == 0

def conan_remove_ref(ref):
    if conan_version.major == 2:
        os.system(f"conan remove {ref} -c")
    else:
        os.system(f"conan remove {ref} -f")

def conan_add_editables(conanfile_path: str, reference: ConanRef): # , path: str
    if conan_version.major == 2:
        os.system(f"conan editable add --version {reference.version} "
                  f"--channel {reference.channel} --user {reference.user}  {conanfile_path}")
    else:
        os.system(f"conan editable add {conanfile_path} {str(reference)}")

def conan_create_and_upload(conanfile: str, ref: str, create_params=""):
    if conan_version.major == 1:
        os.system(f"conan create {conanfile} {ref} {create_params}")
        os.system(f"conan upload {ref} -r {TEST_REMOTE_NAME} --force --all")
    elif conan_version.major == 2:
        ref = ref.replace("@_/_", "") # does not work anymore...
        cfr = ConanRef.loads(ref)
        extra_args = ""
        if cfr.user:
            extra_args = f"--user={cfr.user} "
        if cfr.channel:
            extra_args += f"--channel={cfr.channel} "
        os.system(
            f"conan create {conanfile} --name={cfr.name} --version={cfr.version} {extra_args} {create_params}")
        os.system(f"conan upload {ref} -r {TEST_REMOTE_NAME} --force")


def create_test_ref(ref, paths, create_params=[""], update=False):
    if conan_version.major == 2:
        ref = ref.replace("@_/_", "") # does not work anymore...
    native_ref = str(ConanRef.loads(ref))
    conan = ConanApi()
    conan.init_api()

    pkgs = conan.search_recipes_in_remotes(native_ref)

    if not update:
        for pkg in pkgs:
            if str(pkg) == native_ref:
                return
    conanfile = str(paths.testdata_path / "conan" / "conanfile.py")
    if conan_version.major == 2:
        conanfile = str(paths.testdata_path / "conan" / "conanfileV2.py")

    for param in create_params:
        conan_create_and_upload(conanfile, ref, param)

def add_remote(remote_name, url):
    if conan_version.major == 1:
        os.system(f"conan remote add {remote_name} {url} false")
    elif conan_version.major == 2:
        os.system(f"conan remote add {remote_name} {url} --insecure")

def remove_remote(remote_name):
    os.system(f"conan remote remove {remote_name}")

def login_test_remote(remote_name):
    if conan_version.major == 1:
        os.system(f"conan user demo -r {remote_name} -p demo")

    elif conan_version.major == 2:
        os.system(f"conan remote login {remote_name} demo -p demo")

def logout_all_remotes():
    if conan_version.major == 1:
        os.system("conan user --clean")
    elif conan_version.major == 2:
        os.system('conan remote logout "*"') # need " for linux

def clean_remotes_on_ci():
    if not is_ci_job():
        return
    if conan_version.major == 1:
        os.system("conan remote clean")
    elif conan_version.major == 2:
        os.system("conan remote remove conancenter")

def get_profiles():
    profiles = ["windows", "linux"]
    if conan_version.major == 2:
        profiles = ["windowsV2", "linuxV2"]
    return profiles

def get_current_profile():
    profiles = get_profiles()
    for profile in profiles:
        if platform.system().lower() in profile:
            return profile


def run_conan_server():
    os.system("conan_server")


def start_conan_server():
    # Setup Server config
    os.system("conan_server --migrate")  # call server once to create a config file
    config_path = Path.home() / ".conan_server" / "server.conf"
    os.makedirs(str(config_path.parent), exist_ok=True)
    # configre server config file
    cp = configparser.ConfigParser()
    cp.read(str(config_path))
    # add write permissions
    if "write_permissions" not in cp:
        cp.add_section("write_permissions")
    cp["write_permissions"]["*/*@*/*"] = "*"
    with config_path.open('w', encoding="utf8") as fd:
        cp.write(fd)

    # Setup default profile
    paths = PathSetup()
    profiles_path = paths.testdata_path / "conan" / "profile"
    if conan_version.major == 1:
        conan = ConanApi()
        os.makedirs(conan._client_cache.profiles_path, exist_ok=True)
        shutil.copy(str(profiles_path / platform.system().lower()),  conan._client_cache.default_profile_path)
    elif conan_version.major == 2:
        os.system("conan profile detect")

    # Add to firewall
    if platform.system() == "Windows":
        # check if firewall was set
        try:
            check_output("netsh advfirewall firewall show rule conan_server").decode("cp850")
        except CalledProcessError:
            # allow server port for private connections
            args = f'advfirewall firewall add rule name="conan_server" program="{sys.executable}" dir= in action=allow protocol=TCP localport=9300'
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "netsh", args, None, 1)
            print("Adding firewall rule for conan_server")

    # Start Server
    global conan_server_thread
    if not conan_server_thread:
        conan_server_thread = Thread(name="ConanServer", daemon=True, target=run_conan_server)
        conan_server_thread.start()
        time.sleep(3)
    print("ADDING CONAN REMOTE")
    clean_remotes_on_ci()
    add_remote(TEST_REMOTE_NAME, TEST_REMOTE_URL)
    login_test_remote(TEST_REMOTE_NAME)
    os.system(f"conan remote enable {TEST_REMOTE_NAME}")
    # Create test data
    if SKIP_CREATE_CONAN_TEST_DATA:
        return
    print("CREATING TESTDATA FOR LOCAL CONAN SERVER")

    for profile in get_profiles():
        profile_path = profiles_path / profile
        create_test_ref(TEST_REF, paths, [f"-pr {str(profile_path)}",
                         f"-o shared=False -pr {str(profile_path)}"], update=True)
        create_test_ref(TEST_REF_OFFICIAL, paths, [f"-pr {str(profile_path)}"], update=True)
        if not conan_version.major == 2:
            paths = PathSetup()
            conanfile = str(paths.testdata_path / "conan" / "conanfile_no_settings.py")
            conan_create_and_upload(conanfile,  "nocompsettings/1.0.0@local/no_sets")


@pytest.fixture(scope="session", autouse=True)
def ConanServer():
    os.environ["CONAN_NON_INTERACTIVE"] = "True"  # don't hang is smth. goes wrong
    started = False
    if not check_if_process_running("conan_server", timeout_s=0):
        started = True
        print("STARTING CONAN SERVER")
        start_conan_server()
    yield
    if started:
        print("\nKILLING CONAN SERVER\n ")
        check_if_process_running("conan_server", timeout_s=0, kill=True)
        conan_server_thread.join()


@pytest.fixture(autouse=True)
def test_output():
    print("\n********************** Starting TEST ********************************")
    yield
    print("\n********************** Finished TEST ********************************")


@pytest.fixture
def base_fixture()-> Generator[PathSetup, None, None]:
    """
    Set up the global variables to be able to start the application.
    Needs to be used, if the tested component uses the global Logger.
    Clean up all instances after the test.
    """
    paths = PathSetup()
    os.environ["CONAN_REVISIONS_ENABLED"] = "1"

    yield paths
    # Teardown

    # delete cache file
    if (base_path / ConanInfoCache.CACHE_FILE_NAME).exists():
        try:
            os.remove(base_path / ConanInfoCache.CACHE_FILE_NAME)
        except PermissionError:  # just Windows things...
            time.sleep(5)
            os.remove(base_path / ConanInfoCache.CACHE_FILE_NAME)
