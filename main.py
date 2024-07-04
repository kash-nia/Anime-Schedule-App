import os
import sys
import json
import re
import requests
import xml.etree.ElementTree as ET
from functools import partial
from datetime import datetime, timedelta
from PySide2.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QLineEdit, QDateTimeEdit, QCheckBox, QComboBox, QTabWidget, QLabel, QInputDialog,
                               QDateEdit, QTimeEdit, QMessageBox, QMenu, QSystemTrayIcon, QAction, QStyle, QDialog,
                               QScrollArea, QGridLayout)
from PySide2.QtCore import Qt, QTimer, QTime, QDate, QRegExp, QDateTime, QPoint, QRect, QEvent
from PySide2.QtGui import QRegExpValidator, QIcon
import pygame

# Global variables
last_alarm_time = None
COOLDOWN_PERIOD = timedelta(minutes=2)
SNOOZE_PERIOD = timedelta(minutes=3)

CONFIG_FILE = os.path.join("Data", f"tabs_config.json")

outer_layer_styling = "background-color: #0a0f18; color: #00ffff;"
frame_styling_data = "background: #141e2c; font-size: 15px; border: 1px solid #1c2936; border-radius: 5px;"
top_layout_styling = "background: #1c2936; border: 1px solid #2a3f55; border-radius: 5px; margin: 5px;"

table_styling_data = """
    QTableWidget {
        font-size: 18px;
        background: #0a0f18;
        color: #00ffff;
        gridline-color: #1c2936;
        border: 1px solid #2a3f55;
        border-radius: 5px;
    }
    QTableWidget QTableCornerButton::section {
        background: #141e2c;
        border: none;
    }
    QHeaderView::section {
        color: #00ffff;
        background: #141e2c;
        padding: 8px;
        border: 1px solid #2a3f55;
    }
    QLineEdit {
        background: #1c2936;
        color: #00ffff;
        border: 1px solid #2a3f55;
        padding: 5px;
        border-radius: 3px;
    }
    QTableWidget::item:selected {
        background-color: #2a3f55;
        color: #ffffff;
    }
    QDateEdit {
        background: #1c2936;
        color: #00ffff;
        border: 1px solid #2a3f55;
        padding: 5px;
        border-radius: 3px;
    }
    QTableWidget::item {
        padding: 5px;
    }
"""

main_styling = """
    QWidget {
        background-color: #0a0f18;
        color: #00ffff;
    }
    QTabWidget::pane {
        border: 1px solid #2a3f55;
        background: #0a0f18;
        top: -1px;
        border-radius: 5px;
    }
    QTabBar::tab {
        background: #141e2c;
        color: #00ffff;
        padding: 10px 20px;
        margin-right: 4px;
        border: 1px solid #2a3f55;
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }
    QTabBar::tab:selected {
        background: #2a3f55;
        color: #ffffff;
        margin-bottom: -1px;
    }
    QTabBar::tab:!selected {
        margin-top: 2px;
    }
    QPushButton {
        background-color: #1c2936;
        color: #00ffff;
        border: 1px solid #2a3f55;
        padding: 8px;
        padding-top: 4px;
        border-radius: 5px;
    }
    QPushButton:hover {
        background-color: #2a3f55;
        border: 1px solid #3d5d80;
    }
    QPushButton:pressed {
        background-color: #3d5d80;
        border: 1px solid #4d7ba6;
    }
    QScrollBar:vertical {
        border: none;
        background: #141e2c;
        width: 10px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #2a3f55;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        background-color: #1c2936;
        border: 1px solid #2a3f55;
        border-radius: 3px;
    }
    QCheckBox::indicator:checked {
        background-color: #00ffff;
    }
"""


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


resource_path("app.ico")
resource_path("om.png")
resource_path("off.png")
resource_path("alarm.mp3")


