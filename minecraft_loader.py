import minecraft_launcher_lib
import subprocess
import os
import sys
import json
from pathlib import Path

# Функции обратного вызова для отслеживания прогресса

def set_status(gui_instance, status: str):
    gui_instance.log_to_console(f"Статус: {status}")

def set_progress(gui_instance, progress: int):
    gui_instance.log_to_console(f"Прогресс: {progress}")

def set_max(gui_instance, new_max: int):
    gui_instance.log_to_console(f"Максимум: {new_max}")


# Функция для загрузки настроек из settings.json
def load_settings():
    settings_path = Path("settings.json")
    if not settings_path.exists():
        print("Файл settings.json не найден! Убедитесь, что он находится в той же директории, что и скрипт.")
        return None

    try:
        with open(settings_path, "r", encoding="utf-8") as file:
            settings = json.load(file)
            return settings
    except json.JSONDecodeError as e:
        print(f"Ошибка чтения settings.json: {e}")
        return None


# Основная логика
def main(gui_instance):
    # Загружаем настройки
    settings = load_settings()
    if not settings:
        gui_instance.log_to_console("Не удалось загрузить настройки!")
        return

    nickname = settings.get("nickname", "Player")
    memory = settings.get("ram", 2048)

    print(f"Никнейм: {nickname}")
    print(f"Выделено оперативной памяти: {memory} МБ")


    minecraft_version = "1.21.1"  # Версия Minecraft

    # Определяем путь к директории Minecraft динамически
    appdata_path = Path(os.getenv('APPDATA'))
    minecraft_directory = appdata_path / ".CmLauncher"

    if not minecraft_directory.exists():
        print(f"Директория {minecraft_directory} не найдена! Убедитесь, что путь указан верно.")
        return

    # Проверяем, что Java установлена
    java_path = minecraft_launcher_lib.utils.get_java_executable()
    if not java_path:
        print("Java не найдена! Установите Java и проверьте её доступность.")
        return

    print(f"Используем Java: {java_path}")

    if memory < 512:
        print("Минимальное значение оперативной памяти - 512 МБ.")
        return

    # Словарь с функциями обратного вызова
    callback = {
        "setStatus": lambda status: set_status(gui_instance, status),
        "setProgress": lambda progress: set_progress(gui_instance, progress),
        "setMax": lambda new_max: set_max(gui_instance, new_max),
    }

    # Проверяем, установлен ли Fabric
    installed_versions = minecraft_launcher_lib.utils.get_installed_versions(minecraft_directory)
    fabric_installed = any("fabric" in version["id"] for version in installed_versions)

    if fabric_installed:
        print("Fabric уже установлен. Пропускаем установку.")
    else:
        try:
            # Устанавливаем Fabric с отслеживанием прогресса
            print("Установка Fabric...")
            minecraft_launcher_lib.fabric.install_fabric(
                minecraft_version, minecraft_directory, callback=callback
            )
            print("Fabric успешно установлен.")
        except Exception as e:
            print(f"Ошибка при установке Fabric: {e}")
            return

    # Ищем установленную версию Fabric
    fabric_version = None
    for version in installed_versions:
        if "fabric" in version["id"]:
            fabric_version = version["id"]
            break

    if fabric_version is None:
        print("Версия Fabric не найдена! Убедитесь, что установка прошла успешно.")
        return

    print(f"Найдена версия Fabric: {fabric_version}")

    # Создаем параметры для запуска
    options = minecraft_launcher_lib.utils.generate_test_options()
    options["username"] = nickname  # Указываем никнейм
    options["executablePath"] = java_path  # Указываем путь к Java
    options["jvmArguments"] = [f"-Xmx{memory}M", f"-Xms{memory}M"]  # Указываем объем оперативной памяти

    try:
        # Получаем команду для запуска версии Fabric
        minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
            fabric_version, minecraft_directory, options
        )

        # Запускаем Minecraft с Fabric через subprocess
        print("Запуск Minecraft...")
        subprocess.run(minecraft_command)
    except Exception as e:
        print(f"Ошибка при запуске Minecraft: {e}")


if __name__ == "__main__":
    main()
