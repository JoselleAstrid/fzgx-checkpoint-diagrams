# Drawing checkpoint diagrams based on a spreadsheet's checkpoint data.
#
# Requirements:
# Python 3.6+ (for f-strings)
# pip install matplotlib (tested with 2.0.2)
# pip install PyQt5

import csv
import os
from pathlib import Path
import re
import sys

from matplotlib.colors import hsv_to_rgb, rgb2hex

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QWidget, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog, QApplication)

from diagram import Diagram


def parse_checkpoint_set(checkpoint_set_str):
    """Example: 0,2-5,177-193"""
    if checkpoint_set_str == '':
        return set()
    
    checkpoint_set = set()
    range_strs = checkpoint_set_str.split(',')
    for range_str in range_strs:
        range_str = range_str.strip()
        if '-' in range_str:
            # A range.
            low, high = range_str.split('-')
            # Limit the range within 0 and 999 to prevent silly
            # hangups from accidentally entering high numbers.
            low = max(int(low), 0)
            high = min(int(high), 999)
            checkpoint_set.update(range(low, high+1))
        else:
            # Just a number
            checkpoint_set.add(int(range_str))
            
    return checkpoint_set
    

def add_checkpoint_colors(checkpoints):
    # Different color for each line, and the colors should be
    # evenly spaced from say, red to blue to medium-green. Use HSV.
    # Assign the colors in order of checkpoint number.
    start_color = [0.33, 1.0, 0.7]
    end_color = [1.0, 1.0, 1.0]
    num_checkpoints = len(checkpoints)
    
    for index, c in enumerate(checkpoints):
        num = index + 1
        interpolation = num / num_checkpoints
        h = start_color[0] + \
            (end_color[0] - start_color[0])*interpolation
        s = start_color[1] + \
            (end_color[1] - start_color[1])*interpolation
        v = start_color[2] + \
            (end_color[2] - start_color[2])*interpolation
        checkpoints[index]['color'] = rgb2hex(hsv_to_rgb([h,s,v]))
        
    return checkpoints
    
    
class Status():
    """Some status variables shared between MainWidget and Diagram."""
    def __init__(self):
        self.course_code = None
        self.course_code_changed = False
        self.checkpoints = None
        self.data_path_points = None