class ScheduleApp(QWidget):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.watch_tab = ['anime', 'animes', 'movie', 'movies', 'tv', 'series', 'shows', 'show', 'seasons', ]
        self.filename_lower = self.filename.lower()
        # print(f"Initializing ScheduleApp with filename: {self.filename}")  # Debug log
        self.stop_timer = None
        self.temp_data = []  # Temporary list for sorting
        self.is_sorting = False
        self.sort_order = Qt.AscendingOrder
        self.last_sorted_column = None
        self.bar_toggle = False

        self.layout = QVBoxLayout(self)
        self.table = QTableWidget()

        # Set up the table
        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            self.table.setColumnCount(8)  # Increase column count
            self.table.setHorizontalHeaderLabels(
                ["Name", "Episode", "Date and Time", "Countdown", "Status", "Alarm", "Snooze",
                 "Next"])  # Add new header
        else:
            self.table.setColumnCount(6)
            self.table.setHorizontalHeaderLabels(
                ["Name", "Date and Time", "Countdown", "Status", "Alarm", "Snooze"])  # Add new header

        header = self.table.horizontalHeader()

        header.setStyleSheet("font-weight: bold;")
        # Set column widths
        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            self.table.setColumnWidth(1, 140)  # Countdown column width
            self.table.setColumnWidth(3, 155)  # Countdown column width
            self.table.setColumnWidth(4, 100)  # Status column width
            self.table.setColumnWidth(5, 70)  # Alarm column width
            self.table.setColumnWidth(6, 75)  # Snooze column width
            self.table.setColumnWidth(7, 100)  # Add A Week column width
        else:
            self.table.setColumnWidth(2, 150)  # Countdown column width
            self.table.setColumnWidth(3, 100)  # Status column width
            self.table.setColumnWidth(4, 70)  # Alarm column width
            self.table.setColumnWidth(5, 75)  # Snooze column width

        # Set stretch mode for the first two columns (Name and Date and Time)

        header.setSectionResizeMode(0, QHeaderView.Stretch)
        # Set fixed mode for the last three columns (Countdown, Status, Alarm, Snooze)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            header.setSectionResizeMode(6, QHeaderView.Fixed)
            header.setSectionResizeMode(1, QHeaderView.Fixed)
            header.setSectionResizeMode(2, QHeaderView.Stretch)
        else:
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.Fixed)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.table.itemChanged.connect(self.on_item_changed)  # ensures saving immediately; name, episode, date

        self.layout.addWidget(self.table)

        # Disable sorting initially
        self.table.setSortingEnabled(False)
        header = self.table.horizontalHeader()
        header.sectionClicked.connect(self.on_header_clicked)

        # Add input fields for new entries
        input_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Entry Name")

        # Date and Time for entry
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd MMM yyyy")

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("hh:mm")
        # Set up validator for time input (12-hour format)
        time_validator = QRegExpValidator(QRegExp("^(0?[1-9]|1[0-2]):[0-5][0-9]$"))
        self.time_input.setValidator(time_validator)

        # Set current time in 12-hour format
        current_time = QTime.currentTime()
        time_string = current_time.toString("h:mm")
        self.time_input.setText(time_string)

        self.am_pm_input = QComboBox()
        self.am_pm_input.addItems(["AM", "PM"])
        self.am_pm_input.setCurrentText("PM" if current_time.hour() >= 12 else "AM")
        self.update_time_input()
        # disable time input if no date is selected
        self.no_date_checkbox = QCheckBox("No date/time")
        self.no_date_checkbox.stateChanged.connect(self.toggle_datetime_input)
        self.add_button = QPushButton("Add Entry")
        self.bottom_bar = QPushButton("☰")  # toggle bottom bar button
        self.bottom_bar.setStyleSheet("font-weight: 900; text-shadow: 3px 3px 0 red; font-size: 20px; border: none;")
        self.bottom_bar.clicked.connect(self.bottom_bar_toggle)

        # entries
        input_layout.addWidget(self.name_input)
        input_layout.addWidget(self.date_input)
        input_layout.addWidget(self.time_input)
        input_layout.addWidget(self.am_pm_input)
        input_layout.addWidget(self.no_date_checkbox)
        input_layout.addWidget(self.add_button)
        input_layout.addWidget(self.bottom_bar)

        self.layout.addLayout(input_layout)

        button_layout = QHBoxLayout()
        self.move_up_button = QPushButton("Move Up")
        self.move_down_button = QPushButton("Move Down")
        button_layout.addWidget(self.move_up_button)
        button_layout.addWidget(self.move_down_button)

        # Enable sorting
        self.toggle_sort_button = QPushButton("Enable Sort")
        self.toggle_sort_button.clicked.connect(self.toggle_sort)
        button_layout.addWidget(self.toggle_sort_button)

        # input field and button for column visibility toggle
        self.column_input = QLineEdit()
        self.column_input.setPlaceholderText("Enter column numbers")
        self.visibility_on_button = QPushButton("Visibility On")
        self.visibility_on_button.clicked.connect(self.visibility_on)
        self.visibility_off_button = QPushButton("Visibility Off")
        self.visibility_off_button.clicked.connect(self.visibility_off)
        button_layout.addWidget(self.column_input)
        button_layout.addWidget(self.visibility_off_button)
        button_layout.addWidget(self.visibility_on_button)

        # Hide the buttons initially (hide buttons)
        self.visibility_off_button.hide()
        self.visibility_on_button.hide()
        self.column_input.hide()
        self.toggle_sort_button.hide()
        self.move_up_button.hide()
        self.move_down_button.hide()


        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            self.column_input.setText("3,4,5,6,7")
        else:
            self.column_input.setText("2,3,4,5")  # default column numbers

        self.layout.addLayout(button_layout)

        self.move_up_button.clicked.connect(self.move_row_up)
        self.move_down_button.clicked.connect(self.move_row_down)
        self.add_button.clicked.connect(self.add_entry)

        # Set fixed width for the buttons
        self.time_input.setFixedWidth(55)  # Set width to 100 pixels
        self.am_pm_input.setFixedWidth(50)
        self.column_input.setFixedWidth(200)  # Set width to 100 pixels
        self.visibility_on_button.setFixedWidth(100)  # Set width to 100 pixels
        self.visibility_off_button.setFixedWidth(100)  # Set width to 100 pixels
        self.bottom_bar.setFixedWidth(25)  # Set width to 100 pixels

        self.rung_alarms = set()  # New attribute to track rung alarms
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)  # Update every second

        # stylesheet
        self.setStyleSheet(table_styling_data)

        self.load_data()
        self.check_startup_alarms()
        # print("ScheduleApp initialization complete")  # Debug log

    def bottom_bar_toggle(self):
        self.bar_toggle = not self.bar_toggle
        if not self.bar_toggle:
            self.visibility_off_button.hide()
            self.visibility_on_button.hide()
            self.column_input.hide()
            self.toggle_sort_button.hide()
            self.move_up_button.hide()
            self.move_down_button.hide()
        else:
            # show buttons
            self.visibility_off_button.show()
            self.visibility_on_button.show()
            self.column_input.show()
            self.toggle_sort_button.show()
            self.move_up_button.show()
            self.move_down_button.show()

    def add_a_week_button_clicked(self, clicked_row):
        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            if not self.is_sorting:
                episode_data = self.table.item(clicked_row, 1)  # Episode
                episode_text = episode_data.text()
                datetime_item = self.table.item(clicked_row, 2)  # Get the datetime item
                datetime_str = datetime_item.text()  # if string is "N/A", do nothing
                status_check = self.table.cellWidget(clicked_row, 4).isChecked()  # status

                # print(f"Week Button Clicked")  # Debug log

                if status_check == 0:
                    pass
                    # print(f"Can't; status not checked = Status is: {status_check}")  # Debug log
                elif status_check != 0:

                    number_match = re.search(r'E-(\d+)', episode_text)  # finding episode number
                    if number_match:  # if episode number format is found [S01 E01]
                        # Convert the datetime string to a datetime object
                        date_time = datetime.strptime(datetime_str, "%d %b %Y %H:%M")
                        # Add a week to the datetime object
                        new_date_time = date_time + timedelta(weeks=1)
                        # Convert the new datetime object back to a string
                        new_date_time_str = new_date_time.strftime("%d %b %Y %H:%M")
                        # Set the new datetime string to the datetime item
                        datetime_item.setText(new_date_time_str)
                        self.table.cellWidget(clicked_row, 4).setChecked(False)  # Uncheck the status checkbox

                        # Convert to an integer and increment by 1
                        episode_number = int(number_match.group(1)) + 1
                        # Create the new episode string
                        new_episode = re.sub(r'E-\d+', f'E-{episode_number:02}', episode_text)
                        episode_data.setText(new_episode)

                        self.save_data()

    def update_time_input(self):
        current_time = QTime.currentTime()
        hour = current_time.hour() % 12
        if hour == 0:
            hour = 12
        time_string = f"{hour}:{current_time.toString('mm')}"
        self.time_input.setText(time_string)
        self.am_pm_input.setCurrentText("PM" if current_time.hour() >= 12 else "AM")

    def update_header_labels(self):
        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            headers = ["Name", "Episode", "Date and Time", "Countdown", "Status", "Alarm", "Snooze", "Add A Week"]
        else:
            headers = ["Name", "Date and Time", "Countdown", "Status", "Alarm", "Snooze"]
        if self.is_sorting and self.last_sorted_column is not None:
            arrow = " ↑" if self.sort_order == Qt.AscendingOrder else " ↓"
            headers[self.last_sorted_column] += arrow
            for row in range(self.table.rowCount()):
                if any(word.lower() in self.filename_lower for word in self.watch_tab):
                    self.table.cellWidget(row, 4).setEnabled(False)  # Status checkbox
                    self.table.cellWidget(row, 5).setEnabled(False)  # Alarm checkbox
                    self.table.cellWidget(row, 6).setEnabled(False)  # Snooze checkbox
                    self.table.cellWidget(row, 7).setEnabled(False)  # Add a Week checkbox
                else:
                    self.table.cellWidget(row, 3).setEnabled(False)  # Status checkbox
                    self.table.cellWidget(row, 4).setEnabled(False)  # Alarm checkbox
                    self.table.cellWidget(row, 5).setEnabled(False)  # Snooze checkbox
        self.table.setHorizontalHeaderLabels(headers)

    def on_item_changed(self, item):
        if not self.is_sorting:
            row = item.row()
            column = item.column()
            if any(word.lower() in self.filename_lower for word in self.watch_tab):
                date_col_no = 2
            else:
                date_col_no = 1

            if column == date_col_no:  # Date and Time column
                date_time_str = item.text()
                if date_time_str != "N/A":
                    try:
                        datetime.strptime(date_time_str, "%d %b %Y %H:%M")
                    except ValueError:
                        # print(ValueError)
                        item.setText("Invalid Date")

            self.save_data()  # Save immediately after any change
        else:
            pass
            # print("Sorting is active. Changes are not saved.")

    # --------------------- Sorting ---------------------
    def on_header_clicked(self, logical_index):
        if self.is_sorting:
            if self.last_sorted_column == logical_index:
                self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
            else:
                self.sort_order = Qt.AscendingOrder

            self.last_sorted_column = logical_index

            reverse_order = (self.sort_order == Qt.DescendingOrder)

            if logical_index == 0:  # Sort by name
                self.temp_data.sort(key=lambda x: x['name'].lower(), reverse=reverse_order)
            elif logical_index == 1 or (logical_index == 2 and "TV" in self.filename):  # Sort by date and time
                self.temp_data.sort(key=lambda x: self.date_time_sort_key(x['datetime']), reverse=reverse_order)

            self.update_table_display()
            self.update_header_labels()

    def sort_temp_data(self, column):
        reverse_order = (self.sort_order == Qt.DescendingOrder)
        if column == 0:  # Sort by name
            self.temp_data.sort(key=lambda x: x['name'].lower(), reverse=reverse_order)
        elif column == 1 or (column == 2 and "TV" in self.filename):  # Sort by datetime
            self.temp_data.sort(key=lambda x: self.date_time_sort_key(x['datetime']), reverse=reverse_order)
        else:
            self.temp_data.sort(key=lambda x: x['entry_position'], reverse=reverse_order)

    def date_time_sort_key(self, date_time_str):
        if date_time_str == "N/A":
            return datetime.max  # Put "N/A" at the end when sorting
        try:
            return datetime.strptime(date_time_str, "%d %b %Y %H:%M")
        except ValueError:
            return datetime.max  # Put invalid dates at the end when sorting

    def toggle_sort(self):
        self.is_sorting = not self.is_sorting
        if self.is_sorting:
            # Load all data into temp_data when sort is toggled on
            data = self.load_data_into_dict()
            self.temp_data = [{'key': k, **v} for k, v in data.items()]
            self.sort_order = Qt.AscendingOrder
            self.last_sorted_column = None
            self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        else:
            # Clear temp_data when toggled off
            self.temp_data = []
            self.last_sorted_column = None
            self.table.setEditTriggers(QAbstractItemView.DoubleClicked)
            # Reload data from file without adding new rows
            self.reload_data_from_file()

        self.update_table_display()
        self.update_header_labels()
        self.toggle_sort_button.setText("Disable Sort" if self.is_sorting else "Enable Sort")
        self.move_up_button.setEnabled(not self.is_sorting)
        self.move_down_button.setEnabled(not self.is_sorting)
        self.add_button.setEnabled(not self.is_sorting)

        # Enable/disable widgets based on sorting state
        for row in range(self.table.rowCount()):
            if any(word.lower() in self.filename_lower for word in self.watch_tab):
                self.table.cellWidget(row, 4).setEnabled(not self.is_sorting)  # Status
                self.table.cellWidget(row, 5).setEnabled(not self.is_sorting)  # Alarm
                self.table.cellWidget(row, 6).setDisabled(self.is_sorting)  # Snooze
                self.table.cellWidget(row, 7).setEnabled(not self.is_sorting)  # Add A Week
            else:
                self.table.cellWidget(row, 3).setEnabled(not self.is_sorting)  # Status
                self.table.cellWidget(row, 4).setEnabled(not self.is_sorting)  # Alarm
                self.table.cellWidget(row, 5).setDisabled(self.is_sorting)  # Snooze
    def reload_data_from_file(self):
        self.table.setRowCount(0)  # Clear the table
        self.load_data()  # Use the existing load_data method to reload

    def update_table_display(self):
        # print("update_table_display() called")  # Debug log
        self.table.setRowCount(0)  # Clear the table

        data_to_display = self.temp_data if self.is_sorting else self.load_data_into_dict().values()

        for item in data_to_display:
            if any(word.lower() in self.filename_lower for word in self.watch_tab):
                self.add_table_row(
                    name=item['name'],
                    episode=item['episode'],
                    date_time=item['datetime'],
                    status=item['status'],
                    alarm=item.get('alarm', False),
                    snooze=item.get('snooze', False)
                )
            else:
                self.add_table_row(
                    name=item['name'],
                    date_time=item['datetime'],
                    status=item['status'],
                    alarm=item.get('alarm', False),
                    snooze=item.get('snooze', False)
                )

        # Update the header to show sort indicators
        if self.is_sorting and self.last_sorted_column is not None:
            self.table.horizontalHeader().setSortIndicator(self.last_sorted_column, self.sort_order)

    def update_entry_positions(self):
        data = self.load_data_into_dict()
        sorted_items = sorted(data.items(), key=lambda x: x[1]['entry_position'])
        for i, (key, item) in enumerate(sorted_items):
            item['entry_position'] = i
        self.save_data_from_dict(data)

    def toggle_datetime_input(self, state):
        is_checked = state == Qt.Checked
        self.date_input.setEnabled(not is_checked)
        self.time_input.setEnabled(not is_checked)
        self.am_pm_input.setEnabled(not is_checked)

        if is_checked:
            self.date_input.clear()
            self.time_input.clear()
            self.am_pm_input.setCurrentIndex(0)
        else:
            # Reset to current date and time when unchecked
            self.date_input.setDate(QDate.currentDate())
            self.update_time_input()

    # --------------------- Data ------------------------
    def add_table_row(self, name, date_time="N/A", status=False, alarm=False, snooze=False,
                      episode="S01 E-01"):  # change addaweek
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(name))

        # Status
        status_checkbox = QCheckBox()
        status_checkbox.setChecked(status)
        status_checkbox.stateChanged.connect(self.save_data())  # Connect the signal here

        status_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 100%;

            }
            QCheckBox::indicator:checked {
                width: 100%;

        
            }
        """)

        # Alarm
        alarm_checkbox = QCheckBox()
        alarm_checkbox.setChecked(alarm)
        alarm_checkbox.stateChanged.connect(
            lambda state, r=row: self.on_alarm_changed(r, state))  # Connect the signal here

        alarm_checkbox.setStyleSheet(
            "QCheckBox::indicator:unchecked { background: none; width: 60px; height: 40px; image: url('off.png'); } QCheckBox::indicator:checked { background: none; width: 60px; height: 40px; image: url('on.png'); }")

        # Snooze
        snooze_checkbox = QCheckBox()
        snooze_checkbox.setChecked(snooze)
        snooze_checkbox.setEnabled(alarm)
        # disable snooze if no alarm
        snooze_checkbox.stateChanged.connect(
            lambda state, r=row: self.on_snooze_changed(r, state))  # Connect the signal here

        snooze_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                background: #4e4e4e;
                width: 100%;

            }
            QCheckBox::indicator:checked {
                background: green;
                width: 100%;


            }
        """)

        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            # Add A Week
            add_a_week_button = QPushButton("+1 Week")  # addaweek
            add_a_week_button.clicked.connect(
                lambda r=row: self.add_a_week_button_clicked(r))  # addaweek button clicked
            self.table.setItem(row, 1, QTableWidgetItem(episode))
            self.table.setItem(row, 2, QTableWidgetItem(date_time))
            self.table.setItem(row, 3, QTableWidgetItem("N/A" if date_time == "N/A" else ""))
            self.table.setCellWidget(row, 4, status_checkbox)
            self.table.setCellWidget(row, 5, alarm_checkbox)
            self.table.setCellWidget(row, 6, snooze_checkbox)
            self.table.setCellWidget(row, 7, add_a_week_button)  # change addaweek
        else:
            self.table.setItem(row, 1, QTableWidgetItem(date_time))
            self.table.setItem(row, 2, QTableWidgetItem("N/A" if date_time == "N/A" else ""))
            self.table.setCellWidget(row, 3, status_checkbox)
            self.table.setCellWidget(row, 4, alarm_checkbox)
            self.table.setCellWidget(row, 5, snooze_checkbox)

    def add_entry(self):
        name = self.name_input.text()
        if self.no_date_checkbox.isChecked():
            date_time = "N/A"
        else:
            date = self.date_input.date()
            time_str = self.time_input.text()
            am_pm = self.am_pm_input.currentText()

            # Parse the time string
            try:
                hour, minute = map(int, time_str.split(':'))
                if am_pm == "PM" and hour != 12:
                    hour += 12
                elif am_pm == "AM" and hour == 12:
                    hour = 0

                # Create QDateTime object
                qdatetime = QDateTime(date, QTime(hour, minute))

                # Format as 24-hour string
                date_time = qdatetime.toString("dd MMM yyyy HH:mm")
            except ValueError:
                # Handle invalid time input
                QMessageBox.warning(self, "Invalid Time", "Please enter a valid time in hh:mm format.")
                return
        if name:
            data = self.load_data_into_dict()
            new_key = str(max(map(int, data.keys())) + 1 if data else 0)

            if any(word.lower() in self.filename_lower for word in self.watch_tab):
                new_entry = {
                    "entry_position": len(data),
                    "name": name,
                    "episode": "S01 E-00",
                    "datetime": date_time,
                    "status": False,
                    "alarm": False,
                    "snooze": False

                }
            else:
                new_entry = {
                    "entry_position": len(data),
                    "name": name,
                    "datetime": date_time,
                    "status": False,
                    "alarm": False,
                    "snooze": False
                }
            data[new_key] = new_entry
            self.save_data_from_dict(data)
            self.add_table_row(name=name, date_time=date_time, status=False)
            self.name_input.clear()

            # Update this line to use the new time input method
            self.update_time_input()
            # Reset date to current date
            self.date_input.setDate(QDate.currentDate())

    def load_data(self):
        try:
            with open(self.filename, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}

        # Sort the data based on the entry_position
        sorted_data = sorted(data.items(), key=lambda x: x[1]["entry_position"])

        for _, item in sorted_data:
            alarm_state = item.get('alarm', False)  # Debug log
            # print(f"Loading alarm state for {item['name']}: {alarm_state}")  # Debug log
            if any(word.lower() in self.filename_lower for word in self.watch_tab):
                self.add_table_row(name=item["name"], episode=item["episode"], date_time=item["datetime"],
                                   status=item["status"], alarm=item.get("alarm", False),
                                   snooze=item.get("snooze", False))
            else:
                self.add_table_row(name=item["name"], date_time=item["datetime"], status=item["status"],
                                   alarm=item.get("alarm", False),
                                   snooze=item.get("snooze", False))

    def save_data(self):
        if not self.is_sorting:
            data = {}
            for row in range(self.table.rowCount()):
                if any(word.lower() in self.filename_lower for word in self.watch_tab):
                    name_item = self.table.item(row, 0)
                    episode_item = self.table.item(row, 1)  # episode
                    datetime_item = self.table.item(row, 2)
                    status_widget = self.table.cellWidget(row, 4)
                    alarm_widget = self.table.cellWidget(row, 5)
                    snooze_widget = self.table.cellWidget(row, 6)
                else:
                    name_item = self.table.item(row, 0)
                    datetime_item = self.table.item(row, 1)
                    status_widget = self.table.cellWidget(row, 3)
                    alarm_widget = self.table.cellWidget(row, 4)
                    snooze_widget = self.table.cellWidget(row, 5)

                name = name_item.text() if name_item else ""
                datetime = datetime_item.text() if datetime_item else "N/A"
                status = status_widget.isChecked() if status_widget else False
                alarm = alarm_widget.isChecked() if alarm_widget else False
                snooze = snooze_widget.isChecked() if snooze_widget else False

                # Find the original key for this row
                original_key = self.find_original_key(row)

                if any(word.lower() in self.filename_lower for word in self.watch_tab):
                    episode = episode_item.text() if episode_item else ""

                    item = {
                        "entry_position": row,
                        "name": name,
                        "episode": episode,
                        "datetime": datetime,
                        "status": status,
                        "alarm": alarm,
                        "snooze": snooze
                    }
                else:
                    item = {
                        "entry_position": row,
                        "name": name,
                        "datetime": datetime,
                        "status": status,
                        "alarm": alarm,
                        "snooze": snooze,
                    }
                data[original_key] = item

            try:
                with open(self.filename, "w") as file:
                    json.dump(data, file)
            except IOError as e:
                pass
                #print(f"Error saving data: {e}")

    def delete_entry(self):
        if not self.is_sorting:
            current_row = self.table.currentRow()
            if current_row != -1:  # if a row is selected
                # Remove row from the table
                self.table.removeRow(current_row)

                # Load data from the file
                data = self.load_data_into_dict()

                # Find the key that corresponds to the current row
                key_to_delete = self.find_key_for_row(current_row, data)

                # Remove the entry from the data
                if key_to_delete in data:
                    del data[key_to_delete]

                # Update the entry positions
                for key, item in data.items():
                    if item["entry_position"] > current_row:
                        item["entry_position"] -= 1

                # Save the data to the file
                self.save_data_from_dict(data)

    def load_data_into_dict(self):
        try:
            with open(self.filename, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}
        return data

    def save_data_from_dict(self, data):
        try:
            if not self.is_sorting:
                with open(self.filename, "w") as file:
                    json.dump(data, file)
        except IOError as e:
            pass
            #print(f"Error saving data: {e}")

    # --------------------- Popup ------------------------
    def download_file(self, url, name):
        response = requests.get(url)
        if response.status_code == 200:
            # Ensure the "Torrent" folder exists
            loaded_folder_path = os.path.join(os.getcwd(), "Torrent")
            if not os.path.exists(loaded_folder_path):
                os.makedirs(loaded_folder_path)
            url_name = os.path.basename(url)
            full_name = name + '_' + url_name
            filename = os.path.join(loaded_folder_path, full_name)

            if not os.path.exists(filename):
                with open(filename, 'wb') as file:
                    file.write(response.content)
                QMessageBox.information(None, "Download", f"Downloaded: {full_name}")
                os.startfile(filename)  # Open the file with its default application
            else:
                os.startfile(filename)  # Open the file with its default application
                QMessageBox.information(None, "Already Downloaded", f"Exist as: {full_name}")

        else:
            QMessageBox.critical(None, "Error", f"Failed to download: {url}")

    def parse_and_create_buttons(self, url, layout):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
        except requests.RequestException as e:
            QMessageBox.critical(None, "Error", f"Failed to fetch XML from: {url}\n{e}")
            return

        try:
            xml_content = response.content
            root = ET.fromstring(xml_content)
            namespace = {'nyaa': 'https://nyaa.si/xmlns/nyaa'}
        except ET.ParseError as e:
            QMessageBox.critical(None, "Error", f"Failed to parse XML content\n{e}")
            return

        # Create a list to store all items
        items = []

        # Iterate through each item and store in the list
        for item in root.findall('./channel/item'):
            title = item.find('title').text
            link = item.find('link').text
            seeders = int(item.find('nyaa:seeders', namespace).text)
            size = item.find('nyaa:size', namespace).text
            items.append((title, link, seeders, size))

        # Sort items by number of seeders in descending order
        items.sort(key=lambda x: x[2], reverse=True)

        # Create a grid layout for the table-like display
        grid_layout = QGridLayout()

        # Create buttons for sorted items
        for index, (title, link, seeders, size) in enumerate(items):
            row = index // 3
            col = index % 3

            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)

            title_label = QLabel(title)
            title_label.setWordWrap(True)
            seeders_label = QLabel(f"Seeders: {seeders}")
            size_label = QLabel(f"Size: {size}")
            download_button = QPushButton("Download")

            download_button.clicked.connect(partial(self.download_file, link, title_label.text()))

            item_layout.addWidget(title_label)
            item_layout.addWidget(seeders_label)
            item_layout.addWidget(size_label)
            item_layout.addWidget(download_button)

            title_label.setStyleSheet("font-size: 16px; color: white;")
            seeders_label.setStyleSheet("color: skyblue;")
            size_label.setStyleSheet("color: red;")

            grid_layout.addWidget(item_widget, row, col)

        # Add the grid layout to the main layout
        layout.addLayout(grid_layout)

    def show_popup(self):
        current_row = self.table.currentRow()

        if current_row != -1:  # if a row is selected
            current_entry_name = self.table.item(current_row, 0).text()
            current_entry_episode = self.table.item(current_row, 1).text()
            episode_simplified = current_entry_episode.replace(" ", "").replace("-", "")

            self.popup_dialog = QDialog(self)
            # Set window flags to remove the '?' button
            self.popup_dialog.setWindowFlags(self.popup_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)

            self.popup_dialog.setWindowTitle("Input Name")
            self.popup_dialog.setFixedSize(1200, 500)  # Increased size to accommodate new content
            layout = QVBoxLayout(self.popup_dialog)

            # Create a horizontal layout for the input textbox and submit button
            input_layout = QHBoxLayout()

            self.input_textbox = QLineEdit()
            self.input_textbox.setText(current_entry_name)
            self.episode_textbox = QLineEdit()
            self.episode_textbox.setText(episode_simplified)

            input_layout.addWidget(self.input_textbox)
            input_layout.addWidget(self.episode_textbox)


            submit_button = QPushButton("All Providers")
            subsplease_button = QPushButton("Subsplease")
            input_layout.addWidget(submit_button)
            input_layout.addWidget(subsplease_button)

            # Add the horizontal layout to the main vertical layout
            layout.addLayout(input_layout)

            self.submitted_text_label = QLabel()
            layout.addWidget(self.submitted_text_label)

            # Create a scroll area for XML content
            # Create a scroll area for XML content
            self.scroll_area = QScrollArea()
            self.scroll_area.setWidgetResizable(True)
            layout.addWidget(self.scroll_area)


            submit_button.clicked.connect(self.display_input_text_in_popup)
            subsplease_button.clicked.connect(self.subplease_popup)

            self.popup_dialog.setLayout(layout)

            # Schedule the automatic click of the subsplease button
            QTimer.singleShot(0, subsplease_button.click)

            self.popup_dialog.exec_()

    def subplease_popup(self):
        self.display_input_text_in_popup(poster="subsplease")

    def display_input_text_in_popup(self, poster=""):
        input_text = self.input_textbox.text()
        episode_no = self.episode_textbox.text()
        self.submitted_text_label.setText(f"Submitted: {input_text} {episode_no}")
        print("called")

        # Create a new widget for scroll content
        new_scroll_content = QWidget()
        new_scroll_layout = QVBoxLayout(new_scroll_content)

        # Set the new widget as the scroll area's widget
        self.scroll_area.setWidget(new_scroll_content)

        if poster == "subsplease":
            if "S01" in episode_no:
                search_episode = episode_no.replace("S01", "").replace("E", " ")
            elif not "S01" in episode_no:
                search_episode = episode_no.replace("S0", "S").replace("E", " ")
            else:
                return

            xml_url = f'https://nyaa.si/?page=rss&q={input_text}+1080p+{search_episode}+subsplease&c=0_0&f=0'
        else:
            xml_url = f'https://nyaa.si/?page=rss&q={input_text}+1080p&c=0_0&f=0'

        # Fetch and parse XML to create buttons
        self.parse_and_create_buttons(xml_url, new_scroll_layout)

        # Update the scroll area
        self.scroll_area.setWidget(new_scroll_content)
        self.scroll_area.update()


    # --------------------- Alarm ------------------------
    def can_ring_alarm(self):
        global last_alarm_time
        if last_alarm_time is None or datetime.now() - last_alarm_time > COOLDOWN_PERIOD:
            return True
        return False

    def trigger_alarm(self, row):
        global last_alarm_time
        last_alarm_time = datetime.now()

        # print(f"Alarm triggered for row {row + 1}!")
        alarm_path = "alarm.mp3"
        alarm_duration = 5  # Duration in seconds
        self.play_mp3(alarm_path, alarm_duration)

        self.rung_alarms.add(row)  # Add this row to the set of rung alarms
        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            snooze_widget = self.table.cellWidget(row, 6)
        else:
            snooze_widget = self.table.cellWidget(row, 5)

        if snooze_widget.isChecked():
            QTimer.singleShot(SNOOZE_PERIOD.total_seconds() * 1000, lambda: self.check_snooze(row))

    def check_snooze(self, row):
        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            alarm_widget = self.table.cellWidget(row, 5)
            snooze_widget = self.table.cellWidget(row, 6)
        else:
            alarm_widget = self.table.cellWidget(row, 4)
            snooze_widget = self.table.cellWidget(row, 5)

        if alarm_widget.isChecked() and snooze_widget.isChecked():
            self.rung_alarms.discard(row)  # Remove this row from rung alarms to allow it to ring again
            self.trigger_alarm(row)

    def update_snooze_state(self, row, state):
        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            snooze_checkbox = self.table.cellWidget(row, 6)
        else:
            snooze_checkbox = self.table.cellWidget(row, 5)
        snooze_checkbox.setEnabled(state == Qt.Checked)
        if state != Qt.Checked:
            snooze_checkbox.setChecked(False)

    def on_alarm_changed(self, row, state):
        # print(f"Alarm state changed for row {row} to {state}")  # Debug log
        self.update_snooze_state(row, state)
        self.save_data()

    def on_snooze_changed(self, row, state):
        self.save_data()

    def play_mp3(self, file_path, duration):
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        self.stop_timer = QTimer()
        self.stop_timer.setSingleShot(True)
        self.stop_timer.timeout.connect(lambda: pygame.mixer.music.stop())
        self.stop_timer.start(duration * 1000)

    def stop_alarm(self, row):
        pygame.mixer.music.stop()  # Ensure the music is stopped
        if any(word.lower() in self.filename_lower for word in self.watch_tab):
            alarm_item = self.table.item(row, 5)
        else:
            alarm_item = self.table.item(row, 4)
        # print(f"Alarm stopped for row {row + 1}")

    def check_startup_alarms(self):
        current_time = datetime.now()
        for row in range(self.table.rowCount()):
            if any(word.lower() in self.filename_lower for word in self.watch_tab):
                date_time_item = self.table.item(row, 2)
                alarm_widget = self.table.cellWidget(row, 5)
            else:
                date_time_item = self.table.item(row, 1)
                alarm_widget = self.table.cellWidget(row, 4)

            if date_time_item and alarm_widget and alarm_widget.isChecked():
                date_time_str = date_time_item.text()
                if date_time_str != "N/A":
                    try:
                        date_time = datetime.strptime(date_time_str, "%d %b %Y %H:%M")
                        if date_time <= current_time:
                            self.trigger_alarm(row)
                            break  # Only trigger the first expired alarm found
                    except ValueError:
                        pass  # Skip invalid dates

    # --------------------- Move Up/Down ------------------------
    def move_row_up(self):
        if not self.is_sorting:
            current_row = self.table.currentRow()
            if current_row > 0:
                self.swap_rows(current_row, current_row - 1)
                self.table.setCurrentCell(current_row - 1, 0)
                self.update_entry_positions()

    def move_row_down(self):
        if not self.is_sorting:
            current_row = self.table.currentRow()
            if current_row < self.table.rowCount() - 1:
                self.swap_rows(current_row, current_row + 1)
                self.table.setCurrentCell(current_row + 1, 0)
                self.update_entry_positions()

    def swap_rows(self, row1, row2):
        # Load the data from the file
        data = self.load_data_into_dict()

        # Find the keys that correspond to the given rows
        key1 = next(key for key, item in data.items() if item["entry_position"] == row1)
        key2 = next(key for key, item in data.items() if item["entry_position"] == row2)

        # Swap the entry_position of the two rows
        data[key1]["entry_position"], data[key2]["entry_position"] = data[key2]["entry_position"], data[key1][
            "entry_position"]

        # Save the data to the file
        if not self.is_sorting:
            self.save_data_from_dict(data)

        # Reload the data into the table
        self.table.setRowCount(0)  # Clear the table
        self.load_data()  # Load the data

    # --------------------- Styling ------------------------
    def set_line_edit_style(self):
        line_edit_style = """
            QLineEdit {
                background-color: #2e2e2e;
                color: white;
                border: 1px solid #3e3e3e;
                padding: 2px;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #4e4e4e;
            }
        """
        return line_edit_style

    # --------------------- More ----------------------------
    def contextMenuEvent(self, event):
        if not self.is_sorting:
            context_menu = QMenu(self)

            # Delete option
            delete_action = context_menu.addAction("Delete Entry")
            delete_action.triggered.connect(self.delete_entry)

            if any(word.lower() in self.filename_lower for word in self.watch_tab):
                # popup option
                popup_action = context_menu.addAction("Show Torrent")
                popup_action.triggered.connect(self.show_popup)

            context_menu.exec_(event.globalPos())

    def update_countdown(self):
        global last_alarm_time
        current_time = datetime.now()

        for row in range(self.table.rowCount()):
            if any(word.lower() in self.filename_lower for word in self.watch_tab):
                date_time_item = self.table.item(row, 2)
                status_widget = self.table.cellWidget(row, 4)
                alarm_widget = self.table.cellWidget(row, 5)
            else:
                date_time_item = self.table.item(row, 1)
                status_widget = self.table.cellWidget(row, 3)
                alarm_widget = self.table.cellWidget(row, 4)

            if date_time_item is None or status_widget is None or alarm_widget is None:
                continue

            date_time_str = date_time_item.text()

            if date_time_str != "N/A":
                try:
                    date_time = datetime.strptime(date_time_str, "%d %b %Y %H:%M")
                    remaining = date_time - current_time
                    if status_widget.isChecked():
                        countdown = "Completed"
                    elif remaining.total_seconds() > 0:
                        countdown = f"{remaining.days} d : {remaining.seconds // 3600:02d} h : {(remaining.seconds % 3600) // 60:02d} m"
                    else:
                        countdown = "Overtime"
                        if alarm_widget.isChecked() and self.can_ring_alarm() and row not in self.rung_alarms:
                            self.trigger_alarm(row)
                except ValueError:
                    # print("Error")
                    # print(ValueError)
                    countdown = "Invalid Date"
            else:
                countdown = "N/A"

            if any(word.lower() in self.filename_lower for word in self.watch_tab):
                countdown_item = self.table.item(row, 3)
            else:
                countdown_item = self.table.item(row, 2)

            if countdown_item is None:
                countdown_item = QTableWidgetItem()
                if any(word.lower() in self.filename_lower for word in self.watch_tab):
                    self.table.setItem(row, 3, countdown_item)
                else:
                    self.table.setItem(row, 2, countdown_item)
            countdown_item.setText(countdown)

    def visibility_on(self):
        column_numbers = self.column_input.text().split(',')
        for column_number in column_numbers:
            try:
                column_number = int(column_number)
                if 0 <= column_number < self.table.columnCount():
                    self.table.setColumnHidden(column_number, False)
            except ValueError:
                pass  # Ignore invalid input

    def visibility_off(self):
        column_numbers = self.column_input.text().split(',')
        for column_number in column_numbers:
            try:
                column_number = int(column_number)
                if 0 <= column_number < self.table.columnCount():
                    self.table.setColumnHidden(column_number, True)
            except ValueError:
                pass  # Ignore invalid input

    def find_original_key(self, row):
        # This method finds the original key for a given row
        try:
            with open(self.filename, "r") as file:
                data = json.load(file)
            for key, item in data.items():
                if item["entry_position"] == row:
                    return key
        except FileNotFoundError:
            pass
        # If not found or file doesn't exist, create a new key
        return str(max(map(int, data.keys())) + 1 if data else 0)

    def find_key_for_row(self, row, data):
        sorted_data = sorted(data.items(), key=lambda x: x[1]['entry_position'])
        if 0 <= row < len(sorted_data):
            return sorted_data[row][0]
        return None


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle("ScheduleApp")
        self.setGeometry(400, 200, 1200, 500)

        if not os.path.exists("Data"):
            os.makedirs("Data")

        # Set application icon
        self.setWindowIcon(QIcon('app.ico'))

        # Central widget
        self.central_widget = ResizableFrame(self)
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(10, 10, 10, 10)

        # Custom title bar
        self.title_bar = CustomTitleBar(self)

        # Create a tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setUsesScrollButtons(True)
        self.set_tab_style()

        # context menu
        self.tab_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)

        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Add widgets to layout
        self.central_layout.addWidget(self.title_bar)
        self.central_layout.addWidget(self.tab_widget)

        self.setCentralWidget(self.central_widget)
        self.setStyleSheet(outer_layer_styling)

        self.load_tabs()

        # Create a system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # Create a context menu for the tray icon
        self.tray_menu = QMenu()
        restore_action = QAction("Restore", self)
        restore_action.triggered.connect(self.showNormal)
        self.tray_menu.addAction(restore_action)
        self.tray_icon.setContextMenu(self.tray_menu)

    def show_tab_context_menu(self, position):
        index = self.tab_widget.tabBar().tabAt(position)
        if index != -1:  # Ensure the right-click is on a tab
            context_menu = QMenu(self)
            rename_action = QAction("Rename", self)
            context_menu.addAction(rename_action)
            rename_action.triggered.connect(lambda: self.rename_current_tab(index))
            context_menu.exec_(self.tab_widget.mapToGlobal(position))

    # Rename current tab
    def rename_current_tab(self, index):
        current_index = index
        if current_index != -1:
            # Confirmation dialog
            current_tab_name = self.tab_widget.tabText(current_index)
            new_tab_name, ok = QInputDialog.getText(self, "Rename Tab", "New name:", QLineEdit.Normal, current_tab_name)
            if ok and new_tab_name:
                self.tab_widget.setTabText(current_index, new_tab_name)
                self.save_tabs()

    # --------------------- Data ------------------------
    def save_all_tabs_data(self):
        for index in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(index)
            if isinstance(tab, ScheduleApp):
                tab.save_data()

    def closeEvent(self, event):
        self.save_all_tabs_data()
        event.accept()

    def minimize_to_tray(self):
        self.hide()
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.tray_icon.hide()
            self.showNormal()

    def add_new_tab(self, tab_name, filename):
        new_tab = ScheduleApp(filename)
        self.tab_widget.addTab(new_tab, tab_name)
        self.save_tabs()

    def create_new_tab(self):
        tab_name, ok = QInputDialog.getText(self, 'Input Dialog', 'Enter tab name:')
        if ok and tab_name:  # if user clicked OK and the input is not empty
            first_word = tab_name.split()[0]
            current_time = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            filename = os.path.join("Data", f"{first_word}_{current_time}.json")
            self.add_new_tab(tab_name, filename)

    def save_tabs(self):
        tabs_info = []
        for index in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(index)
            tab_name = self.tab_widget.tabText(index)
            filename = widget.filename
            tabs_info.append({"name": tab_name, "filename": filename})

        current_tab_index = self.tab_widget.currentIndex()

        with open(CONFIG_FILE, "w") as file:
            json.dump({"tabs_info": tabs_info, "current_tab_index": current_tab_index}, file)

    def load_tabs(self):
        # print("Loading tabs")  # Debug log
        try:
            with open(CONFIG_FILE, "r") as file:
                data = json.load(file)
                if isinstance(data, dict) and "tabs_info" in data:
                    tabs_info = data["tabs_info"]
                    for tab_info in tabs_info:
                        # print(f"Adding tab: {tab_info['name']}, filename: {tab_info['filename']}")  # Debug log
                        self.add_new_tab(tab_info["name"], tab_info["filename"])
                    current_tab_index = data.get("current_tab_index", 0)
                    self.tab_widget.setCurrentIndex(current_tab_index)
                elif isinstance(data, list):
                    for tab_info in data:
                        # print(f"Adding tab: {tab_info['name']}, filename: {tab_info['filename']}")  # Debug log
                        self.add_new_tab(tab_info["name"], tab_info["filename"])
                    self.tab_widget.setCurrentIndex(0)
        except FileNotFoundError:
            # print("Config file not found, creating default tab")  # Debug log
            tab1_filename = os.path.join("Data", f"ScheduleApp_tab1.json")
            self.add_new_tab("Anime", tab1_filename)
        # print("Tab loading complete")  # Debug log

    def on_tab_changed(self, index):
        # print(f"Changing to tab {index}")  # Debug log
        # Save tabs whenever the active tab is changed
        self.save_tabs()

    def delete_current_tab(self):
        current_index = self.tab_widget.currentIndex()
        if current_index != -1:
            # Confirmation dialog
            reply = QMessageBox.question(self, 'Confirmation',
                                         "Delete the current tab?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                # Get the current tab widget
                current_widget = self.tab_widget.widget(current_index)
                # Remove the tab from the QTabWidget
                self.tab_widget.removeTab(current_index)
                # Delete the corresponding file
                if os.path.exists(current_widget.filename):
                    os.remove(current_widget.filename)
                # Update the tabs_config.json file
                self.save_tabs()


    # -------------- styling ----------------
    def set_tab_style(self):
        self.tab_widget.setStyleSheet(main_styling)


class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.initUI()

    def initUI(self):
        self.setFixedHeight(40)

        # Layouts
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Title label
        self.title_label = QLabel("Remember Me?")
        self.title_label.setStyleSheet("color: white; font-size: 16px; padding-left: 10px; background: none; border: none;")

        # Buttons
        self.new_tab_button = QPushButton("New Tab")
        self.new_tab_button.setFixedSize(120, 40)
        self.new_tab_button.clicked.connect(self.parent.create_new_tab)

        self.delete_tab_button = QPushButton("X Tab")
        self.delete_tab_button.setFixedSize(60, 40)
        self.delete_tab_button.clicked.connect(self.parent.delete_current_tab)

        self.minimize_button = QPushButton("—")
        self.minimize_button.setFixedSize(40, 40)
        self.minimize_button.clicked.connect(self.minimize)

        self.maximize_button = QPushButton("🗖")
        self.maximize_button.setFixedSize(40, 40)
        self.maximize_button.clicked.connect(self.maximize)

        self.close_button = QPushButton("❌")
        self.close_button.setFixedSize(40, 40)
        self.close_button.clicked.connect(self.close)

        # Add widgets to layout
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(self.delete_tab_button)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(self.new_tab_button)

        self.main_layout.addStretch()
        self.main_layout.addWidget(self.minimize_button)
        self.main_layout.addWidget(self.maximize_button)
        self.main_layout.addWidget(self.close_button)

        self.setLayout(self.main_layout)
        self.setStyleSheet(top_layout_styling)

        # Add a minimize to tray button
        self.minimize_to_tray_button = QPushButton("__")
        self.minimize_to_tray_button.setFixedSize(40, 40)
        self.minimize_to_tray_button.clicked.connect(self.parent.minimize_to_tray)

        # Add the minimize to tray button to the layout
        self.main_layout.addWidget(self.minimize_to_tray_button)

    def minimize(self):
        self.parent.showMinimized()

    def maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def mouseDoubleClickEvent(self, event):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def close(self):
        self.parent.save_all_tabs_data()
        self.parent.close()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
        self.oldPos = event.globalPos()


class ResizableFrame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.oldPos = None
        self.oldGeometry = None
        self.setMouseTracking(True)
        self.setStyleSheet(frame_styling_data)
        self.resize_margin = 5

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()
        self.oldGeometry = self.parent.geometry()

    def mouseMoveEvent(self, event):
        if self.oldPos:
            self.handleResize(event.globalPos())
        else:
            self.updateCursorShape(event.pos())

    def mouseReleaseEvent(self, event):
        self.oldPos = None

    def updateCursorShape(self, pos):
        if pos.x() < self.resize_margin and pos.y() < self.resize_margin:
            self.setCursor(Qt.SizeFDiagCursor)
        elif pos.x() > self.width() - self.resize_margin and pos.y() < self.resize_margin:
            self.setCursor(Qt.SizeBDiagCursor)
        elif pos.x() < self.resize_margin and pos.y() > self.height() - self.resize_margin:
            self.setCursor(Qt.SizeBDiagCursor)
        elif pos.x() > self.width() - self.resize_margin and pos.y() > self.height() - self.resize_margin:
            self.setCursor(Qt.SizeFDiagCursor)
        elif pos.x() < self.resize_margin or pos.x() > self.width() - self.resize_margin:
            self.setCursor(Qt.SizeHorCursor)
        elif pos.y() < self.resize_margin or pos.y() > self.height() - self.resize_margin:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def handleResize(self, globalPos):
        delta = globalPos - self.oldPos
        newGeometry = QRect(self.oldGeometry)

        if self.cursor().shape() in (Qt.SizeFDiagCursor, Qt.SizeBDiagCursor, Qt.SizeHorCursor):
            if self.oldPos.x() < self.width() / 2:
                newGeometry.setLeft(self.oldGeometry.left() + delta.x())
            else:
                newGeometry.setRight(self.oldGeometry.right() + delta.x())

        if self.cursor().shape() in (Qt.SizeFDiagCursor, Qt.SizeBDiagCursor, Qt.SizeVerCursor):
            if self.oldPos.y() < self.height() / 2:
                newGeometry.setTop(self.oldGeometry.top() + delta.y())
            else:
                newGeometry.setBottom(self.oldGeometry.bottom() + delta.y())

        self.parent.setGeometry(newGeometry)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec_())

