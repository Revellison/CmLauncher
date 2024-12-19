#pyuic6 -x launcherremake.ui -o design2.py
from PIL import Image, ImageDraw, ImageFilter, ImageQt
import minecraft_launcher_lib
import uuid
from PyQt6.QtGui import QFontDatabase, QFont
from Launcherdesign import Ui_CmLauncher # Импортируем интерфейс из сгенерированного файла
from PyQt6 import QtWidgets, QtCore
from minecraft_launcher_lib import install, utils, command
from PyQt6.QtCore import QSettings, Qt, QEasingCurve, QPropertyAnimation, QRect, QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QGraphicsDropShadowEffect, QFileDialog, QLineEdit, QFrame, QPushButton
from PyQt6.QtGui import QDesktopServices, QColor, QPixmap, QImage
from PyQt6.QtCore import QUrl, QPropertyAnimation, QEasingCurve, Qt, QPoint
import psutil  # Для определения доступной оперативной памяти
import os
import sys
import threading
import requests
import os
import json
import  socket
import shutil
import subprocess


class Animated:
    def __init__(self, button: QPushButton):
        self.button = button
        self.default_icon_size = button.iconSize()  # Запоминаем стандартный размер иконки

        # Определяем увеличенный размер иконки
        self.animated_icon_size = QSize(
            self.default_icon_size.width() - 2,
            self.default_icon_size.height() - 2
        )

        # Подключаем анимацию к нажатию
        button.pressed.connect(self.start_animation)

    def start_animation(self):
        # Анимация увеличения иконки
        self.grow_animation = QPropertyAnimation(self.button, b"iconSize")
        self.grow_animation.setDuration(250)
        self.grow_animation.setStartValue(self.default_icon_size)
        self.grow_animation.setEndValue(self.animated_icon_size)
        self.grow_animation.setEasingCurve(QEasingCurve.Type.InOutSine)

        # Анимация возврата размера иконки
        self.shrink_animation = QPropertyAnimation(self.button, b"iconSize")
        self.shrink_animation.setDuration(250)
        self.shrink_animation.setStartValue(self.animated_icon_size)
        self.shrink_animation.setEndValue(self.default_icon_size)
        self.shrink_animation.setEasingCurve(QEasingCurve.Type.InOutSine)

        # Запуск анимаций
        self.grow_animation.finished.connect(self.shrink_animation.start)
        self.grow_animation.start()

def prepare_mask(size, antialias=4):
    """Создаёт сглаженную маску круга."""
    mask = Image.new("L", (size[0] * antialias, size[1] * antialias), 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + mask.size, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)

def crop(im, size):
    """Обрезает и масштабирует изображение под заданный размер."""
    w, h = im.size
    k = w / size[0] - h / size[1]
    if k > 0:
        im = im.crop(((w - h) / 2, 0, (w + h) / 2, h))
    elif k < 0:
        im = im.crop((0, (h - w) / 2, w, (h + w) / 2))
    return im.resize(size, Image.Resampling.LANCZOS)

def make_circle_avatar(image_path, size):
    """Создаёт круглую аватарку с использованием сглаженной маски."""
    image = Image.open(image_path).convert("RGBA")
    image = crop(image, size)
    mask = prepare_mask(size, antialias=4)
    image.putalpha(mask)
    return image

def load_fonts():

    font1_id = QFontDatabase.addApplicationFont("fonts/NotoSans.ttf")
    if font1_id == -1:
        print("Ошибка: шрифт 'NotoSans' не загружен!")
    else:
        font1_family = QFontDatabase.applicationFontFamilies(font1_id)[0]
        print(f"Шрифт '{font1_family}' успешно загружен!")


    font2_id = QFontDatabase.addApplicationFont("fonts/NicoMoji-Regular.ttf")
    if font2_id == -1:
        print("Ошибка: шрифт 'NicoMoji' не загружен!")
    else:
        font2_family = QFontDatabase.applicationFontFamilies(font2_id)[0]
        print(f"Шрифт '{font2_family}' успешно загружен!")


