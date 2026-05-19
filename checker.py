from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QTableWidgetItem,
    QMessageBox,
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from PyQt5 import uic
import sys
import json
import os
import glob
import cv2
import subprocess

FRAMES_DIR = ".nexis/miner/frames"
INFO_DIR = ".nexis/miner/info"
CLIP_DIR = ".nexis/miner/clips"

# season
SUMMER = 1
WINTER = 2

# environment
WATER = 16
LAND = 32
SEA = 64

# place
CITY = 256
NATURE = 512

CATEGORY_GROUPS = (
    ("env", (("water", WATER), ("land", LAND), ("sea", SEA))),
    ("season", (("summer", SUMMER), ("winter", WINTER))),
    ("place", (("city", CITY), ("nature", NATURE))),
)


class StatisticsWindow(QDialog):
    def __init__(self, image_files, parent=None):
        super().__init__(parent)
        uic.loadUi("statistics.ui", self)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setFixedSize(self.size())
        self.image_files = image_files
        self.category_values = self._load_category_values()

        self._checkboxes = {
            "water": self.water_check,
            "land": self.land_check,
            "sea": self.sea_check,
            "summer": self.summer_check,
            "winter": self.winter_check,
            "city": self.city_check,
            "nature": self.nature_check,
        }

        for checkbox in self._checkboxes.values():
            checkbox.stateChanged.connect(self.update_statistics)

        self.close_btn.clicked.connect(self.close)
        self.update_statistics()

    def _load_category_values(self):
        values = []
        for img_path in self.image_files:
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            json_path = os.path.join(INFO_DIR, base_name + ".json")
            category = 0
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r") as f:
                        data = json.load(f)
                    category = int(data.get("Category", 0))
                except Exception as e:
                    print(f"Error reading JSON for statistics: {e}")
            values.append(category)
        return values

    def _count_with_flag(self, flag):
        return sum(1 for value in self.category_values if value & flag)

    def _group_selections(self):
        groups = []
        for group_name, items in CATEGORY_GROUPS:
            selected = [
                flag
                for label, flag in items
                if self._checkboxes[label].isChecked()
            ]
            groups.append(selected)
        return groups

    def _matches_filter(self, category_value):
        for selected in self._group_selections():
            if not selected:
                continue
            if not any(category_value & flag for flag in selected):
                return False
        return True

    def update_statistics(self):
        total = len(self.image_files)
        self.total_label.setText(f"Total Clips: {total}")

        has_filter = any(selected for selected in self._group_selections())
        if has_filter:
            matching = sum(
                1
                for value in self.category_values
                if self._matches_filter(value)
            )
        else:
            matching = total
        self.matching_label.setText(f"Matching filter: {matching}")

        for group_name, items in CATEGORY_GROUPS:
            for label, flag in items:
                count = self._count_with_flag(flag)
                self._checkboxes[label].setText(f"{label} ({count})")


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("checker.ui", self)  # Load your .ui file
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setFixedSize(self.size())
        self.setWindowTitle("Frame Checker")

        self.load_images()

        # Connect buttons
        self.next_btn.clicked.connect(self.next_image)
        self.before_btn.clicked.connect(self.prev_image)
        self.delete_btn.clicked.connect(self.delete_files)
        self.caption_btn.clicked.connect(self.check_captions)
        self.statistic_btn.clicked.connect(self.show_statistics)
        self.video_btn.clicked.connect(self.show_mp4_mpv)
        self.open_btn.clicked.connect(self.open_directory)
        self._stats_window = None

        # Configure SpinBox
        self.clip_num.setMinimum(1)
        self.clip_num.setMaximum(max(1, len(self.image_files)))
        self.clip_num.setValue(self.current_index + 1)
        self.clip_num.valueChanged.connect(self.on_clip_num_changed)

        # Default radio button values
        self.set_default_category()

        # Show first image
        if self.image_files:
            self.show_image()
        else:
            self.clear_all()

        # Install global event filter to handle keys
        self.installEventFilter(self)

    # ----------------------------
    # CATEGORY HELPERS
    # ----------------------------
    def set_default_category(self):
        """Default: water + summer + city"""
        self.land_radio.setChecked(True)
        self.summer_radio.setChecked(True)
        self.nature_radio.setChecked(True)

    def get_category_value(self):
        """Read radio button states and combine category flags."""
        category_value = 0
        # Environment
        if self.water_radio.isChecked():
            category_value |= WATER
        elif self.land_radio.isChecked():
            category_value |= LAND
        elif self.sea_radio.isChecked():
            category_value |= SEA
        # Season
        if self.summer_radio.isChecked():
            category_value |= SUMMER
        elif self.winter_radio.isChecked():
            category_value |= WINTER
        # Place
        if self.city_radio.isChecked():
            category_value |= CITY
        elif self.nature_radio.isChecked():
            category_value |= NATURE
        return category_value

    def set_category_from_value(self, category_value):
        """Set radio buttons from Category value."""
        # Environment
        if category_value & WATER:
            self.water_radio.setChecked(True)
        elif category_value & LAND:
            self.land_radio.setChecked(True)
        elif category_value & SEA:
            self.sea_radio.setChecked(True)
        else:
            self.water_radio.setChecked(True)
        # Season
        if category_value & SUMMER:
            self.summer_radio.setChecked(True)
        elif category_value & WINTER:
            self.winter_radio.setChecked(True)
        else:
            self.summer_radio.setChecked(True)
        # Place
        if category_value & CITY:
            self.city_radio.setChecked(True)
        elif category_value & NATURE:
            self.nature_radio.setChecked(True)
        else:
            self.city_radio.setChecked(True)

    def save_current_category_to_json(self):
        """Save current radio button category to current image JSON."""
        if not self.image_files:
            return
        img_path = self.image_files[self.current_index]
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        json_path = os.path.join(INFO_DIR, base_name + ".json")
        data = {}

        # Load existing JSON if exists
        if os.path.exists(json_path):
            try:
                with open(json_path, "r") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"Error reading JSON for category save: {e}")

        # Update category
        data["Category"] = self.get_category_value()

        # Save back
        try:
            with open(json_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving Category to JSON: {e}")

    # ----------------------------
    # IMAGE LOADING
    # ----------------------------
    def load_images(self):
        self.image_files = sorted(
            glob.glob(os.path.join(FRAMES_DIR, "*.png"))
            + glob.glob(os.path.join(FRAMES_DIR, "*.jpg"))
            + glob.glob(os.path.join(FRAMES_DIR, "*.jpeg"))
        )
        self.current_index = 0
        self.update_total_count()

    def update_total_count(self):
        total = len(self.image_files)
        self.total_cnt.setText(f"{total}")

    # ----------------------------
    # GLOBAL KEY EVENTS
    # ----------------------------
    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress:
            key = event.key()

            # Navigation
            if key == Qt.Key_V:
                self.prev_image()
                return True
            elif key == Qt.Key_W:
                self.delete_files()
                return True
            elif key == Qt.Key_Control:
                # Ctrl alone pressed → next image
                self.next_image()
                return True

            # Cycle radio buttons
            elif key == Qt.Key_A:
                self.cycle_environment()
                return True
            elif key == Qt.Key_S:
                self.cycle_season()
                return True
            elif key == Qt.Key_D:
                self.cycle_place()
                return True

        return super().eventFilter(obj, event)

    # ----------------------------
    # RADIO BUTTON CYCLE HELPERS
    # ----------------------------
    def cycle_environment(self):
        if self.water_radio.isChecked():
            self.land_radio.setChecked(True)
        elif self.land_radio.isChecked():
            self.sea_radio.setChecked(True)
        else:
            self.water_radio.setChecked(True)

    def cycle_season(self):
        if self.summer_radio.isChecked():
            self.winter_radio.setChecked(True)
        else:
            self.summer_radio.setChecked(True)

    def cycle_place(self):
        if self.city_radio.isChecked():
            self.nature_radio.setChecked(True)
        else:
            self.city_radio.setChecked(True)

    # ----------------------------
    # NAVIGATION
    # ----------------------------
    def next_image(self):
        if not self.image_files:
            return
        self.save_current_category_to_json()
        self.current_index = (self.current_index + 1) % len(self.image_files)
        self.show_image()

    def prev_image(self):
        if not self.image_files:
            return
        self.current_index = (self.current_index - 1) % len(self.image_files)
        self.show_image()

    def on_clip_num_changed(self, value):
        """Jump to selected frame from SpinBox."""
        if not self.image_files:
            return
        new_index = max(0, min(value - 1, len(self.image_files) - 1))
        if new_index != self.current_index:
            self.current_index = new_index
            self.show_image()

    # ----------------------------
    # DISPLAY
    # ----------------------------
    def show_image(self):
        if not self.image_files:
            return
        img_path = self.image_files[self.current_index]
        pixmap = QPixmap(img_path)
        self.first_frame.setPixmap(pixmap)
        self.first_frame.setScaledContents(True)

        # Update SpinBox
        self.clip_num.blockSignals(True)
        self.clip_num.setMaximum(max(1, len(self.image_files)))
        self.clip_num.setValue(self.current_index + 1)
        self.clip_num.blockSignals(False)

        # Load JSON
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        json_path = os.path.join(INFO_DIR, base_name + ".json")
        if os.path.exists(json_path):
            self.load_json_to_table(json_path)
        else:
            self.info_widget.clear()
            self.set_default_category()

        # Load MP4
        mp4_path = os.path.join(CLIP_DIR, base_name + ".mp4")
        if os.path.exists(mp4_path):
            self.show_mp4_frames(mp4_path)
        else:
            self.clear_frames()

    def load_json_to_table(self, filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            self.info_widget.clear()
            self.set_default_category()
            return

        # Set category radios
        if "Category" in data:
            self.set_category_from_value(data["Category"])
        else:
            self.set_default_category()

        # Populate table
        self.info_widget.clear()
        self.info_widget.setRowCount(len(data))
        self.info_widget.setColumnCount(2)
        self.info_widget.setHorizontalHeaderLabels(["Key", "Value"])
        for row, (key, value) in enumerate(data.items()):
            self.info_widget.setItem(row, 0, QTableWidgetItem(str(key)))
            self.info_widget.setItem(row, 1, QTableWidgetItem(str(value)))
        self.info_widget.resizeColumnsToContents()
        self.info_widget.resizeRowsToContents()

    # ----------------------------
    # VIDEO FRAME DISPLAY
    # ----------------------------
    def show_mp4_frames(self, mp4_path):
        cap = cv2.VideoCapture(mp4_path)
        if not cap.isOpened():
            self.clear_frames()
            return
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_text.setText(f"duration: {(total_frames)/24:.2f} s")
        if total_frames == 0:
            cap.release()
            return
        frame_indices = [24, total_frames // 2, total_frames - 1]
        check_frames = [self.check_frame1, self.check_frame2, self.check_frame3]
        for idx, frame_no in enumerate(frame_indices):
            if frame_no >= total_frames:
                check_frames[idx].clear()
                continue
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(
                    frame.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                pixmap = QPixmap.fromImage(qt_image)
                check_frames[idx].setPixmap(pixmap)
                check_frames[idx].setScaledContents(True)
            else:
                check_frames[idx].clear()
        cap.release()

    def clear_frames(self):
        self.check_frame1.clear()
        self.check_frame2.clear()
        self.check_frame3.clear()

    # ----------------------------
    # Video player
    # ----------------------------
    def show_mp4_mpv(self):
        """Open MP4 using system default video player (cross-platform)."""
        if not self.image_files:
            return

        img_path = self.image_files[self.current_index]
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        mp4_path = os.path.abspath(os.path.join(CLIP_DIR, base_name + ".mp4"))

        if not os.path.exists(mp4_path):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("MP4 Not Found")
            msg.setText(f"No MP4 file found for {base_name}.")
            msg.exec_()
            return

        try:
            # Windows
            if sys.platform.startswith("win"):
                os.startfile(mp4_path)

            # macOS
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", mp4_path])

            # Linux / Ubuntu / most Unix
            else:
                subprocess.Popen(["xdg-open", mp4_path])

        except Exception as e:
            # Fallback: try common players manually
            fallback_players = [
                ["vlc", mp4_path],
                ["mpv", mp4_path],
                ["totem", mp4_path],
                ["smplayer", mp4_path],
            ]

            opened = False

            for player_cmd in fallback_players:
                try:
                    subprocess.Popen(player_cmd)
                    opened = True
                    break
                except Exception:
                    continue

            if not opened:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("Error Opening MP4")
                msg.setText(
                    f"Could not open video with default player or fallback players.\n\nError:\n{e}"
                )
                msg.exec_()

    # ----------------------------
    # FRAMES_DIR = ".nexis/miner/frames"
    # INFO_DIR = ".nexis/miner/info"
    # CLIP_DIR = ".nexis/miner/clips"
    # update FRAMES_DIR, INFO_DIR, CLIP_DIR with opened directory in directory open dialogue and reload images
    def open_directory(self):
        from PyQt5.QtWidgets import QFileDialog

        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Directory", os.getcwd()
        )
        if dir_path:
            global FRAMES_DIR, INFO_DIR, CLIP_DIR
            FRAMES_DIR = os.path.join(dir_path, "frames")
            INFO_DIR = os.path.join(dir_path, "info")
            CLIP_DIR = os.path.join(dir_path, "clips")
            self.load_images()
            if self.image_files:
                self.current_index = 0
                self.show_image()
            else:
                self.clear_all()

    def show_statistics(self):
        if self._stats_window is not None:
            self._stats_window.close()
        self._stats_window = StatisticsWindow(self.image_files, self)
        self._stats_window.show()

    # ----------------------------
    # CAPTION CHECK
    # ----------------------------
    def check_captions(self):
        no_caption_files = []
        for img_path in self.image_files:
            base_name = os.path.splitext(os.path.basename(img_path))[0]
            json_path = os.path.join(INFO_DIR, base_name + ".json")
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r") as f:
                        data = json.load(f)
                        if not data.get("caption"):
                            no_caption_files.append(os.path.basename(json_path))
                except Exception as e:
                    print(f"Error reading JSON file: {e}")
                    continue
        msg = QMessageBox()
        if no_caption_files:
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Missing Captions")
            msg.setText(f"{len(no_caption_files)} files are missing captions.")
            msg.setInformativeText("\n".join(no_caption_files))
        else:
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("All Captions Present")
            msg.setText("All files have captions.")
        msg.exec_()

    # ----------------------------
    # DELETE
    # ----------------------------
    def delete_files(self):
        if not self.image_files:
            return
        img_path = self.image_files[self.current_index]
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        files_to_delete = [
            img_path,
            os.path.join(INFO_DIR, base_name + ".json"),
            os.path.join(CLIP_DIR, base_name + ".mp4"),
        ]
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)
                print("Deleted:", file)
        del self.image_files[self.current_index]
        if self.current_index >= len(self.image_files):
            self.current_index = len(self.image_files) - 1
        self.update_total_count()
        if self.image_files:
            self.show_image()
        else:
            self.clear_all()

    # ----------------------------
    # CLEAR
    # ----------------------------
    def clear_all(self):
        self.first_frame.clear()
        self.clear_frames()
        self.info_widget.clear()
        self.clip_num.blockSignals(True)
        self.clip_num.setMaximum(1)
        self.clip_num.setValue(1)
        self.clip_num.blockSignals(False)
        self.set_default_category()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())