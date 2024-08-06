

import argparse
import os
import subprocess

conan_major = 1

parser = argparse.ArgumentParser()
parser.add_argument("--conan_major_version", type=str)

args = parser.parse_args()
conan_major = args.conan_major_version

test_versions = {
    "1": ["==1.48.0", "==1.59.0", "<2"],
    "2": ["==2.0.14", "~=2.1.0", "~=2.2.0", "~=2.3.0", "~=2.4.0", "~=2.5.0"]
}

# compatbility
os.system("pip install setuptools wheel")
for conan_version in test_versions[conan_major]:

    os.system(f"pip install conan{conan_version} --use-pep517 --no-build-isolation")
    if conan_major=="2":
        os.system(f"pip install conan_server{conan_version} --use-pep517")
    conan_version_stripped = conan_version.strip("=").strip("~").strip("<")
    subprocess.run(["pytest", "-v", "test", f"--junit-xml=./results/result-unit-{conan_version_stripped}.xml",
                    "--cov=conan_unified_api", "--cov-branch", "--cov-append", "--capture=no"], 
                    check=True)
    os.environ["SKIP_CREATE_CONAN_TEST_DATA"]="True" # enable after first run
