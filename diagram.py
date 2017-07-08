import math

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import hsv_to_rgb, rgb2hex
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QRubberBand

    
# Coordinates
def x_coord(lateral_offset, check):
    return check['center_x'] + lateral_offset*check['right_x']
def y_coord(lateral_offset, check):
    return check['center_y'] + lateral_offset*check['right_y']
def z_coord(lateral_offset, check):
    return check['center_z'] + lateral_offset*check['right_z']
def neg_x_coord(lateral_offset, check):
    return -(check['center_x'] + lateral_offset*check['right_x'])
def neg_y_coord(lateral_offset, check):
    return -(check['center_y'] + lateral_offset*check['right_y'])
def neg_z_coord(lateral_offset, check):
    return -(check['center_z'] + lateral_offset*check['right_z'])
def get_checkpoint_position_function(coord_str):
    if coord_str == 'x':
        return x_coord
    if coord_str == 'y':
        return y_coord
    if coord_str == 'z':
        return z_coord
    if coord_str == '-x':
        return neg_x_coord
    if coord_str == '-y':
        return neg_y_coord
    if coord_str == '-z':
        return neg_z_coord
def get_point_position_function(coord_str):
    if coord_str == 'x':
        return lambda p: p['x']
    if coord_str == 'y':
        return lambda p: p['y']
    if coord_str == 'z':
        return lambda p: p['z']
    if coord_str == '-x':
        return lambda p: -p['x']
    if coord_str == '-y':
        return lambda p: -p['y']
    if coord_str == '-z':
        return lambda p: -p['z']


