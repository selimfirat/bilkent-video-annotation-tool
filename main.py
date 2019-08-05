import json
import sys
import os.path
import vlc
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import QToolBar, QAction, QStatusBar, QShortcut, QFileDialog

import glob

# TODO: create annotations file on video end
# TODO: progress bar for number of videos/total videos
# TODO: transition to next video on video end
# TODO: Hide/show next/back buttons on edges.
# TODO: share on github

class Player(QtWidgets.QMainWindow):

    def __init__(self, master=None):
        QtWidgets.QMainWindow.__init__(self, master)

        self.setWindowTitle("Bilkent Video Annotation Tool")
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        video_paths = []
        while len(video_paths) == 0 or len(videos_dir) == 0:
            videos_dir = str(QFileDialog.getExistingDirectory(self, "Select Videos Directory", options=options))
            video_paths = [f for f in glob.glob(videos_dir + "**/*.avi", recursive=False)] # TODO: support other formats, too
            print(video_paths)

            if len(video_paths) == 0 or len(videos_dir) == 0:
                QtWidgets.QMessageBox.question(self, 'No videos exist', "Please select a directory containing videos.",
                                                             QtWidgets.QMessageBox.Ok)

        annotations_dir = ""
        while len(annotations_dir) == 0:
            annotations_dir = str(QFileDialog.getExistingDirectory(self, "Select Annotations Directory", options=options))
            print(annotations_dir)
            annotation_paths = [f for f in glob.glob(annotations_dir + "**/*.json", recursive=False)]
            if len(annotations_dir) == 0:
                QtWidgets.QMessageBox.question(self, 'No directory selected.', "Please select a directory for annotations",
                                                             QtWidgets.QMessageBox.Ok)


        self.num_videos = len(video_paths)
        self.current_video = 0


        annotations = {}

        for annotation_path in annotation_paths:
            j = json.load(open(annotation_path, "r"))
            annotations[j["name"]] = j

        print(annotation_paths)

        self.createVideoPlayer()

        self.createUI()

        self.createToolbar()

        self.setStatusBar(QStatusBar(self))

        self.createShortcuts()

        self.current_annotation = "A"

        for i, video_path in enumerate(video_paths):
            video_name = video_path.split("\\")[-1]
            if video_name not in annotations:
                self.file = self.OpenFile(video_path)
                self.current_video_attrs = {
                    "name": video_name,
                    "path": video_path
                }
                self.current_video = i

                break


        self.setPrevNextVisibility()

    def setPrevNextVisibility(self):
        if self.current_video == 0:
            self.action_previous.setVisible(False)

        if self.current_video == self.num_videos - 1:
            self.action_next.setVisible(False)

    def createShortcuts(self):
        self.shortcut_playpause = QShortcut(QKeySequence(QtCore.Qt.Key_Return), self)
        self.shortcut_playpause.activated.connect(self.playPauseShortcut)

        self.shortcut_previous = QShortcut(QKeySequence(QtCore.Qt.Key_Left), self)
        self.shortcut_previous.activated.connect(self.previousShortcut)

        self.shortcut_next = QShortcut(QKeySequence(QtCore.Qt.Key_Right), self)
        self.shortcut_next.activated.connect(self.nextShortcut)

        self.shortcut_annotate = QShortcut(QKeySequence(QtCore.Qt.Key_Space), self)
        self.shortcut_annotate.activated.connect(self.annotate)

    def previousShortcut(self):
        self.previous()

    def nextShortcut(self):
        self.next()

    def annotate(self):
        if not self.mediaplayer.is_playing():
            return

        if self.current_video["name"] not in self.annotations:
            self.annotations[self.current_video["name"]] = {
                "name": self.current_video["name"],
                "path": self.current_video["path"],
                "annotations": {}
            }
        if self.current_annotation not in self.annotations[self.current_video["name"]]["annotations"]:
            self.annotations[self.current_video["name"]]["annotations"][self.current_annotation] = []

        self.annotations[self.current_video["name"]]["annotations"][self.current_annotation].append(self.mediaplayer.get_position())

    def playPauseShortcut(self):
        if self.isPaused:
            self.play()
        else:
            self.pause()

    def createVideoPlayer(self):

        self.instance = vlc.Instance()

        self.mediaplayer = self.instance.media_player_new()

        self.isPaused = False


    def createToolbar(self):
        toolbar = QToolBar("Manage Video")
        toolbar.setIconSize(QSize(32, 32))

        self.addToolBar(toolbar)

        self.action_play = QAction(QIcon("icons/play-button.png"), "Play", self)
        self.action_play.triggered.connect(self.play)
        self.action_play.setStatusTip("Play Video [Enter Key]")
        toolbar.addAction(self.action_play)


        self.action_pause = QAction(QIcon("icons/pause.png"), "Pause", self)
        self.action_pause.triggered.connect(self.pause)
        self.action_pause.setVisible(False)
        self.action_pause.setStatusTip("Pause Video [Enter Key]")
        toolbar.addAction(self.action_pause)

        self.action_previous = QAction(QIcon("icons/previous.png"), "Previous Video", self)
        self.action_previous.setStatusTip("Previous Video [Right Arrow]")
        self.action_previous.triggered.connect(self.previous)
        toolbar.addAction(self.action_previous)

        self.action_next = QAction(QIcon("icons/next.png"), "Next Video", self)
        self.action_next.triggered.connect(self.next)
        self.action_next.setStatusTip("Next Video [Right Arrow]")
        toolbar.addAction(self.action_next)


    def play(self):
        print("Play clicked")
        self.PlayPause()

    def pause(self):
        print("Pause clicked")
        self.PlayPause()


    def previous(self):
        print("Previous clicked")

        if self.current_video - 1 < 0:
            return

        self.current_video -= 1
        video_path = self.video_paths[self.current_video]
        video_name = video_path.split("\\")[-1]
        self.file = self.OpenFile(video_path)
        self.current_video_attrs = {
            "name": video_name,
            "path": video_path
        }

        self.progress.setValue(self.current_video)
        self.setPrevNextVisibility()

    def next(self):
        print("Next clicked")



        if self.current_video + 1 == self.num_videos:
            return

        self.current_video += 1
        video_path = self.video_paths[self.current_video]
        video_name = video_path.split("\\")[-1]
        self.file = self.OpenFile(video_path)
        self.current_video_attrs = {
            "name": video_name,
            "path": video_path
        }

        self.progress.setValue(self.current_video)
        self.setPrevNextVisibility()

    def createUI(self):
        """Set up the user interface, signals & slots
        """
        self.widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.widget)

        # In this widget, the video will be drawn
        # if sys.platform == "darwin": # for MacOS
        #     self.videoframe = QtWidgets.QMacCocoaViewContainer(0)
        # else:
        #     self.videoframe = QtWidgets.QFrame()
        self.videoframe = QtWidgets.QFrame()
        self.palette = self.videoframe.palette()
        self.palette.setColor (QtGui.QPalette.Window,
                               QtGui.QColor(0,0,0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        self.positionslider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
        self.positionslider.setToolTip("Position")
        self.positionslider.setMaximum(1000)
        self.positionslider.sliderMoved.connect(self.setPosition)

        self.vboxlayout = QtWidgets.QVBoxLayout()
        self.vboxlayout.addWidget(self.videoframe)
        self.vboxlayout.addWidget(self.positionslider)

        self.widget.setLayout(self.vboxlayout)

        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setMaximum(self.num_videos)
        self.vboxlayout.addWidget(self.progress)


        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.updateUI)


    def PlayPause(self):
        """Toggle play/pause status
        """
        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.action_play.setVisible(True)
            self.action_pause.setVisible(False)
            self.isPaused = True
        else:
            self.mediaplayer.play()
            self.action_play.setVisible(False)
            self.action_pause.setVisible(True)
            self.timer.start()
            self.isPaused = False

    def Stop(self):
        """Stop player
        """
        self.mediaplayer.stop()

    def OpenFile(self, filename=None):
        """Open a media file in a MediaPlayer
        """
        if filename is None or filename is False:
            print("Attempt to openup OpenFile")
            filenameraw = QtWidgets.QFileDialog.getOpenFileName(self, "Open File", os.path.expanduser('~'))
            filename = filenameraw[0]

        if not filename:
            return

        # create the media
        if sys.version < '3':
            filename = unicode(filename)
        self.media = self.instance.media_new(filename)
        # put the media in the media player
        self.mediaplayer.set_media(self.media)

        # parse the metadata of the file
        self.media.parse()
        # set the title of the track as window title
        self.setWindowTitle(self.media.get_meta(0))

        # the media player has to be 'connected' to the QFrame
        # (otherwise a video would be displayed in it's own window)
        # this is platform specific!
        # you have to give the id of the QFrame (or similar object) to
        # vlc, different platforms have different functions for this
        if sys.platform.startswith('linux'): # for Linux using the X Server
            self.mediaplayer.set_xwindow(self.videoframe.winId())
        elif sys.platform == "win32": # for Windows
            self.mediaplayer.set_hwnd(self.videoframe.winId())
        elif sys.platform == "darwin": # for MacOS
            self.mediaplayer.set_nsobject(int(self.videoframe.winId()))
        self.PlayPause()


    def setPosition(self, position):
        """Set the position
        """
        # setting the position to where the slider was dragged
        self.mediaplayer.set_position(position / 1000.0)
        # the vlc MediaPlayer needs a float value between 0 and 1, Qt
        # uses integer variables, so you need a factor; the higher the
        # factor, the more precise are the results
        # (1000 should be enough)

    def updateUI(self):
        """updates the user interface"""
        # setting the slider to the desired position
        self.positionslider.setValue(self.mediaplayer.get_position() * 1000)

        if not self.mediaplayer.is_playing():
            # no need to call this function if nothing is played
            self.timer.stop()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    player = Player()
    player.show()
    player.resize(640, 480)
    sys.exit(app.exec_())