class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        load_fonts()
        self.isAnimating = False
        self.ui = Ui_CmLauncher()  # Ваш UI класс
        self.ui.setupUi(self)
        self.ui.stackedWidget.setCurrentIndex(0)
        self.apply_theme("styles/dark_theme.qss")
        self.current_theme = "dark"
        self.settings_file = "settings.json"
        self.game_version = "1.21.1"
        self.fabric_version = "1.21.1"
        self.game_root = os.path.join(os.path.expanduser("~"), ".CmLauncher")
        self.ui.play_button.clicked.connect(self.handle_start_button)
        self.settings = QSettings("MyCompany", "MyApp")

        self.buttons = [self.ui.settings_button_pg1, self.ui.play_button_pg0, self.ui.button_explorepg2, self.ui.button_mappg3,
                        self.ui.bober_kombatpg4,
                        self.ui.settings_button_pg1, self.ui.off_button]  # Добавьте все кнопки из дизайна
        self.animated_buttons = [Animated(button) for button in self.buttons]

        # Инициализация интерфейса и связки сигналов
        self.set_ram_slider()
        self.ui.RAM_horizontalSlider.valueChanged.connect(self.update_ram_label)


        # Кнопки для переключения страниц
        self.ui.play_button_pg0.clicked.connect(lambda: self.switch_page(0))
        self.ui.settings_button_pg1.clicked.connect(lambda: self.switch_page(1))
        self.ui.button_explorepg2.clicked.connect(lambda: self.switch_page(2))
        self.ui.button_mappg3.clicked.connect(lambda: self.switch_page(3))
        self.ui.bober_kombatpg4.clicked.connect(lambda: self.switch_page(4))
        self.ui.setavatar.clicked.connect(self.choose_image)

        # Настройка кнопки для запуска игры
        if self.is_version_installed(self.game_version):
            self.ui.play_button.setText("Connect")
        else:
            self.ui.play_button.setText("download")

        self.ui.play_button.clicked.connect(self.handle_start_button)

        self.total_files = 0
        self.files_downloaded = 0

        # Инициализация виджета для ввода никнейма
        self.nickname_widget = QFrame(self)
        self.nickname_widget.setObjectName("nickname_widget")
        self.nickname_widget.setFixedSize(150, 30)
        self.nickname_widget.setVisible(False)

        self.nickname_edit = QLineEdit(self.nickname_widget)
        self.nickname_edit.setPlaceholderText("nickname")
        self.nickname_edit.setGeometry(0, 0, 150, 30)

        self.nickname_edit.textChanged.connect(self.update_nick_start_info_3)
        self.ui.miniavatar_label.mousePressEvent = self.toggle_nickname_widget

        # Загружаем настройки после полной инициализации виджетов
        self.load_settings()

    def load_settings(self):
        """Загружает настройки из JSON файла и применяет их к интерфейсу."""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                settings = json.load(f)

            # Загружаем значение RAM и устанавливаем его в слайдер
            self.loaded_ram_value = settings.get("ram", 2048)
            self.ui.RAM_horizontalSlider.setValue(self.loaded_ram_value)

            # Загружаем никнейм и устанавливаем его в nickname_edit
            nickname = settings.get("nickname", "")
            self.nickname_edit.setText(nickname)

            # Загружаем путь к аватарке
            avatar_path = settings.get("avatar_path", "")
            if avatar_path and os.path.exists(avatar_path):
                self.avatar_path = avatar_path
                self.set_avatars(avatar_path)
            else:
                self.avatar_path = ""
        else:
            # Устанавливаем значения по умолчанию
            self.loaded_ram_value = 2048
            self.avatar_path = ""

    def closeEvent(self, event):
        """Переопределение метода закрытия окна."""
        print("closeEvent вызван")  # Проверка, вызывается ли метод
        self.save_settings_on_close(event)  # Вызов сохранения настроек

    def save_settings_on_close(self, event):
        """Сохраняет настройки перед закрытием приложения."""
        # Отладка
        print(f"Сохранение настроек...")
        print(f"Путь к аватарке: {getattr(self, 'avatar_path', 'Не установлен')}")

        settings = {
            "nickname": self.nickname_edit.text(),
            "ram": self.ui.RAM_horizontalSlider.value(),
            "avatar_path": getattr(self, "avatar_path", "")  # Сохраняем путь или пустую строку
        }

        try:
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=4)  # Сохраняем с отступами для читабельности
                print("Настройки успешно сохранены.")
        except Exception as e:
            print(f"Ошибка при сохранении настроек: {e}")

        event.accept()

    def toggle_nickname_widget(self, event):
        """Переключает видимость виджета для ввода никнейма."""
        if self.nickname_widget.isVisible():
            self.nickname_widget.setVisible(False)
        else:
            miniavatar_pos = self.ui.miniavatar_label.pos()
            self.nickname_widget.move(miniavatar_pos.x() + 60, miniavatar_pos.y())  # Сдвиг на 60px вправо
            self.nickname_widget.setVisible(True)

    def update_nick_start_info_3(self, text):
        """Обновляет текст в QLabel nick_start_info_3."""
        if hasattr(self.ui, 'nick_start_info_3'):
            self.ui.nick_start_info_3.setText(text)
        else:
            print("Error: nick_start_info_3 not found.")

    def choose_image(self):
        file_dialog = QFileDialog()
        image_path, _ = file_dialog.getOpenFileName(
            self,
            "Выберите изображение",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if image_path:  # Если файл выбран
            self.avatar_path = image_path  # Сохраняем путь
            print(f"Выбранный путь к изображению: {self.avatar_path}")  # Отладка
            self.set_avatars(image_path)

    def set_avatars(self, image_path):

        try:
            # Круглая аватарка для avatar_label (120x120)
            circular_avatar_large = make_circle_avatar(image_path, (120, 120))
            qt_image_large = ImageQt.ImageQt(circular_avatar_large)
            pixmap_large = QPixmap.fromImage(QImage(qt_image_large))
            self.ui.avatar_label.setPixmap(pixmap_large)

            # Круглая аватарка для miniavatar_label (60x60)
            circular_avatar_small = make_circle_avatar(image_path, (60, 60))
            qt_image_small = ImageQt.ImageQt(circular_avatar_small)
            pixmap_small = QPixmap.fromImage(QImage(qt_image_small))
            self.ui.miniavatar_label.setPixmap(pixmap_small)

        except Exception as e:
            print(f"Error: {e}")

    def is_version_installed(self, version_id):
        """Проверяет, установлена ли указанная версия Minecraft."""
        installed_versions = minecraft_launcher_lib.utils.get_installed_versions(self.game_root)
        return any(version["id"] == version_id for version in installed_versions)

    def setup_fabric(self):
        """Устанавливает Fabric для указанной версии Minecraft."""
        try:
            minecraft_launcher_lib.fabric.install_fabric(self.fabric_version, self.game_root)
            print(f"Fabric для версии {self.fabric_version} успешно установлен.")
        except Exception as e:
            print(f"Ошибка при установке Fabric: {e}")

    def install_minecraft(self):
        """Устанавливает базовую версию Minecraft."""
        try:
            callbacks = {
                "setStatus": self.ui.minecraft_download_label.setText,
                "setProgress": self.ui.progress_bar.setValue,
                "setMax": self.ui.progress_bar.setMaximum,
            }
            minecraft_launcher_lib.install.install_minecraft_version(self.game_version, self.game_root,
                                                                     callback=callbacks)
            print(f"Minecraft версии {self.game_version} успешно установлен.")
        except Exception as e:
            print(f"Ошибка при установке Minecraft: {e}")

    def run_minecraft(self):
        """Запускает Minecraft с установленным Fabric."""
        try:
            # Генерация тестовых опций
            options = minecraft_launcher_lib.utils.generate_test_options()

            # Добавление параметров JVM
            options["jvmArguments"] = [f"-Xmx{self.ui.RAM_horizontalSlider.value()}M", "-Xms512M"]
            options["launcherName"] = "CmLauncher"
            options["launcherVersion"] = "1.0"
            options["gameDirectory"] = self.game_root

            # Получение команды запуска Minecraft
            minecraft_command = minecraft_launcher_lib.command.get_minecraft_command(
                f"fabric-loader-{self.fabric_version}", self.game_root, options
            )

            # Запуск Minecraft через subprocess
            subprocess.run(minecraft_command)
            print("Minecraft успешно запущен.")
        except Exception as e:
            print(f"Ошибка при запуске Minecraft: {e}")

    def handle_start_button(self):
        """Обрабатывает нажатие на кнопку Play."""
        try:
            if not self.is_version_installed(self.game_version):
                print("Minecraft не установлен. Начинаем установку...")
                self.install_minecraft()

            # Проверяем наличие установленного Fabric
            fabric_version_id = f"fabric-loader-{self.fabric_version}"
            if not self.is_version_installed(fabric_version_id):
                print("Fabric не установлен. Начинаем установку...")
                self.setup_fabric()

            # После установки запускаем Minecraft
            self.run_minecraft()
        except Exception as e:
            print(f"Ошибка при обработке кнопки Play: {e}")

    def set_ram_slider(self):
        total_ram = psutil.virtual_memory().total // (1024 * 1024)
        self.ui.RAM_horizontalSlider.setRange(2048, total_ram)
        self.update_ram_label()
        QtCore.QTimer.singleShot(0, self.set_slider_value)

    def set_slider_value(self):
        self.ui.RAM_horizontalSlider.setValue(self.loaded_ram_value)
        self.update_ram_label()



    def open_minecraft_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.game_root))

    def update_ram_label(self):
        ram_mb = self.ui.RAM_horizontalSlider.value()
        self.ui.Ram_label.setText(f"{ram_mb} MB")



    def set_max(self, max_value):
        self.ui.progress_bar.setMaximum(max_value)



    def hide_progress(self):
        self.ui.minecraft_download_label.hide()



    def update_nickname_display(self):
        nickname = self.ui.Nickname_input.text()
        self.ui.nick_start_info.setText(nickname)
        self.ui.nick_profile_info.setText(nickname)



    def apply_theme(self, theme_file):
        with open(theme_file, "r") as f:
            style = f.read()
            self.setStyleSheet(style)

    def set_white_theme(self):
        self.apply_theme("styles/light_theme.qss")
        self.current_theme = "light"

    def set_black_theme(self):
        self.apply_theme("styles/dark_theme.qss")
        self.current_theme = "dark"

    def switch_page(self, index):
        if self.isAnimating or index == self.ui.stackedWidget.currentIndex():
            return

        self.isAnimating = True

        current_widget = self.ui.stackedWidget.currentWidget()
        next_widget = self.ui.stackedWidget.widget(index)
        next_widget.setGeometry(current_widget.geometry())
        next_widget.show()

        self.animation_out = QtCore.QPropertyAnimation(current_widget, b"geometry")
        self.animation_out.setDuration(500)
        self.animation_out.setStartValue(current_widget.geometry())
        self.animation_out.setEndValue(QtCore.QRect(
            current_widget.x(),
            current_widget.y() + current_widget.height(),
            current_widget.width(),
            current_widget.height()
        ))

        self.animation_in = QtCore.QPropertyAnimation(next_widget, b"geometry")
        self.animation_in.setDuration(500)
        self.animation_in.setStartValue(QtCore.QRect(
            next_widget.x(),
            next_widget.y() - next_widget.height(),
            next_widget.width(),
            next_widget.height()
        ))
        self.animation_in.setEndValue(current_widget.geometry())

        self.animation_out.setEasingCurve(QtCore.QEasingCurve.Type.InOutCirc)
        self.animation_in.setEasingCurve(QtCore.QEasingCurve.Type.InOutCirc)

        self.animation_out.finished.connect(lambda: self.finalize_switch_page(index, current_widget))

        self.animation_out.start()
        self.animation_in.start()

    def finalize_switch_page(self, index, current_widget):
        self.ui.stackedWidget.setCurrentIndex(index)
        current_widget.hide()
        self.isAnimating = False

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())