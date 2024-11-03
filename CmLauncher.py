#pyuic6 -x launcherremake.ui -o design2.py
import minecraft_launcher_lib
import uuid
from design2 import Ui_CmLauncher # Импортируем интерфейс из сгенерированного файла
from PyQt6 import QtWidgets, QtCore
from minecraft_launcher_lib import install, utils, command
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
import psutil  # Для определения доступной оперативной памяти
import os
import sys
import threading
import requests
import os
import json


class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.isAnimating = False
        self.ui = Ui_CmLauncher()
        self.ui.setupUi(self)
        self.setFixedSize(990, 600)
        self.ui.stackedWidget.setCurrentIndex(0)
        self.apply_theme("styles/dark_theme.qss")
        self.current_theme = "dark"
        self.settings_file = "settings.json"

        self.game_version = "1.21.1"
        self.game_root = os.path.join(os.path.expanduser("~"), ".CmLauncher")

        self.settings = QSettings("MyCompany", "MyApp")

        self.load_settings()

        self.set_ram_slider()

        # Подключение кнопок
        self.ui.folder_mine_open.clicked.connect(self.open_minecraft_folder)
        self.ui.RAM_horizontalSlider.valueChanged.connect(self.update_ram_label)

        # Закрытие приложения — сохранение настроек
        self.closeEvent = self.save_settings_on_close


        if self.is_version_installed(self.game_version):
            self.ui.play_button.setText("PLAY")
        else:
            self.ui.play_button.setText("download")


        self.ui.play_button.clicked.connect(self.handle_start_button)

        self.total_files = 0
        self.files_downloaded = 0

        # stackedwidget_switcher
        self.ui.play_button_pg0.clicked.connect(lambda: self.switch_page(0))
        self.ui.settings_button_pg2.clicked.connect(lambda: self.switch_page(1))
        self.ui.account_button_pg1.clicked.connect(lambda: self.switch_page(2))
        #self.ui.bank_button_pg3.clicked.connect(lambda: self.switch_page(3))

    def load_settings(self):
        """Загружает настройки из файла."""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
            # Сохраняем загруженное значение RAM для последующего использования
            self.loaded_ram_value = settings.get("ram", 2048)
            self.ui.Nickname_input.setText(settings.get("nickname", ""))
        else:
            self.loaded_ram_value = 2048

    def set_ram_slider(self):
        """Настраивает диапазон слайдера для выбора оперативной памяти."""
        total_ram = psutil.virtual_memory().total // (1024 * 1024)  # в мегабайтах
        self.ui.RAM_horizontalSlider.setRange(2048, total_ram)  # от 2 ГБ до максимума
        self.update_ram_label()  # Обновление отображаемого значения

        # Установка значения слайдера после установки диапазона
        QtCore.QTimer.singleShot(0, self.set_slider_value)

    def set_slider_value(self):
        """Устанавливает значение слайдера после установки диапазона."""
        self.ui.RAM_horizontalSlider.setValue(self.loaded_ram_value)
        self.update_ram_label()

    def save_settings_on_close(self, event):
        """Сохраняет настройки перед закрытием приложения."""
        settings = {
            "nickname": self.ui.Nickname_input.text(),
            "ram": self.ui.RAM_horizontalSlider.value()
        }
        with open(self.settings_file, "w") as f:
            json.dump(settings, f)
        event.accept()  # Закрыть приложение после сохранения

    def open_minecraft_folder(self):
        """Открывает папку Minecraft."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.game_root))

    def update_ram_label(self):
        """Обновляет отображение выбранного объема памяти."""
        ram_mb = self.ui.RAM_horizontalSlider.value()
        self.ui.Ram_label.setText(f"{ram_mb} MB")

    def handle_start_button(self):
        """Логика загрузки и запуска Minecraft."""
        if not self.is_version_installed(self.game_version):
            # Начало загрузки, если версия не установлена
            self.ui.minecraft_download_label.setText("Скачивание файлов Minecraft...")
            self.ui.minecraft_download_label.show()  # Показать лейбл прогресса
            threading.Thread(target=self.download_minecraft).start()
        else:
            # Запуск игры, если версия уже установлена
            self.start_game()

    def is_version_installed(self, version):
        """Проверяет, установлена ли указанная версия Minecraft."""
        if not utils.is_minecraft_installed(self.game_root):
            return False
        version_path = os.path.join(self.game_root, "versions", version)
        return os.path.exists(version_path)

    def download_minecraft(self):
        """Загружает Minecraft с отображением прогресса."""
        try:
            install.install_minecraft_version(
                self.game_version,
                self.game_root,
                callback={
                    "setStatus": self.set_status,
                }
            )
            self.on_download_complete()
        except Exception as e:
            self.ui.minecraft_download_label.setText(f"Ошибка загрузки: {str(e)}")
            print(f"Ошибка загрузки: {str(e)}")

    def set_status(self, status):
        """Обновляет текущий файл в QLabel."""
        self.ui.minecraft_download_label.setText(f"{status}")

    def on_download_complete(self):
        """Обработка завершения загрузки."""
        self.ui.minecraft_download_label.setText("Загрузка завершена!")
        self.ui.play_button.setText("PLAY")
        QtCore.QTimer.singleShot(1000, self.hide_progress)  # Скрыть лейбл через 1 сек

    def hide_progress(self):
        """Скрывает лейбл после загрузки."""
        self.ui.minecraft_download_label.hide()

    def start_game(self):
        """Запускает Minecraft в оффлайн-режиме с настройками пользователя."""
        nickname = self.ui.Nickname_input.text()
        ram = self.ui.RAM_horizontalSlider.value()

        options = {
            "username": nickname,
            "uuid": str(uuid.uuid4()),
            "version": self.game_version,
            "gameDirectory": self.game_root,
            "jvmArguments": [f"-Xmx{ram}M"]
        }

        try:
            command_list = minecraft_launcher_lib.command.get_minecraft_command(self.game_version, self.game_root,
                                                                                options)
            threading.Thread(target=self.run_command, args=(command_list,)).start()
        except Exception as e:
            self.ui.minecraft_download_label.setText(f"Ошибка запуска: {str(e)}")
            print(f"Ошибка запуска: {str(e)}")
            self.ui.minecraft_download_label.show()

    def run_command(self, command_list):
        """Выполняет команду для запуска Minecraft."""
        os.system(" ".join(command_list))

    def apply_theme(self, theme_file):
        """Загрузить и применить тему из QSS файла."""
        with open(theme_file, "r") as f:
            style = f.read()
            self.setStyleSheet(style)

    def set_white_theme(self):
        """Установить светлую тему."""
        self.apply_theme("styles/light_theme.qss")
        self.current_theme = "light"

    def set_black_theme(self):
        """Установить темную тему."""
        self.apply_theme("styles/dark_theme.qss")
        self.current_theme = "dark"

    def switch_page(self, index):
        """Переключение страниц с анимацией сверху вниз."""
        if self.isAnimating or index == self.ui.stackedWidget.currentIndex():
            return  # Если анимация уже выполняется или нажата та же кнопка, ничего не делаем

        self.isAnimating = True  # Устанавливаем флаг анимации

        current_widget = self.ui.stackedWidget.currentWidget()
        next_widget = self.ui.stackedWidget.widget(index)

        # Устанавливаем начальные параметры для следующего виджета
        next_widget.setGeometry(current_widget.geometry())  # Совпадение геометрии текущего виджета
        next_widget.show()  # Показываем следующий виджет

        # Анимация для текущего виджета (выход вниз)
        self.animation_out = QtCore.QPropertyAnimation(current_widget, b"geometry")
        self.animation_out.setDuration(500)
        self.animation_out.setStartValue(current_widget.geometry())
        self.animation_out.setEndValue(QtCore.QRect(
            current_widget.x(),
            current_widget.y() + current_widget.height(),  # Двигаем вниз
            current_widget.width(),
            current_widget.height()
        ))

        # Анимация для следующего виджета (вход сверху)
        self.animation_in = QtCore.QPropertyAnimation(next_widget, b"geometry")
        self.animation_in.setDuration(500)
        self.animation_in.setStartValue(QtCore.QRect(
            next_widget.x(),
            next_widget.y() - next_widget.height(),  # Начальная позиция сверху
            next_widget.width(),
            next_widget.height()
        ))
        self.animation_in.setEndValue(current_widget.geometry())  # Конечная позиция

        # Устанавливаем эффект ease in-out
        self.animation_out.setEasingCurve(QtCore.QEasingCurve.Type.InOutCirc)
        self.animation_in.setEasingCurve(QtCore.QEasingCurve.Type.InOutCirc)

        # Переключение страниц после завершения анимации выхода
        self.animation_out.finished.connect(lambda: self.finalize_switch_page(index, current_widget))

        # Запуск анимаций
        self.animation_out.start()
        self.animation_in.start()

    def finalize_switch_page(self, index, current_widget):
        """Завершение переключения страницы."""
        self.ui.stackedWidget.setCurrentIndex(index)
        current_widget.hide()  # Скрываем текущий виджет после анимации
        self.isAnimating = False  # Сбрасываем флаг анимации

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())