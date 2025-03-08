import numpy as np
import math
import pylsl
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from typing import List
import matplotlib.pyplot as plt

# Basic parameters for the plotting window
plot_duration = 5  # how many seconds of data to show
update_interval = 30  # ms between screen updates
pull_interval = 100  # ms between each pull operation

# Global color list
cmap = plt.get_cmap('Set1')
colors = [cmap(i) for i in range(cmap.N)]
color_index = 0

def get_next_color():
    global color_index
    color = colors[color_index % len(colors)]
    color_index += 1
    return tuple(int(255 * x) for x in color)

class Inlet:
    """Base class to represent a plottable inlet"""
    def __init__(self, info: pylsl.StreamInfo):
        self.inlet = pylsl.StreamInlet(info, max_buflen=plot_duration,
                                       processing_flags=pylsl.proc_clocksync | pylsl.proc_dejitter, max_chunklen=0)
        self.name = info.name()
        self.channel_count = info.channel_count()

    def pull_and_plot(self, plot_time: float, plt: pg.PlotItem):
        pass

class DataInlet(Inlet):
    dtypes = [[], np.float32, np.float64, None, np.int32, np.int16, np.int8, np.int64]

    def __init__(self, info: pylsl.StreamInfo, plt: pg.PlotItem):
        super().__init__(info)
        bufsize = (2 * math.ceil(info.nominal_srate() * plot_duration), info.channel_count())
        self.buffer = np.empty(bufsize, dtype=self.dtypes[info.channel_format()])
        empty = np.array([])

        self.curves = []
        for _ in range(self.channel_count):
            pen = pg.mkPen(get_next_color())
            curve = pg.PlotCurveItem(x=empty, y=empty, autoDownsample=True, pen=pen)
            self.curves.append(curve)
            plt.addItem(curve)

    def pull_and_plot(self, plot_time, plt):
        _, ts = self.inlet.pull_chunk(timeout=0.0, max_samples=self.buffer.shape[0], dest_obj=self.buffer)
        if ts:
            ts = np.asarray(ts)
            y = self.buffer[0:ts.size, :]
            this_x = None
            old_offset = 0
            new_offset = 0
            for ch_ix in range(self.channel_count):
                old_x, old_y = self.curves[ch_ix].getData()
                if ch_ix == 0:
                    old_offset = old_x.searchsorted(plot_time)
                    new_offset = ts.searchsorted(plot_time)
                    this_x = np.hstack((old_x[old_offset:], ts[new_offset:]))
                this_y = np.hstack((old_y[old_offset:], y[new_offset:, ch_ix] - ch_ix * 1.5))
                self.curves[ch_ix].setData(this_x, this_y)

class MarkerInlet(Inlet):
    """A MarkerInlet shows events that happen sporadically as vertical lines"""
    def __init__(self, info: pylsl.StreamInfo):
        super().__init__(info)

    def pull_and_plot(self, plot_time, plt):
        strings, timestamps = self.inlet.pull_chunk(0)
        if timestamps:
            for string, ts in zip(strings, timestamps):
                plt.addItem(pg.InfiniteLine(ts, angle=90, movable=False, label=string[0], pen=pg.mkPen(get_next_color())))

class StreamSelectorDialog(QtWidgets.QDialog):
    def __init__(self, streams):
        super().__init__()
        self.setWindowTitle("Select Streams")
        self.selected_streams = []

        layout = QtWidgets.QVBoxLayout()
        
        # Create checkboxes for each stream
        self.checkboxes = []
        for stream in streams:
            checkbox = QtWidgets.QCheckBox(stream.name())
            layout.addWidget(checkbox)
            self.checkboxes.append((checkbox, stream))  # Store both checkbox and stream

        # Add OK and Cancel buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def accept(self):
        # Gather only the streams with checked boxes
        self.selected_streams = [stream for checkbox, stream in self.checkboxes if checkbox.isChecked()]
        super().accept()  # Close the dialog with accepted status

    def get_selected_streams(self):
        return self.selected_streams