class Diagram():
    
    zoom_factor = 1.2
    
    def __init__(self, status, coords_label):
        
        self.status = status
        self.coords_label = coords_label
        
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumWidth(200)
        self.canvas.setMinimumHeight(200)
        self.previous_dpi = self.figure.get_dpi()
        # Add axes that fill the figure (while maintaining aspect ratio)
        # https://stackoverflow.com/a/6377406/
        self.axes = self.figure.add_axes([0, 0, 1, 1])
        
        # Make it possible to focus on the canvas by clicking on it.
        # This allows the canvas to capture keypresses.
        # https://stackoverflow.com/questions/22043549/
        # http://doc.qt.io/qt-5/qt.html#FocusPolicy-enum
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        
        self.canvas.setCursor(Qt.OpenHandCursor)
        self.drag_position = None
        
        self.rectangle_select_interaction = None
        self.rect_rubberband = QRubberBand(QRubberBand.Rectangle, self.canvas)
        
        self.canvas.mpl_connect(
            'button_press_event', self.button_press_event)
        self.canvas.mpl_connect(
            'button_release_event', self.button_release_event)
        self.canvas.mpl_connect(
            'motion_notify_event', self.motion_notify_event)
        self.canvas.mpl_connect(
            'key_press_event', self.key_press_event)
        self.canvas.mpl_connect(
            'scroll_event', self.scroll_event)
        self.canvas.mpl_connect(
            'resize_event', self.resize_event)
    
    def refresh(self):
        
        if not self.status.course_code:
            return
            
        old_axes_xlim = self.axes.get_xlim()
        old_axes_ylim = self.axes.get_ylim()
        
        self.axes.clear()
        self.draw_checkpoints()
        self.setup_figure()
        
        # If the course is the same as the last refresh, we'd like to keep the
        # user's current pan and zoom positions.
        # draw_checkpoints() calls plot() which seems to unavoidably change
        # the limits, so we must revert the limits to before that call.
        if not self.status.course_code_changed:
            self.axes.set_xlim(old_axes_xlim)
            self.axes.set_ylim(old_axes_ylim)
        
        self.canvas.draw()
        
        self.deactivate_rectangle_select()
        
    def canvas_width(self):
        return self.canvas.get_width_height()[0]
    def canvas_height(self):
        return self.canvas.get_width_height()[1]
            
    def convert_coords_canvas_to_game(self, x, y):
        xlim = self.axes.get_xlim()
        ylim = self.axes.get_ylim()
        canvas_width, canvas_height = self.canvas.get_width_height()
        return (
            xlim[0] + (xlim[1] - xlim[0])*(x / canvas_width),
            ylim[0] + (ylim[1] - ylim[0])*(y / canvas_height))
    
    def button_press_event(self, event):
        # Mouse button press
        self.rectangle_select_button_press_event(event)
        
        if not self.rectangle_select_interaction:
            # Start pan
            #print(f'Button press: {event.x}, {event.y}, {event.button}')
            self.drag_position = (event.x, event.y)
            self.canvas.setCursor(Qt.ClosedHandCursor)
        
    def button_release_event(self, event):
        # Mouse button release
        self.rectangle_select_button_release_event(event)
            
        # End pan
        #print(f'Button release: {event.x}, {event.y}, {event.button}')
        self.drag_position = None
        self.canvas.setCursor(Qt.OpenHandCursor)
        
    def motion_notify_event(self, event):
        # Mouse motion
        self.rectangle_select_motion_notify_event(event)
            
        # If mouse button pressed, pan the figure
        #print(f'Motion: {event.x}, {event.y}')
        if self.drag_position:
            self.pan(
                event.x - self.drag_position[0],
                event.y - self.drag_position[1])
            self.drag_position = (event.x, event.y)
            
        # Update coordinates display
        coords = self.convert_coords_canvas_to_game(event.x, event.y)
        # Instead of "-z = 490.73", display "z = -490.73"
        if self.status.axis_1.startswith('-'):
            coord_1_str = f'{self.status.axis_1[1:]} = {-coords[0]:.3f}'
        else:
            coord_1_str = f'{self.status.axis_1} = {coords[0]:.3f}'
        if self.status.axis_2.startswith('-'):
            coord_2_str = f'{self.status.axis_2[1:]} = {-coords[1]:.3f}'
        else:
            coord_2_str = f'{self.status.axis_2} = {coords[1]:.3f}'
        
        self.coords_label.setText(f'{coord_1_str}, {coord_2_str}')
            
    def scroll_event(self, event):
        # Mousewheel scrolling
        #print(f'Scroll: {event.x}, {event.y}, {event.step}')
        if event.step > 0:
            # Scroll up -> zoom in on the current mouse position
            self.zoom_in(event.x, event.y)
        else:
            # Scroll down -> zoom out from the current mouse position
            self.zoom_out(event.x, event.y)
            
    def key_press_event(self, event):
        #print(f'Key press: {event.key}')
        if event.key == 'up':
            # Up arrow -> zoom in on the diagram center
            canvas_width, canvas_height = self.canvas.get_width_height()
            self.zoom_in(canvas_width / 2, canvas_height / 2)
        elif event.key == 'down':
            # Down arrow -> zoom out from the diagram center
            canvas_width, canvas_height = self.canvas.get_width_height()
            self.zoom_out(canvas_width / 2, canvas_height / 2)
            
    def resize_event(self, event):
        # Canvas is resized
        # Note: This does not get called if the canvas size changes due to
        # a diagram DPI update. It only gets called when a window resize
        # triggers a canvas resize.
        #print(f'Resize: {event.width}, {event.height}')
        
        # Fix aspect ratio of the diagram.
        axes_hmin, axes_hmax = self.axes.get_xlim()
        axes_vmin, axes_vmax = self.axes.get_ylim()
        hrange = axes_hmax - axes_hmin
        vrange = axes_vmax - axes_vmin
        
        if hrange / vrange >= event.width / event.height:
            # Add extra vertical range to maintain aspect ratio
            target_vrange = hrange*(event.height / event.width)
            extra_vspace_one_side = (target_vrange - vrange) / 2
            axes_vmin = axes_vmin - extra_vspace_one_side
            axes_vmax = axes_vmax + extra_vspace_one_side
        else:
            # Add extra horizontal range to maintain aspect ratio
            target_hrange = vrange*(event.width / event.height)
            extra_hspace_one_side = (target_hrange - hrange) / 2
            axes_hmin = axes_hmin - extra_hspace_one_side
            axes_hmax = axes_hmax + extra_hspace_one_side
            
        # Apply the new axes limits to fix the aspect ratio
        self.axes.set_xlim(axes_hmin, axes_hmax)
        self.axes.set_ylim(axes_vmin, axes_vmax)
        
        # Rectangle can get wonky after a canvas resize, so just erase it
        self.deactivate_rectangle_select()
        
            
    def pan(self, change_x, change_y):
        canvas_width, canvas_height = self.canvas.get_width_height()
        
        xlim = self.axes.get_xlim()
        x_coord_ratio_game_to_canvas = (xlim[1] - xlim[0]) / canvas_width
        self.axes.set_xlim(
            xlim[0] - change_x*x_coord_ratio_game_to_canvas,
            xlim[1] - change_x*x_coord_ratio_game_to_canvas)
        
        ylim = self.axes.get_ylim()
        y_coord_ratio_game_to_canvas = (ylim[1] - ylim[0]) / canvas_height
        self.axes.set_ylim(
            ylim[0] - change_y*y_coord_ratio_game_to_canvas,
            ylim[1] - change_y*y_coord_ratio_game_to_canvas)
        
        self.canvas.draw()
        
        # print(f"Pan: {change_x}, {change_y}")
        # print(f"xlim: {self.axes.get_xlim()}")
        # print(f"ylim: {self.axes.get_ylim()}")
        
    def zoom(self, x, y, direction_is_inward):
        """Zoom in/out, centered on the current mouse position"""
        game_coords = self.convert_coords_canvas_to_game(x, y)
        
        if direction_is_inward:
            # Zoom in
            space_stretch_factor = 1 / self.zoom_factor
        else:
            # Zoom out
            space_stretch_factor = self.zoom_factor
        
        xlim = self.axes.get_xlim()
        self.axes.set_xlim(
            game_coords[0] - (game_coords[0] - xlim[0])*space_stretch_factor,
            game_coords[0] - (game_coords[0] - xlim[1])*space_stretch_factor)
        
        ylim = self.axes.get_ylim()
        self.axes.set_ylim(
            game_coords[1] - (game_coords[1] - ylim[0])*space_stretch_factor,
            game_coords[1] - (game_coords[1] - ylim[1])*space_stretch_factor)
        
        self.canvas.draw()
        
    def zoom_in(self, x, y):
        self.zoom(x, y, True)
        
    def zoom_out(self, x, y):
        self.zoom(x, y, False)
        
    def activate_rectangle_select(self):
        self.rect_rubberband.setGeometry(0, 0, 0, 0)
        self.rect_rubberband.show()
        self.save_rectangle = None
        self.canvas.setCursor(Qt.CrossCursor)
        self.rectangle_select_interaction = 'ready'
        
    def deactivate_rectangle_select(self):
        self.rect_rubberband.hide()
        self.save_rectangle = None
        self.canvas.setCursor(Qt.OpenHandCursor)
        self.rectangle_select_interaction = None
        
    def rectangle_select_button_press_event(self, event):
        # Mouse button press
        if self.rectangle_select_interaction == 'ready':
            # Start drawing rectangle.
            # Rectangle dimensions have opposite direction y from
            # event/canvas dimensions
            self.rectangle_select_origin_x = event.x
            self.rectangle_select_origin_y = event.y
            self.rectangle_select_interaction = 'drawing'
        else:
            self.deactivate_rectangle_select()
            
    def rectangle_select_motion_notify_event(self, event):
        # Mouse motion
        if self.rectangle_select_interaction == 'drawing':
            # Change the rectangle shape according to the mouse position.
            canvas_width, canvas_height = self.canvas.get_width_height()
            
            # If the mouse is outside of the canvas boundary, snap the
            # rectangle to the boundary
            event_x_bounded = event.x
            event_x_bounded = max(event_x_bounded, 0)
            event_x_bounded = min(event_x_bounded, canvas_width)
            event_y_bounded = event.y
            event_y_bounded = max(event_y_bounded, 0)
            event_y_bounded = min(event_y_bounded, canvas_height)
            
            # 1. Rect rubberband dimensions have opposite direction y from
            # event/canvas dimensions, so need to do canvas height minus
            # event y
            # 2. setGeometry() only works when the sizes are positive, so need
            # to start with the lower coordinates and ensure positive sizes
            self.rect_rubberband.setGeometry(
                min(self.rectangle_select_origin_x, event_x_bounded),
                min(
                    canvas_height - self.rectangle_select_origin_y,
                    canvas_height - event_y_bounded),
                abs(self.rectangle_select_origin_x - event_x_bounded),
                abs(self.rectangle_select_origin_y - event_y_bounded))
        
    def rectangle_select_button_release_event(self, event):
        # Mouse button release
        if self.rectangle_select_interaction == 'drawing':
            # Finish the rectangle.
            
            # If the mouse is outside of the canvas boundary, snap the
            # rectangle to the boundary
            canvas_width, canvas_height = self.canvas.get_width_height()
            event_x_bounded = event.x
            event_x_bounded = max(event_x_bounded, 0)
            event_x_bounded = min(event_x_bounded, canvas_width)
            event_y_bounded = event.y
            event_y_bounded = max(event_y_bounded, 0)
            event_y_bounded = min(event_y_bounded, canvas_height)
            
            self.save_rectangle = (
                (self.rectangle_select_origin_x,
                 self.rectangle_select_origin_y),
                (event_x_bounded, event_y_bounded))
            self.rectangle_select_interaction = None
            #print(self.save_rectangle)
        
    def draw_checkpoints(self):
        
        # Prepare to plot checkpoints/paths on the chosen axes. The first will 
        # appear as the horizontal axis, and the second will appear as the 
        # vertical axis on the figure.
        haxis = get_checkpoint_position_function(self.status.axis_1)
        vaxis = get_checkpoint_position_function(self.status.axis_2)
        haxis_point = get_point_position_function(self.status.axis_1)
        vaxis_point = get_point_position_function(self.status.axis_2)
        
        # Track the farthest values on either axis so we can compute the
        # display boundaries.
        self.data_hmin = math.inf
        self.data_hmax = -math.inf
        self.data_vmin = math.inf
        self.data_vmax = -math.inf
        
        # Draw the checkpoints.
        for c in self.status.checkpoints:
            
            if c['checkpoint'] in self.status.hidden_checkpoints:
                continue
            
            track_width = c['track_width']
            half_track_width = track_width/2
            
            # Draw markers on the checkpoint's center, and on both edges 
            # of the track directly lateral from the checkpoint.
            # http://stackoverflow.com/a/8409110
            haxis_coords = [
                haxis(-half_track_width, c),
                haxis(0, c),
                haxis(half_track_width, c)]
            vaxis_coords = [
                vaxis(-half_track_width, c),
                vaxis(0, c),
                vaxis(half_track_width, c)]
            
            self.axes.plot(
                haxis_coords, vaxis_coords, color=c['color'], marker='o')
            
            base_3d_length = half_track_width
            base_plane_length = math.sqrt(
                (haxis_coords[1]-haxis_coords[0])**2
                + (vaxis_coords[1]-vaxis_coords[0])**2)
            
            if c['checkpoint'] in self.status.extended_checkpoints:
                # Draw an extended line for the checkpoint,
                # with equal line length on both sides.
                # The line length is defined in the diagram's coord plane.
                extended_plane_length = self.status.extend_length
                if base_plane_length > 0:
                    extended_3d_length = (extended_plane_length
                        * (base_3d_length / base_plane_length))
                else:
                    # In this case the line is perpendicular to the
                    # diagram's plane.
                    extended_3d_length = 0
                
                extend_haxis_coords = [
                    haxis(-extended_3d_length, c),
                    haxis(extended_3d_length, c)]
                extend_vaxis_coords = [
                    vaxis(-extended_3d_length, c),
                    vaxis(extended_3d_length, c)]
                self.axes.plot(
                    extend_haxis_coords, extend_vaxis_coords, c['color'])
            
            # Label the checkpoint with its checkpoint number.
            # Position the label a certain distance away from one end
            # of the (non-extended) checkpoint line.
            # Negative distances put the number on the other side.
            # Again, make sure to define distance in the diagram's coord plane.
            if c['checkpoint'] not in self.status.hidden_numbers:
                if self.status.number_distance > 0:
                    label_distance = (
                        self.status.number_distance + half_track_width)
                    side_track_is_on = 'left'
                else:
                    label_distance = (
                        self.status.number_distance - half_track_width)
                    side_track_is_on = 'right'
                    
                if base_plane_length > 0 or base_plane_length < 0:
                    label_3d_distance = (label_distance
                        * (base_3d_length / base_plane_length))
                else:
                    label_3d_distance = 0
                label_coords = (
                    haxis(label_3d_distance, c), vaxis(label_3d_distance, c))
                self.axes.text(
                    label_coords[0], label_coords[1],
                    # Ensure the checkpoint number on the plot
                    # shows no decimal places
                    int(c['checkpoint']),
                    fontdict=dict(
                        # Number color should match the line color
                        color=c['color'],
                        # Font size
                        size=self.status.number_size,
                        # Base the position on the side of the text, not the
                        # center. This way, 1 digit and 3 digit numbers
                        # are the same distance from the side of the track.
                        # And it generally reduces instances where the text is
                        # struck-through by extended checkpoint lines.
                        horizontalalignment=side_track_is_on,
                        # Put the bottom of the text at this position.
                        # This generally reduces instances where the text is
                        # struck-through by extended checkpoint lines.
                        verticalalignment='bottom',
                    ),
                )
                
                # Update coordinate boundaries to ensure they contain the
                # checkpoint numbers.
                self.data_hmin = min([self.data_hmin, label_coords[0]])
                self.data_hmax = max([self.data_hmax, label_coords[0]])
                self.data_vmin = min([self.data_vmin, label_coords[1]])
                self.data_vmax = max([self.data_vmax, label_coords[1]])
            
            # Update coordinate boundaries to ensure they contain the
            # (non-extended) checkpoint lines.
            self.data_hmin = min([self.data_hmin] + haxis_coords)
            self.data_hmax = max([self.data_hmax] + haxis_coords)
            self.data_vmin = min([self.data_vmin] + vaxis_coords)
            self.data_vmax = max([self.data_vmax] + vaxis_coords)
            
        # Plot the path, if any.
        if self.status.data_path_points:
            haxis_coords = [
                haxis_point(p) for p in self.status.data_path_points]
            vaxis_coords = [
                vaxis_point(p) for p in self.status.data_path_points]
            # Plot in black.
            color = rgb2hex(hsv_to_rgb([0, 0, 0.0]))
            self.axes.plot(haxis_coords, vaxis_coords, color)
            
        # Plot crossing data, if any.
        if self.status.crossing_data:
            for c in self.status.crossing_data:
                if c['success'] == "Y":
                    # Success = black
                    color = rgb2hex(hsv_to_rgb([0, 0, 0.0]))
                else:
                    # Failure = gray
                    color = rgb2hex(hsv_to_rgb([0, 0, 0.6]))
                
                # Add line segments.
                p1 = dict(x=c['x1'], y=c['y1'], z=c['z1'])
                p2 = dict(x=c['x2'], y=c['y2'], z=c['z2'])
                haxis_coords = [haxis_point(p1), haxis_point(p2)]
                vaxis_coords = [vaxis_point(p1), vaxis_point(p2)]
                self.axes.plot(haxis_coords, vaxis_coords, color)
                
                # Add dot markers.
                self.axes.plot(haxis_coords, vaxis_coords, color, marker='o')
            
        
    def setup_figure(self):
        # Set the desired DPI.
        self.figure.set_dpi(self.status.dpi)
        
        # Fix the figure size in case of a new DPI.
        # If the DPI decreased then the figure inches need to increase,
        # and vice versa.
        # If this is not done, then updating the DPI will make the figure not
        # fit in the canvas. (It only fixes itself upon a window resize.)
        if self.previous_dpi != self.status.dpi:
            x_inches, y_inches = self.figure.get_size_inches()
            self.figure.set_size_inches(
                x_inches * (self.previous_dpi / self.status.dpi),
                y_inches * (self.previous_dpi / self.status.dpi))
        self.previous_dpi = self.status.dpi
        
        # Figure out what the axes limits should be to contain all the
        # checkpoints.
        margin_factor = 0.1
        axes_hmin = (
            self.data_hmin - (self.data_hmax - self.data_hmin)*margin_factor)
        axes_hmax = (
            self.data_hmax + (self.data_hmax - self.data_hmin)*margin_factor)
        axes_vmin = (
            self.data_vmin - (self.data_vmax - self.data_vmin)*margin_factor)
        axes_vmax = (
            self.data_vmax + (self.data_vmax - self.data_vmin)*margin_factor)
        hrange = axes_hmax - axes_hmin
        vrange = axes_vmax - axes_vmin
        
        # Expand one dimension as needed to fill the canvas while maintaining
        # aspect ratio.
        canvas_width, canvas_height = self.canvas.get_width_height()
        if hrange / vrange >= canvas_width / canvas_height:
            # Add extra vertical range to maintain aspect ratio
            target_vrange = hrange*(canvas_height / canvas_width)
            extra_vspace_one_side = (target_vrange - vrange) / 2
            axes_vmin = axes_vmin - extra_vspace_one_side
            axes_vmax = axes_vmax + extra_vspace_one_side
        else:
            # Add extra horizontal range to maintain aspect ratio
            target_hrange = vrange*(canvas_width / canvas_height)
            extra_hspace_one_side = (target_hrange - hrange) / 2
            axes_hmin = axes_hmin - extra_hspace_one_side
            axes_hmax = axes_hmax + extra_hspace_one_side
            
        # Apply the axes limits.
        self.axes.set_xlim(axes_hmin, axes_hmax)
        self.axes.set_ylim(axes_vmin, axes_vmax)
        
        # Debug info
        # print(f"canvas size: {canvas_width}, {canvas_height}")
        # print(f"figure size: {self.figure.get_size_inches()}")
        # print(
        #     f"data ranges: {self.data_hmin:.3f}~{self.data_hmax:.3f}"
        #     f" {self.data_vmin:.3f}~{self.data_vmax:.3f}")
        # print(f"axes range sizes: {hrange}, {vrange}")
        # print(f"xlim: {self.axes.get_xlim()}")
        # print(f"ylim: {self.axes.get_ylim()}")
            
        
    def save(self, filepath):
        if self.save_rectangle:
            # We've specified a specific region of the diagram to save.
            dpi = self.status.dpi
            # save_rectangle is in canvas pixels; need to convert to inches
            bbox_inches = Bbox([
                (min(self.save_rectangle[0][0], self.save_rectangle[1][0])/dpi,
                min(self.save_rectangle[0][1], self.save_rectangle[1][1])/dpi),
                (max(self.save_rectangle[0][0], self.save_rectangle[1][0])/dpi,
                max(self.save_rectangle[0][1], self.save_rectangle[1][1])/dpi),
            ])
        else:
            # Save the whole diagram.
            bbox_inches = None
            
        self.figure.savefig(
            filepath,
            # Force PNG format; JPEG is not supported by our MPL backend
            format='png',
            # DPI to use for saving.
            # This solely affects level of detail/resolution of the resulting
            # image file. Font size, line thickness, etc. should be the same
            # as seen in the figure canvas.
            dpi=self.status.save_dpi,
            bbox_inches=bbox_inches,
        )