class MainWidget(QWidget):
    
    def __init__(self):
        super().__init__()
        
        # Set to True for debugging, False otherwise (for responsiveness)
        self.synchronous_signals = True
        if self.synchronous_signals:
            self.signal_type = Qt.AutoConnection
        else:
            self.signal_type = Qt.QueuedConnection
            
        self.status = Status()
        
        self.init_ui()
        
        
    def init_ui(self):

        vbox = QVBoxLayout()
        
        char_width = 12
        char_height = 12

        hbox = QHBoxLayout()
        label = QLabel("Course code:")
        label.setToolTip(
            "Course to display checkpoints for.")
        hbox.addWidget(label)
        self.course_combo_box = QComboBox()
        self.course_combo_box.addItem("Select course")
        self.add_course_codes()
        self.course_combo_box.currentTextChanged.connect(
            self.on_course_code_change, self.signal_type)
        hbox.addWidget(self.course_combo_box)
        hbox.addStretch(1)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        label = QLabel("Extended checkpoints:")
        label.setToolTip(
            "Checkpoints whose lines should extend beyond the track"
            " boundaries."
            "\nYou can specify a series of checkpoint numbers and checkpoint ranges."
            "\nExample: 0,4-8,290,293-306")
        hbox.addWidget(label)
        self.extended_checkpoints_line_edit = QLineEdit()
        hbox.addWidget(self.extended_checkpoints_line_edit)
        
        label = QLabel("Extend length:")
        label.setToolTip(
            "Line length of extended checkpoint lines.")
        hbox.addWidget(label)
        self.extend_length_line_edit = QLineEdit()
        self.extend_length_line_edit.setFixedWidth(char_width*4)
        self.extend_length_line_edit.setText("2000")
        hbox.addWidget(self.extend_length_line_edit)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        label = QLabel("Hidden checkpoints:")
        label.setToolTip(
            "Checkpoints you don't want to display in the diagram."
            "\nHiding checkpoints can reduce clutter in areas with many"
            "\ncheckpoints close together, and it can improve"
            " panning responsiveness."
            "\nThe format is the same as the extended checkpoints.")
        hbox.addWidget(label)
        self.hidden_checkpoints_line_edit = QLineEdit()
        hbox.addWidget(self.hidden_checkpoints_line_edit)
        
        label = QLabel("Hidden numbers:")
        label.setToolTip(
            "Checkpoints where you want to display the line, but not the"
            " number."
            "\nThis is another option to strike a balance between"
            " information and clutter."
            "\nThe format is the same as the extended checkpoints.")
        hbox.addWidget(label)
        self.hidden_numbers_line_edit = QLineEdit()
        hbox.addWidget(self.hidden_numbers_line_edit)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        label = QLabel("Number distance from checkpoint:")
        label.setToolTip(
            "Distance between a checkpoint number and the side of the track.")
        hbox.addWidget(label)
        self.number_distance_line_edit = QLineEdit()
        self.number_distance_line_edit.setFixedWidth(char_width*3)
        self.number_distance_line_edit.setText("75")
        hbox.addWidget(self.number_distance_line_edit)
        
        label = QLabel("Number size:")
        label.setToolTip(
            "Font size of checkpoint numbers. This is also affected by DPI.")
        hbox.addWidget(label)
        self.number_size_line_edit = QLineEdit()
        self.number_size_line_edit.setFixedWidth(char_width*3)
        self.number_size_line_edit.setText("14")
        hbox.addWidget(self.number_size_line_edit)
        
        label = QLabel("DPI:")
        label.setToolTip(
            "Dots per inch to use during drawing."
            "\nThis affects number size, line thickness, and circle size.")
        hbox.addWidget(label)
        self.dpi_line_edit = QLineEdit()
        self.dpi_line_edit.setFixedWidth(char_width*3)
        self.dpi_line_edit.setText("100")
        hbox.addWidget(self.dpi_line_edit)
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        
        hbox = QHBoxLayout()
        label = QLabel("Axes:")
        label.setToolTip(
            "In-game coordinate axes to display in the diagram."
            "\nZ points backward from the finish line. X points right from the finish line. Y points up.")
        hbox.addWidget(label)
        axis_choices = ['x', 'y', 'z', '-x', '-y', '-z']
        self.axis_1_combo_box = QComboBox()
        self.axis_2_combo_box = QComboBox()
        for axis_choice in axis_choices:
            self.axis_1_combo_box.addItem(axis_choice)
            self.axis_2_combo_box.addItem(axis_choice)
        self.axis_1_combo_box.setCurrentText('x')
        self.axis_2_combo_box.setCurrentText('-z')
        hbox.addWidget(self.axis_1_combo_box)
        hbox.addWidget(self.axis_2_combo_box)
        hbox.addStretch(1)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        label = QLabel("Path from data files:")
        label.setToolTip(
            "Some courses have extra data files which define paths."
            "\nHere you can select a path to display on the diagram.")
        hbox.addWidget(label)
        self.data_path_combo_box = QComboBox()
        self.data_path_combo_box.setFixedWidth(250)
        hbox.addWidget(self.data_path_combo_box)
        
        self.crossings_checkbox = QCheckBox("Show crossing data")
        self.crossings_checkbox.setToolTip(
            "Courses with wide-crossing or precise-crossing strategies have"
            "\nsuccess and failure data in the file Crossings.csv."
            "\nYou can tick this checkbox to display the crossings data.")
        hbox.addWidget(self.crossings_checkbox)
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        
        hbox = QHBoxLayout()
        self.update_button = QPushButton("Update diagram")
        self.update_button.setFixedWidth(120)
        self.update_button.clicked.connect(
            self.update_diagram, self.signal_type)
        hbox.addWidget(self.update_button)
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("QLabel { color: red; }")
        self.error_label.setFixedHeight(char_height)
        vbox.addWidget(self.error_label)
        
        self.coords_label = QLabel("")
        self.coords_label.setFixedHeight(char_height)
        self.diagram = Diagram(self.status, self.coords_label)
        vbox.addWidget(self.diagram.canvas)
        vbox.addWidget(self.coords_label)
        
        hbox = QHBoxLayout()
        self.save_button = QPushButton("Save image")
        self.save_button.setFixedWidth(120)
        self.save_button.clicked.connect(
            self.on_save_button_click, self.signal_type)
        hbox.addWidget(self.save_button)
        
        label = QLabel("DPI:")
        label.setToolTip(
            "Dots per inch to use for saving. You can use this to adjust the"
            "\nresolution of the saved image."
            "\nThe relative scale of things will be the same as the diagram.")
        hbox.addWidget(label)
        self.save_dpi_line_edit = QLineEdit()
        self.save_dpi_line_edit.setFixedWidth(char_width*3)
        self.save_dpi_line_edit.setText("100")
        hbox.addWidget(self.save_dpi_line_edit)
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        
        # TODO: Rectangle select tool
        
        self.save_error_label = QLabel("")
        self.save_error_label.setStyleSheet("QLabel { color: red; }")
        self.save_error_label.setFixedHeight(char_height)
        vbox.addWidget(self.save_error_label)
        
        self.setLayout(vbox)
        
        self.find_courses_with_crossing_data()
        self.on_course_code_change()
        self.update_diagram()
        
        self.setWindowTitle("F-Zero GX checkpoint diagrams")
        self.show()
        
        # Center the window on the active screen
        # (where the mouse pointer is currently located).
        # https://stackoverflow.com/a/20244839/
        #
        # This must be done after self.show(), or the window size will be
        # inaccurate and we won't center it properly.
        frame_geometry = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(
            QApplication.desktop().cursor().pos())
        center_point = (
            QApplication.desktop().screenGeometry(screen).center())
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
    
    
    def update_diagram_fields(self):
        
        try:
            self.status.number_distance = float(
                self.number_distance_line_edit.text())
        except ValueError:
            self.error_label.setText("Number distance must be a number.")
            
        try:
            self.status.number_size = float(
                self.number_size_line_edit.text())
        except ValueError:
            self.error_label.setText("Number size must be a number.")
        
        try:
            self.status.extended_checkpoints = parse_checkpoint_set(
                self.extended_checkpoints_line_edit.text())
        except ValueError:
            self.error_label.setText(
                "Extended checkpoints are not in the correct format.")
            
        try:
            self.status.extend_length = float(
                self.extend_length_line_edit.text())
        except ValueError:
            self.error_label.setText("Extend length must be a number.")
            
        try:
            self.status.hidden_checkpoints = parse_checkpoint_set(
                self.hidden_checkpoints_line_edit.text())
        except ValueError:
            self.error_label.setText(
                "Hidden checkpoints are not in the correct format.")
            
        try:
            self.status.hidden_numbers = parse_checkpoint_set(
                self.hidden_numbers_line_edit.text())
        except ValueError:
            self.error_label.setText(
                "Hidden numbers are not in the correct format.")
            
        self.status.axis_1 = self.axis_1_combo_box.currentText()
        self.status.axis_2 = self.axis_2_combo_box.currentText()
        
        data_path_text = self.data_path_combo_box.currentText()
        if data_path_text in ["No path selected", "(None)"]:
            self.status.data_path_name = None
        else:
            self.status.data_path_name = data_path_text
            
        try:
            self.status.dpi = float(self.dpi_line_edit.text())
        except ValueError:
            self.error_label.setText("DPI must be a number.")
        
        
    def update_diagram(self):
        self.error_label.setText("")
        
        self.update_diagram_fields()
        if self.status.course_code_changed and self.status.course_code:
            self.read_checkpoints()
            
        if self.status.data_path_name:
            self.read_data_path()
        else:
            self.status.data_path_points = None
            
        if (self.crossings_checkbox.isEnabled() and
           self.crossings_checkbox.isChecked()):
            self.read_crossing_data()
        else:
            self.status.crossing_data = None
            
        self.diagram.refresh()
        
        self.status.course_code_changed = False
        
        
    def add_course_codes(self):
        # Look in /data for csv files whose names consists of all capital
        # letters and numbers. For example: MCTR, SOSS, CH3
        data_filenames = os.listdir(Path('data'))
        course_data_file_regex = re.compile('([A-Z0-9]+)\.csv')
        
        for filename in data_filenames:
            match = re.fullmatch(course_data_file_regex, filename)
            if match:
                course_code = match.groups()[0]
                self.course_combo_box.addItem(course_code)
                
                
    def read_checkpoints(self):
        
        csv_filepath = Path('data', f'{self.status.course_code}.csv')
        try:
            csv_file = open(csv_filepath, 'r')
        except IOError as e:
            self.error_label.setText(
                f"There was a problem trying to read {csv_filepath}: {e}")
            return
        csv_reader = csv.reader(csv_file)
        
        # Get the column names (first row). Convert to lowercase and replace
        # spaces with underscores.
        column_names = next(csv_reader)
        dict_labels = [n.lower().replace(' ', '_') for n in column_names]
        
        # Get checkpoint data from the rest of the rows.
        # Ignore empty rows.
        self.status.checkpoints = [
            dict(zip(dict_labels, row)) for row in csv_reader
            if len(row) > 0 and len(row[0]) > 0]
            
        # Convert stuff to ints/floats as needed.
        for c in self.status.checkpoints:
            c['checkpoint'] = int(c['checkpoint'])
            c['center_x'] = float(c['center_x'])
            c['center_y'] = float(c['center_y'])
            c['center_z'] = float(c['center_z'])
            c['right_x'] = float(c['right_x'])
            c['right_y'] = float(c['right_y'])
            c['right_z'] = float(c['right_z'])
            
            # Take care of the track width
            if 'true_width' in c and c['true_width']:
                # This is only specified for pipes, which make the normal
                # track width stat inaccurate
                c['track_width'] = float(c['true_width'])
            elif 'track_width' in c and c['track_width']:
                # Use the normal track width stat if true width isn't specified
                c['track_width'] = float(c['track_width'])
            else:
                # If both are unspecified, use a default
                c['track_width'] = 90.0
        
        # Associate each checkpoint with a color.
        self.status.checkpoints = add_checkpoint_colors(
            self.status.checkpoints)
        
        
    def read_data_path(self):
        csv_filepath = Path(
            'data',
            f'{self.status.course_code}_{self.status.data_path_name}.csv')
        try:
            csv_file = open(csv_filepath, 'r')
        except IOError as e:
            self.error_label.setText(
                f"There was a problem trying to read {csv_filepath}: {e}")
            return
        csv_reader = csv.reader(csv_file)
        
        # Get the column names (first row). Convert to lowercase and replace
        # spaces with underscores.
        column_names = next(csv_reader)
        dict_labels = [n.lower().replace(' ', '_') for n in column_names]
        
        # Get path data from the rest of the rows.
        # Ignore empty rows.
        self.status.data_path_points = [
            dict(zip(dict_labels, row)) for row in csv_reader
            if len(row) > 0 and len(row[0]) > 0]
            
        # Convert stuff to ints/floats as needed.
        for p in self.status.data_path_points:
            p['x'] = float(p['x'])
            p['y'] = float(p['y'])
            p['z'] = float(p['z'])
            
            
    def find_courses_with_crossing_data(self):
        csv_filepath = Path('data', 'Crossings.csv')
        try:
            csv_file = open(csv_filepath, 'r')
        except IOError as e:
            self.error_label.setText(
                f"There was a problem trying to read {csv_filepath}: {e}")
            self.courses_with_crossing_data = []
            return
        csv_reader = csv.reader(csv_file)
        
        # Get the column names (first row). Convert to lowercase and replace
        # spaces with underscores.
        column_names = next(csv_reader)
        dict_labels = [n.lower().replace(' ', '_') for n in column_names]
        
        # Get crossing data from the rest of the rows.
        # Ignore empty rows.
        crossings = [
            dict(zip(dict_labels, row)) for row in csv_reader
            if len(row) > 0 and len(row[0]) > 0]
        
        # Build a set of the tracks with crossing data.
        self.courses_with_crossing_data = set(c['track'] for c in crossings)
        
        
    def read_crossing_data(self):
        csv_filepath = Path('data', 'Crossings.csv')
        try:
            csv_file = open(csv_filepath, 'r')
        except IOError as e:
            self.error_label.setText(
                f"There was a problem trying to read {csv_filepath}: {e}")
            self.status.crossing_data = None
            return
        csv_reader = csv.reader(csv_file)
        
        # Get the column names (first row). Convert to lowercase and replace
        # spaces with underscores.
        column_names = next(csv_reader)
        dict_labels = [n.lower().replace(' ', '_') for n in column_names]
        
        # Get crossing data from the rest of the rows.
        # Ignore empty rows.
        self.status.crossing_data = [
            dict(zip(dict_labels, row)) for row in csv_reader
            if len(row) > 0 and len(row[0]) > 0]
        # Filter so that we only have data for the current course.
        self.status.crossing_data = [
            c for c in self.status.crossing_data
            if c['track'] == self.status.course_code]
            
        # Convert stuff to ints/floats as needed.
        for c in self.status.crossing_data:
            c['x1'] = float(c['x1'])
            c['x2'] = float(c['x2'])
            c['y1'] = float(c['y1'])
            c['y2'] = float(c['y2'])
            c['z1'] = float(c['z1'])
            c['z2'] = float(c['z2'])
        
        
    def on_course_code_change(self):
        
        course_code_text = self.course_combo_box.currentText()
        if course_code_text == "Select course":
            self.status.course_code = None
        else:
            self.status.course_code = course_code_text
            
        # Add path choices to data_path_combo_box according to what's
        # available for the course
        self.data_path_combo_box.clear()
        data_path_names = []
        
        if self.status.course_code:
            # If the course code is MCTR, we expect data files like
            # MCTR_skip_success.csv
            data_filenames = os.listdir(Path('data'))
            path_data_file_regex = re.compile(
                f'{self.status.course_code}_([A-Za-z0-9_]+)\.csv')
            
            for filename in data_filenames:
                match = re.fullmatch(path_data_file_regex, filename)
                if match:
                    data_path_name = match.groups()[0]
                    data_path_names.append(data_path_name)
        
        if data_path_names:
            self.data_path_combo_box.addItem("No path selected")
            self.data_path_combo_box.setCurrentText("No path selected")
            for data_path_name in data_path_names:
                self.data_path_combo_box.addItem(data_path_name)
        else:
            self.data_path_combo_box.addItem("(None)")
            self.data_path_combo_box.setCurrentText("(None)")
            
        has_crossing_data = (
            self.status.course_code in self.courses_with_crossing_data)
        self.crossings_checkbox.setEnabled(has_crossing_data)
            
        self.status.course_code_changed = True
        
        
    def on_save_button_click(self):
        self.save_error_label.setText("")
        
        try:
            self.status.save_dpi = float(self.save_dpi_line_edit.text())
        except ValueError:
            self.save_error_label.setText("Save DPI must be a number.")
            return
            
        dialog = QFileDialog(self)
        
        filepath, _ = dialog.getSaveFileName(
            self, caption="Choose location to save image to",
            filter="PNG images (*.png)")
        if not filepath:
            # The user cancelled the dialog or something
            return
        self.diagram.save(filepath)


if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    widget = MainWidget()
    sys.exit(app.exec_())