class LSLPlotter(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_paused = False

        self.inlets: List[Inlet] = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle('LSL Plot')

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout()
        central_widget.setLayout(layout)

        self.plot_widget = pg.PlotWidget(title='LSL Plot')
        layout.addWidget(self.plot_widget)

        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.enableAutoRange(x=False, y=True)
        self.legend = self.plot_item.addLegend(loc='upper left')

        self.setup_streams()

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_plot_range)
        self.update_timer.start(update_interval)

        self.pull_timer = QtCore.QTimer()
        self.pull_timer.timeout.connect(self.update)
        self.pull_timer.start(pull_interval)

    def setup_streams(self):
        print("Looking for streams...")
        streams = pylsl.resolve_streams()

        # Show the stream selection dialog
        dialog = StreamSelectorDialog(streams)
        if dialog.exec() == 1:  # Using 1 for QDialog.Accepted
            selected_streams = dialog.get_selected_streams()
            print("Selected streams:", [stream.name() for stream in selected_streams])

            # Now set up inlets only for the selected streams
            for info in selected_streams:
                if info.type() == 'Markers':
                    if info.nominal_srate() != pylsl.IRREGULAR_RATE or info.channel_format() != pylsl.cf_string:
                        print('Invalid marker stream ' + info.name())
                    print('Adding marker inlet: ' + info.name())
                    self.inlets.append(MarkerInlet(info))  # Now recognized
                elif info.nominal_srate() != pylsl.IRREGULAR_RATE and info.channel_format() != pylsl.cf_string:
                    print('Adding data inlet: ' + info.name())
                    inlet = DataInlet(info, self.plot_item)
                    self.inlets.append(inlet)

                    # Access the metadata to fetch channel labels
                    channelInlet = pylsl.StreamInlet(info)
                    channelInlet = channelInlet.info()
                    channels = channelInlet.desc().child("channels").child("channel")
                    channel_labels = []  # List to store channel labels
                    
                    # Retrieve the channel labels and store them
                    for ch_index in range(channelInlet.channel_count()):
                        # Add the label to the list
                        channel_labels.append(channels.child_value("label"))

                        # Move to the next sibling channel
                        channels = channels.next_sibling("channel")

                    # Check that the labels list is populated
                    print(f"Channel Labels for {info.name()}: {channel_labels}")

                    # Assign labels to the curves
                    for ch_index, channel_label in enumerate(channel_labels):
                        if ch_index < len(inlet.curves):
                            print(f"Assigning label '{channel_label}' to curve {ch_index}")
                            self.legend.addItem(inlet.curves[ch_index], f'{channel_label}')
                        else:
                            print(f"Warning: No curve for channel {channel_label}")
                elif info.nominal_srate() == pylsl.IRREGULAR_RATE and info.channel_format() != pylsl.cf_string:
                    print('Adding irregular data inlet: ' + info.name())
                    inlet = IrregularDataInlet(info, self.plot_item)
                    self.inlets.append(inlet)

                    # Access the metadata to fetch channel labels
                    channelInlet = pylsl.StreamInlet(info)
                    channelInlet = channelInlet.info()
                    channels = channelInlet.desc().child("channels").child("channel")
                    channel_labels = []  # List to store channel labels
                    
                    # Retrieve the channel labels and store them
                    for ch_index in range(channelInlet.channel_count()):
                        # Add the label to the list
                        channel_labels.append(channels.child_value("label"))

                        # Move to the next sibling channel
                        channels = channels.next_sibling("channel")

                    # Check that the labels list is populated
                    print(f"Channel Labels for {info.name()}: {channel_labels}")

                    # Assign labels to the curves
                    for ch_index, channel_label in enumerate(channel_labels):
                        if ch_index < len(inlet.curves):
                            print(f"Assigning label '{channel_label}' to curve {ch_index}")
                            self.legend.addItem(inlet.curves[ch_index], f'{channel_label}')
                        else:
                            print(f"Warning: No curve for channel {channel_label}")
                else:
                    print("Don't know what to do with stream " + info.name())
    
    def update_plot_range(self):
        """Update the plot's X-axis range to create a scrolling effect."""
        fudge_factor = pull_interval * .002
        plot_time = pylsl.local_clock()
        self.plot_widget.setXRange(plot_time - plot_duration + fudge_factor, plot_time - fudge_factor)

    def update(self):
        mintime = pylsl.local_clock() - plot_duration
        for inlet in self.inlets:
            inlet.pull_and_plot(mintime, self.plot_item)

def setup_streams(self):
    print("Looking for streams...")
    streams = pylsl.resolve_streams()
    
    # Show the stream selection dialog
    dialog = StreamSelectorDialog(streams)
    if dialog.exec() == QtWidgets.QDialog.Accepted:
        selected_streams = dialog.get_selected_streams()
        print("Selected streams:", [stream.name() for stream in selected_streams])

        # Now set up inlets only for the selected streams
        for info in selected_streams:
            # Setup the inlets as before
            if info.type() == 'Markers':
                if info.nominal_srate() != pylsl.IRREGULAR_RATE or info.channel_format() != pylsl.cf_string:
                    print('Invalid marker stream ' + info.name())
                print('Adding marker inlet: ' + info.name())
                self.inlets.append(MarkerInlet(info))
            elif info.nominal_srate() != pylsl.IRREGULAR_RATE and info.channel_format() != pylsl.cf_string:
                print('Adding data inlet: ' + info.name())
                inlet = DataInlet(info, self.plot_item)
                self.inlets.append(inlet)
                
                # Adding channels to the legend
                channels = info.desc().child("channels").child("channel")
                channel_index = 0
                while channels and channel_index < len(inlet.curves):
                    channel_label = channels.child_value("label")
                    self.legend.addItem(inlet.curves[channel_index], f'{info.name()} - {channel_label}')
                    channels = channels.next_sibling("channel")
                    channel_index += 1
            elif info.nominal_srate() == pylsl.IRREGULAR_RATE and info.channel_format() != pylsl.cf_string:
                print('Adding irregular data inlet: ' + info.name())
                inlet = IrregularDataInlet(info, self.plot_item)
                self.inlets.append(inlet)

                channels = info.desc().child("channels").child("channel")
                channel_index = 0
                while channels and channel_index < len(inlet.curves):
                    channel_label = channels.child_value("label")
                    self.legend.addItem(inlet.curves[channel_index], f'{info.name()} - {channel_label}')
                    channels = channels.next_sibling("channel")
                    channel_index += 1
            else:
                print("Don't know what to do with stream " + info.name())

    def scroll(self):
        fudge_factor = pull_interval * .002
        plot_time = pylsl.local_clock()
        self.plot_widget.setXRange(plot_time - plot_duration + fudge_factor, plot_time - fudge_factor)

    def update(self):
        mintime = pylsl.local_clock() - plot_duration
        for inlet in self.inlets:
            inlet.pull_and_plot(mintime, self.plot_item)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.update_timer.stop()
            self.pull_timer.stop()
        else:
            self.update_timer.start(update_interval)
            self.pull_timer.start(pull_interval)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.toggle_pause()
        else:
            super().keyPressEvent(event)

def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    window = LSLPlotter()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
