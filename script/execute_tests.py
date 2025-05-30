import argparse
import os
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

conan_major = 1

parser = argparse.ArgumentParser()
parser.add_argument("--conan_major_version", type=str, default="1")

args = parser.parse_args()
conan_major = args.conan_major_version

os.system("pip install setuptools wheel tomli")
# read in version number from pyproject.toml
import tomli

versions_2 = ["==2.0.14"]  # only supported version for conan 2.0.X
pyproject = tomli.loads(Path("pyproject.toml").read_text())
minor_version_max = int(pyproject["project"]["version"].split(".")[1])

deps = pyproject["project"]["dependencies"]
for dep in deps:
    if dep.startswith("conan"):
        if int(dep.split("<")[1].split(".")[1]) - 1 != minor_version_max:
            raise Exception("Minor version of project is not conan version")

for minor in range(1, minor_version_max + 1):
    versions_2.append(f"~=2.{minor}.0")
test_versions = {
    "1": ["==1.48.0", "==1.59.0", "<2"],
    "2": versions_2,
}

# compatbility
ci_name = platform.system() + "_Py" + "_".join(map(str, sys.version_info[0:2]))
for conan_version in test_versions[conan_major]:
    subprocess.run(
        ["pip", "install", f"conan{conan_version}", "--use-pep517", "--no-build-isolation"],
        check=True,
    )  # "--no_build_isolation"
    if conan_major == "2":
        os.system(f"pip install conan_server{conan_version} --use-pep517")
    conan_version_stripped = conan_version.strip("==").strip("~=")
    if "<" in conan_version_stripped:
        conan_version_stripped = str(int(conan_version_stripped.strip("<")) - 1) + "-latest"
    subprocess.run(
        [
            "pytest",
            "-v",
            "test",
            f"--junit-xml=./results/result-unit-{conan_version_stripped}.xml",
            f"--cov-report=xml:cov/cov-{ci_name}-{conan_version_stripped}.xml",
            "--cov=conan_unified_api",
            "--cov-branch",
            "--cov-append",
            "--capture=no",
        ],
        check=True,
    )
    os.environ["SKIP_CREATE_CONAN_TEST_DATA"] = "True"  # enable after first run

## normalize coverage paths

for cov_file in (Path(".") / "cov").glob("*.xml"):
    root = ET.fromstring(cov_file.read_text())
    source = root.find(".//sources/source")
    orig_path = source.text
    new_path = "./" + Path(source.text).name
    print(f"Replaced {orig_path} to {new_path}")
    source.text = new_path
    cov_file.write_text(ET.tostring(root).decode("utf-8"))
