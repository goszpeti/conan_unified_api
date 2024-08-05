
"""
This module is for conan cli command wrappers, which are used for the testcases,
where we don't want to use the conan_unified_api methods for setting up the testcases.
"""
import os
import platform
import subprocess
from conan_unified_api import conan_version
from conan_unified_api.types import ConanRef
from . import TEST_REMOTE_NAME, PathSetup, is_ci_job, conan_api

# TESTED feature switches - after these switches are set true,
# the cli functions will switch to the much faster internal methods
TESTED_ADD_REMOVE_REMOTE = False #not is_ci_job()
TESTED_DISABLE_REMOTE = False # not is_ci_job()

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


def conan_add_editables(conanfile_path: str, reference: ConanRef):  # , path: str
    if conan_version.major == 2:
        os.system(f"conan editable add --version {reference.version} "
                  f"--channel {reference.channel} --user {reference.user}  {conanfile_path}")
    else:
        os.system(f"conan editable add {conanfile_path} {str(reference)}")


def conan_create(conanfile: str, ref: str, create_params=""):
    if conan_version.major == 1:
        os.system(f"conan create {conanfile} {ref} {create_params}")
    elif conan_version.major == 2:
        ref = ref.replace("@_/_", "")  # does not work anymore...
        cfr = ConanRef.loads(ref)
        extra_args = ""
        if cfr.user:
            extra_args = f"--user={cfr.user} "
        if cfr.channel:
            extra_args += f"--channel={cfr.channel} "
        os.system(
            f"conan create {conanfile} --name={cfr.name} --version={cfr.version} {extra_args} {create_params}")


def conan_upload(ref: str):
    if conan_version.major == 1:
        os.system(f"conan upload {ref} -r {TEST_REMOTE_NAME} --force --all")
    elif conan_version.major == 2:
        os.system(f"conan upload {ref} -r {TEST_REMOTE_NAME} --force")

def add_remote(remote_name, url):
    if TESTED_ADD_REMOVE_REMOTE:
        try:
            conan_api.add_remote(remote_name, url, False) # only local remotes
        except Exception as e: # already added
            pass
        return
    if conan_version.major == 1:
        os.system(f"conan remote add {remote_name} {url} false")
    elif conan_version.major == 2:
        os.system(f"conan remote add {remote_name} {url} --insecure")


def disable_remote(remote_name):
    if TESTED_DISABLE_REMOTE:
        conan_api.disable_remote(remote_name, True)
    os.system(f"conan remote disable {remote_name}")

def get_remote_list():
    ret = subprocess.check_output("conan remote list").decode()
    lines = ret.split("\n")
    remote_list = []
    for line in lines:
        remote_list.append(line.split(" ")[0].rstrip(":"))
    return remote_list

def remove_remote(remote_name):
    if TESTED_ADD_REMOVE_REMOTE:
        try:
            conan_api.remove_remote(remote_name)
        except Exception:  # don't care if it does not exist
            pass
        return
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
        os.system('conan remote logout "*"')  # need " for linux


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


def add_editable(ref, path, output_path=None):

    if conan_version.major == 1:
        add_cmd = f"conan editable add {str(path)} {ref}"
    else:
        conan_ref = ConanRef.loads(ref)
        add_cmd = (f"conan editable add {str(path)} --name {conan_ref.name} --version {conan_ref.version} "
                   f" --channel {conan_ref.channel} --user {conan_ref.user}")
    if output_path: # ok for both
        add_cmd += " -of " + str(output_path)

    os.system(add_cmd)

def remove_editable(ref):
    if conan_version.major == 1:
        os.system(f"conan editable remove {ref}")
    else:
        os.system(f"conan editable remove -r {ref}")
