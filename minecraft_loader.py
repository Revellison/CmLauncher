import minecraft_launcher_lib
import subprocess
import os
import sys
import json
from pathlib import Path
import requests, shutil, urllib.parse
from zipfile import ZipFile
import hashlib

# Constants
DIRECT_MRPACK_URL = "https://www.dropbox.com/scl/fi/284edmjcoryuzq9kdz0fb/CmLauncher-Modpack-1.0.0.mrpack?rlkey=hekinnutqwvz16sy86y3pwpbh&st=98822nh7&dl=1"
APPDATA_PATH = os.path.join(os.getenv('APPDATA'), ".CmLauncher")
modrinthHeaders = {"User-Agent": "Provi Modpack Installer (https://github.com/Provismet/Modrinth-Modpack-Installer)"}

def download_file(url, local_filename):
    with requests.get(url, stream=True, headers=modrinthHeaders) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def get_filename_from_url(url):
    parsed = urllib.parse.urlparse(url)
    return os.path.basename(parsed.path)

def calculate_file_hash(filepath, hash_type="sha1"):
    hash_func = hashlib.new(hash_type)
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def downloadSingleMod(url: str, downloadPath: str, expected_hash: str = None) -> None:
    modName = os.path.basename(downloadPath)
    if os.path.exists(downloadPath):
        if expected_hash:
            local_hash = calculate_file_hash(downloadPath)
            if local_hash == expected_hash:
                print(f"{modName} is already downloaded and verified.")
                return
            else:
                print(f"{modName} hash mismatch. Redownloading...")
        else:
            print(f"{modName} already exists. Skipping hash check.")
            return

    response = None
    hadError = False

    try:
        response = requests.get(url, headers=modrinthHeaders)
    except Exception as e:
        print(f"Could not download mod ({modName}) from URL: {url}")
        hadError = True

    if response is not None:
        try:
            with open(downloadPath, 'wb') as file:
                file.write(response.content)
        except Exception as e:
            print(f"Could not save mod ({modName}) due to error: {str(e)}")
            print(f"Please manually download mod ({modName}) from url: {url}")
            hadError = True

    if not hadError:
        print(f"Downloaded: {modName}")

def install_modpack():
    tempDirectory = os.path.join(os.curdir, ".modrinthInstallerTemp")
    mrpack_filename = get_filename_from_url(DIRECT_MRPACK_URL)
    MRPACK_PATH = os.path.join(os.curdir, mrpack_filename)

    try:
        print(f"Downloading modpack as {mrpack_filename}...")
        download_file(DIRECT_MRPACK_URL, MRPACK_PATH)

        os.makedirs(tempDirectory, exist_ok=True)

        with ZipFile(MRPACK_PATH, 'r') as zip:
            zip.extractall(tempDirectory)

        overridesFolder = os.path.join(tempDirectory, "overrides")

        if os.path.isdir(overridesFolder):
            for item in os.listdir(overridesFolder):
                s = os.path.join(overridesFolder, item)
                d = os.path.join(APPDATA_PATH, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

        if not os.path.isdir(os.path.join(APPDATA_PATH, "mods")):
            os.makedirs(os.path.join(APPDATA_PATH, "mods"))

        with open(os.path.join(tempDirectory, "modrinth.index.json"), 'r') as indexFile:
            jsonIndex = json.load(indexFile)

        print(f"Downloading {len(jsonIndex['files'])} mods...")
        for fileData in jsonIndex["files"]:
            mod_path = os.path.join(APPDATA_PATH, fileData["path"])
            downloadSingleMod(fileData["downloads"][0], mod_path, fileData.get("hashes", {}).get("sha1"))

        print("\nModpack installation done.")
    except Exception as e:
        print(f"\nFailed due to error: {str(e)}")
        print("Try again with administrator privileges.\n")

    try:
        shutil.rmtree(tempDirectory)
    except Exception as e:
        print(f"Failed to remove temporary directory: \"{tempDirectory}\"")
        print("Please remove temporary directory manually.")

def load_settings():
    settings_path = Path("settings.json")
    if not settings_path.exists():
        return {}
    try:
        with settings_path.open("r", encoding="utf-8") as file:
            settings = json.load(file)
            return settings
    except json.JSONDecodeError:
        return {}

def save_settings(data):
    settings_path = Path("settings.json")
    with settings_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def launch_minecraft():
    settings = load_settings()
    if not settings:
        print("Failed to load settings!")
        return

    minecraft_version = "1.21.1"
    nickname = settings.get("nickname", "Player")
    memory = settings.get("ram", 2048)

    print(f"Nickname: {nickname}")
    print(f"Allocated memory: {memory} MB")

    minecraft_directory = Path(os.getenv('APPDATA')) / ".CmLauncher"

    if not minecraft_directory.exists():
        print(f"Directory {minecraft_directory} not found! Make sure the path is correct.")
        return

    java_path = minecraft_launcher_lib.utils.get_java_executable()
    if not java_path:
        print("Java not found! Install Java and make sure it's accessible.")
        return

    print(f"Using Java: {java_path}")

    if memory < 512:
        print("Minimum memory allocation is 512 MB.")
        return

    installed_versions = minecraft_launcher_lib.utils.get_installed_versions(minecraft_directory)
    fabric_installed = any("fabric" in version["id"] for version in installed_versions)

    if not fabric_installed:
        print("Installing Fabric...")
        minecraft_launcher_lib.fabric.install_fabric(minecraft_version, minecraft_directory)
        print("Fabric installed successfully.")

    fabric_version = next((version["id"] for version in installed_versions if "fabric" in version["id"]), None)
    if fabric_version is None:
        print("Fabric version not found! Make sure installation was successful.")
        return

    print(f"Found Fabric version: {fabric_version}")

    options = minecraft_launcher_lib.utils.generate_test_options()
    options["username"] = nickname
    options["executablePath"] = java_path
    options["jvmArguments"] = [f"-Xmx{memory}M", f"-Xms{memory}M"]

    try:
        minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(fabric_version, minecraft_directory,
                                                                                 options)
        subprocess.run(minecraft_command)
    except Exception as e:
        print(f"Error launching Minecraft: {e}")

def main():
    settings = load_settings()

    # Check modpack-status to determine whether to install or skip installation
    if "modpack-status" not in settings or settings["modpack-status"] != "installed":
        print("Installing or updating modpack...")
        install_modpack()
        settings["modpack-status"] = "installed"
        save_settings(settings)
    else:
        print("Modpack already installed, skipping installation.")

    # Launch Minecraft
    launch_minecraft()

if __name__ == "__main__":
    main()
