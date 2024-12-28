import requests
import os
import shutil
import json
import re
import tkinter as tk
from tkinter import messagebox

# Путь к файлу с версией
VERSION_FILE = 'version.json'

# URL к последнему релизу на GitHub
GITHUB_API_URL = 'https://api.github.com/repos/Revellison/CmLauncher/releases/latest'


def get_current_version():
    """Считывает текущую версию приложения из JSON файла."""
    if not os.path.exists(VERSION_FILE):
        print("Файл version.json не найден.")
        return 'v0.0.0'  # Возврат версии по умолчанию

    with open(VERSION_FILE, 'r') as file:
        data = json.load(file)
        return data.get('version', 'v0.0.0')


def update_version_json(new_version):
    """Обновляет версию приложения в JSON файле."""
    data = {'version': new_version}
    with open(VERSION_FILE, 'w') as file:
        json.dump(data, file, indent=4)
    print(f"Версия обновлена до {new_version} в version.json")


def check_for_updates(current_version):
    """
    Проверяет, есть ли новая версия приложения на GitHub.
    Возвращает информацию о последнем релизе или None.
    """
    try:
        response = requests.get(GITHUB_API_URL)
        response.raise_for_status()

        latest_release = response.json()
        latest_version = latest_release['tag_name']  # Тег версии, например, 'v1.0.1'

        # Сравниваем версии
        if compare_versions(latest_version, current_version):
            return latest_release
    except requests.RequestException as e:
        print(f"Ошибка при проверке обновлений: {e}")
    return None


def compare_versions(latest_version, current_version):
    """
    Сравнивает версии в формате vX.X.X.
    Возвращает True, если latest_version новее current_version.
    """
    latest = list(map(int, re.findall(r'\d+', latest_version)))
    current = list(map(int, re.findall(r'\d+', current_version)))
    return latest > current


def download_and_update(update_info):
    """
    Скачивает последнюю версию, распаковывает и обновляет приложение.
    """
    download_url = update_info['zipball_url']  # Ссылка на архив с релизом
    print("Скачивание обновления...")

    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        # Сохраняем архив
        with open('update.zip', 'wb') as file:
            file.write(response.content)

        # Распаковываем архив
        print("Распаковка обновления...")
        shutil.unpack_archive('update.zip', 'temp_update')

        # Копируем новые файлы поверх старых
        for root, _, files in os.walk('temp_update'):
            for file in files:
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, 'temp_update')
                destination_path = os.path.join(os.getcwd(), relative_path)

                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                shutil.copy2(source_path, destination_path)

        # Удаляем временные файлы
        shutil.rmtree('temp_update')
        os.remove('update.zip')

        print("Обновление успешно установлено.")
        return True
    except Exception as e:
        print(f"Ошибка при установке обновления: {e}")
        return False


def perform_update():
    """Главная функция для выполнения обновления."""
    print("Запуск автообновления...")

    # Чтение текущей версии
    current_version = get_current_version()
    print(f"Текущая версия: {current_version}")

    # Проверка наличия обновлений
    update_info = check_for_updates(current_version)
    if update_info:
        print(f"Доступна новая версия: {update_info['tag_name']}")
        user_input = show_update_message()

        if user_input == 'yes':
            if download_and_update(update_info):
                update_version_json(update_info['tag_name'])
                show_message("Обновление завершено. Перезапустите приложение.")
            else:
                show_message("Ошибка при обновлении.")
        else:
            print("Обновление отменено пользователем.")
    else:
        print("Вы используете последнюю версию.")


def show_update_message():
    """Показывает сообщение с предложением обновления и возвращает ответ пользователя."""
    root = tk.Tk()
    root.withdraw()  # Скрываем главное окно

    # Показываем окно с вопросом
    response = messagebox.askyesno(
        "Обновление доступно",
        "Доступна новая версия приложения. Хотите обновить?"
    )
    return 'yes' if response else 'no'


def show_message(message):
    """Показывает сообщение пользователю в виде окна."""
    root = tk.Tk()
    root.withdraw()  # Скрываем главное окно

    messagebox.showinfo("Информация", message)


# Функции для интеграции в основной код:

def check_and_update():
    """Проверка обновлений и выполнение их в случае необходимости."""
    current_version = get_current_version()
    update_info = check_for_updates(current_version)

    if update_info:
        print(f"Найдена новая версия: {update_info['tag_name']}")
        return update_info['tag_name']
    else:
        print("Нет доступных обновлений.")
        return None


def update_application(update_info):
    """Обновление приложения с использованием информации о релизе."""
    if download_and_update(update_info):
        update_version_json(update_info['tag_name'])
        return True
    else:
        return False


if __name__ == "__main__":
    # В этом месте можно вызвать функции из основного кода:
    check_and_update()  # Проверка наличия обновлений
    # В дальнейшем вы можете интегрировать вызов `update_application` для установки обновлений.
