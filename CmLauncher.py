
from PIL import Image, ImageDraw, ImageFilter, ImageQt
import uuid
from PyQt6.QtGui import QFontDatabase, QFont, QDesktopServices, QColor, QPixmap, QImage
from Launcherdesign import Ui_CmLauncher
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import QSettings, Qt, QEasingCurve, QPropertyAnimation, QRect, QSize, pyqtProperty, QTimer, QUrl, QPoint
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsDropShadowEffect, QFileDialog, QLineEdit, QFrame,
QPushButton, QLabel, QWidget, QVBoxLayout, QDialog, QMessageBox)
import psutil
import os
from test2 import main
from pathlib import Path
import sys
import threading
import requests
import json
import  socket
import shutil
import subprocess

class Animated:
    def __init__(self, button: QPushButton):
        self.button = button
        self.default_icon_size = button.iconSize()

        self.animated_icon_size = QSize(
            self.default_icon_size.width() - 2,
            self.default_icon_size.height() - 2
        )

        button.pressed.connect(self.start_animation)

    def start_animation(self):
        self.grow_animation = QPropertyAnimation(self.button, b"iconSize")
        self.grow_animation.setDuration(250)
        self.grow_animation.setStartValue(self.default_icon_size)
        self.grow_animation.setEndValue(self.animated_icon_size)
        self.grow_animation.setEasingCurve(QEasingCurve.Type.InOutSine)

        self.shrink_animation = QPropertyAnimation(self.button, b"iconSize")
        self.shrink_animation.setDuration(250)
        self.shrink_animation.setStartValue(self.animated_icon_size)
        self.shrink_animation.setEndValue(self.default_icon_size)
        self.shrink_animation.setEasingCurve(QEasingCurve.Type.InOutSine)

        self.grow_animation.finished.connect(self.shrink_animation.start)
        self.grow_animation.start()

def prepare_mask(size, antialias=4):
    mask = Image.new("L", (size[0] * antialias, size[1] * antialias), 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + mask.size, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)

def crop(im, size):
    w, h = im.size
    k = w / size[0] - h / size[1]
    if k > 0:
        im = im.crop(((w - h) / 2, 0, (w + h) / 2, h))
    elif k < 0:
        im = im.crop((0, (h - w) / 2, w, (h + w) / 2))
    return im.resize(size, Image.Resampling.LANCZOS)

def make_circle_avatar(image_path, size):
    image = Image.open(image_path).convert("RGBA")
    image = crop(image, size)
    mask = prepare_mask(size, antialias=4)
    image.putalpha(mask)
    return image

def load_fonts():
    font1_id = QFontDatabase.addApplicationFont("fonts/NotoSans.ttf")
    if font1_id == -1:
        print("error")
    else:
        font1_family = QFontDatabase.applicationFontFamilies(font1_id)[0]

    font2_id = QFontDatabase.addApplicationFont("fonts/Rubik-VariableFont_wght.ttf")
    if font2_id == -1:
        print("error")
    else:
        font2_family = QFontDatabase.applicationFontFamilies(font2_id)[0]

class MyApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        load_fonts()
        self.isAnimating = False
        self.ui = Ui_CmLauncher()
        self.ui.setupUi(self)
        self.ui.stackedWidget.setCurrentIndex(0)
        self.apply_theme("styles/dark_theme.qss")
        self.current_theme = "dark"
        self.settings_file = "settings.json"
        self.game_version = "1.21.1"
        self.fabric_version = "1.21.1"
        self.game_root = os.path.join(os.path.expanduser("~"), ".CmLauncher")
        self.settings = QSettings("MyCompany", "MyApp")
        self.ui.off_button.clicked.connect(self.close_application)
        self.appdata_path = Path(os.getenv('APPDATA'))
        self.minecraft_directory = self.appdata_path / ".CmLauncher"

        self.buttons = [self.ui.settings_button_pg1, self.ui.play_button_pg0, self.ui.button_explorepg2, self.ui.button_mappg3,
                        self.ui.bober_kombatpg4,
                        self.ui.settings_button_pg1, self.ui.off_button]  # Добавьте все кнопки из дизайна
        self.animated_buttons = [Animated(button) for button in self.buttons]

        self.set_ram_slider()
        self.ui.RAM_horizontalSlider.valueChanged.connect(self.update_ram_label)

        #swich_page
        self.ui.play_button_pg0.clicked.connect(lambda: self.switch_page(0))
        self.ui.settings_button_pg1.clicked.connect(lambda: self.switch_page(1))
        self.ui.button_explorepg2.clicked.connect(lambda: self.switch_page(2))
        self.ui.button_mappg3.clicked.connect(lambda: self.switch_page(3))
        self.ui.bober_kombatpg4.clicked.connect(lambda: self.switch_page(4))

        self.ui.update_progressBar.hide()
        self.total_files = 0
        self.files_downloaded = 0

        self.nickname_widget = QFrame(self)
        self.nickname_widget.setObjectName("nickname_widget")
        self.nickname_widget.setFixedSize(140, 90)
        self.nickname_widget.setVisible(False)

        self.nickname_edit = QLineEdit(self.nickname_widget)
        self.nickname_edit.setPlaceholderText("nickname")
        self.nickname_edit.setGeometry(0, 0, 150, 30)

        self.avatar_button = QPushButton("Выбрать аватар", self.nickname_widget)
        self.avatar_button.setGeometry(0, 30, 150, 30)
        self.avatar_button.clicked.connect(self.choose_image)

        self.save_button = QPushButton("Сохранить", self.nickname_widget)
        self.save_button.setGeometry(0, 60, 150, 30)
        self.save_button.clicked.connect(self.save_settings)

        self.ui.miniavatar_label.mousePressEvent = self.toggle_nickname_widget

        self.nickname_edit.textChanged.connect(self.update_nick_start_info_3)
        self.load_settings()
        self.ui.folder_open.clicked.connect(self.open_folder)
        self.ui.play_button.clicked.connect(self.handle_start_button)


    def open_folder(self):
        if self.minecraft_directory.exists():
            os.system(f'explorer "{self.minecraft_directory}"')
        else:
            QMessageBox.warning(self, "Ошибка", f"Директория {self.minecraft_directory} не существует.")

    def handle_start_button(self):
        threading.Thread(target=self.start_minecraft_loader, daemon=True).start()

    def start_minecraft_loader(self):
        try:
            import minecraft_loader
            minecraft_loader.main()
        except Exception as e:
            print(f"Ошибка: {e}")

    def close_application(self):
        self.close()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                settings = json.load(f)

            self.loaded_ram_value = settings.get("ram", 2048)
            self.ui.RAM_horizontalSlider.setValue(self.loaded_ram_value)

            nickname = settings.get("nickname", "")
            self.nickname_edit.setText(nickname)

            avatar_path = settings.get("avatar_path", "")
            if avatar_path and os.path.exists(avatar_path):
                self.avatar_path = avatar_path
                self.set_avatars(avatar_path)
            else:
                self.avatar_path = ""
        else:
            self.loaded_ram_value = 2048
            self.avatar_path = ""

    def closeEvent(self, event):

        print("closeEvent вызван")
        self.save_settings_on_close(event)

    def save_settings_on_close(self, event):
        print(f"Путь к аватарке: {getattr(self, 'avatar_path', 'Не установлен')}")

        settings = {
            "nickname": self.nickname_edit.text(),
            "ram": self.ui.RAM_horizontalSlider.value(),
            "avatar_path": getattr(self, "avatar_path", "")
        }
        try:
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=4)
                print("Настройки успешно сохранены.")
        except Exception as e:
            print(f"settings save error: {e}")
        event.accept()

    def save_settings(self):
        print(f"Путь к аватарке: {getattr(self, 'avatar_path', 'Не установлен')}")

        settings = {
            "nickname": self.nickname_edit.text(),
            "ram": self.ui.RAM_horizontalSlider.value(),
            "avatar_path": getattr(self, "avatar_path", "")
        }

        try:
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=4)
                print("Настройки успешно сохранены.")
        except Exception as e:
            print(f"settings save error: {e}")

    def toggle_nickname_widget(self, event):

        if self.nickname_widget.isVisible():
            self.nickname_widget.setVisible(False)
        else:
            miniavatar_pos = self.ui.miniavatar_label.pos()
            self.nickname_widget.move(miniavatar_pos.x() + 60, miniavatar_pos.y())
            self.nickname_widget.setVisible(True)

    def update_nick_start_info_3(self, text):
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

        if image_path:
            self.avatar_path = image_path
            print(f"Выбранный путь к изображению: {self.avatar_path}")
            self.set_avatars(image_path)

            self.nickname_widget.setVisible(False)

    def set_avatars(self, image_path):

        try:
            circular_avatar_large = make_circle_avatar(image_path, (120, 120))
            qt_image_large = ImageQt.ImageQt(circular_avatar_large)
            pixmap_large = QPixmap.fromImage(QImage(qt_image_large))
            self.ui.avatar_label.setPixmap(pixmap_large)

            circular_avatar_small = make_circle_avatar(image_path, (60, 60))
            qt_image_small = ImageQt.ImageQt(circular_avatar_small)
            pixmap_small = QPixmap.fromImage(QImage(qt_image_small))
            self.ui.miniavatar_label.setPixmap(pixmap_small)

        except Exception as e:
            print(f"Error: {e}")

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
    #apply_font_antialiasing(app)
    window = MyApp()
    window.show()
    sys.exit(app.exec())