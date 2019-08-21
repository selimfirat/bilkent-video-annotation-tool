import json
import sys
import string
import os.path
import vlc
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QKeySequence, QPainter, QFont, QColor, QPen
from PyQt5.QtWidgets import QToolBar, QAction, QStatusBar, QShortcut, QFileDialog

import glob


class Player(QtWidgets.QMainWindow):

    def __init__(self, master=None):
        QtWidgets.QMainWindow.__init__(self, master)
        self.setWindowIcon(QIcon("icons/app.svg"))
        self.title = "Bilkent Video Annotation Tool"

        self.setWindowTitle(self.title)
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        options |= QFileDialog.Directory

        # options |= QFileDialog.DontUseNativeDialog

        self.video_paths = []
        while len(self.video_paths) == 0:
            videos_dir = str(QFileDialog.getExistingDirectory(self, "Select Videos Directory", options=options))
            self.video_paths = [f for f in glob.glob(videos_dir + "**/*.avi", recursive=False)] # TODO: support other formats, too
            print(self.video_paths)

            if len(self.video_paths) == 0 or len(videos_dir) == 0:
                QtWidgets.QMessageBox.question(self, 'No videos exist', "Please select a directory containing videos.",
                                                             QtWidgets.QMessageBox.Ok)

        self.annotations_dir = ""
        while len(self.annotations_dir) == 0:
            self.annotations_dir = str(QFileDialog.getExistingDirectory(self, "Select Annotations Directory", options=options))
            print(self.annotations_dir)
            self.annotation_paths = [f for f in glob.glob(self.annotations_dir + "**/*.json", recursive=False)]
            if len(self.annotations_dir) == 0:
                QtWidgets.QMessageBox.question(self, 'No directory selected.', "Please select a directory for annotations",
                                                             QtWidgets.QMessageBox.Ok)


        self.num_videos = len(self.video_paths)
        self.current_video = 0


        self.annotations = {}

        for annotation_path in self.annotation_paths:
            j = json.load(open(annotation_path, "r"))
            self.annotations[j["name"]] = j

        print(self.annotation_paths)

        self.createVideoPlayer()

        self.createUI()

        self.createToolbar()

        self.setStatusBar(QStatusBar(self))

        self.createShortcuts()

        self.current_annotation = "A"

        is_video_set = False
        for i, video_path in enumerate(self.video_paths):

            if "\\" in video_path:
                video_name = video_path.split("\\")[-1]
            else:
                video_name = video_path.split("/")[-1]

            if video_name not in self.annotations:
                self.file = self.OpenFile(video_path)

                self.current_video_attrs = self.annotations.get(video_name, {
                    "name": video_name,
                    "path": video_path,
                    "annotations": {}
                })
                self.annotations[self.current_video_attrs["name"]] = self.current_video_attrs
                self.current_video = i

                is_video_set = True

                break

        if not is_video_set:
            video_path = self.video_paths[0]
            if "\\" in video_path:
                video_name = video_path.split("\\")[-1]
            else:
                video_name = video_path.split("/")[-1]
            self.file = self.OpenFile(video_path)
            self.current_video_attrs = self.annotations.get(video_name, {
                "name": video_name,
                "path": video_path,
                "annotations": {}
            })

            self.annotations[self.current_video_attrs["name"]] = self.current_video_attrs

        self.play()

        self.next_visible = True
        self.prev_visible = True
        self.setVisibilities()

    def setPrevNextVisibility(self):
        self.prev_visible = self.current_video != 0
        self.next_visible = self.current_video != self.num_videos - 1
        self.remove_visible = self.current_video_attrs["name"] in self.annotations and len(self.annotations[self.current_video_attrs["name"]]["annotations"]) > 0

        self.action_previous.setVisible(self.prev_visible)
        self.action_next.setVisible(self.next_visible)
        self.action_remove_annotations.setVisible(self.remove_visible)

    def createShortcuts(self):
        self.shortcut_playpause = QShortcut(QKeySequence(QtCore.Qt.Key_Return), self)
        self.shortcut_playpause.activated.connect(self.playPauseShortcut)

        self.shortcut_previous = QShortcut(QKeySequence(QtCore.Qt.Key_Left), self)
        self.shortcut_previous.activated.connect(self.previousShortcut)

        self.shortcut_next = QShortcut(QKeySequence(QtCore.Qt.Key_Right), self)
        self.shortcut_next.activated.connect(self.nextShortcut)

        self.shortcut_annotate = QShortcut(QKeySequence(QtCore.Qt.Key_Space), self)
        self.shortcut_annotate.activated.connect(self.annotate)

        self.shortcut_remove_annotation = QShortcut(QKeySequence(QtCore.Qt.Key_Shift), self) # TODO: Change key
        self.shortcut_remove_annotation.activated.connect(self.removeAnnotations)

        for s in string.ascii_uppercase:
            key = getattr(QtCore.Qt, "Key_" + s)
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(self.changeAnnotationShortcut(s))

    def changeAnnotationShortcut(self, s):

        def annotationShortcut():
            self.current_annotation = s

        return annotationShortcut

    def removeAnnotations(self):

        self.current_video_attrs["annotations"] = {}
        self.annotations[self.current_video_attrs["name"]] = self.current_video_attrs

        self.setVisibilities()

    def previousShortcut(self):
        if self.prev_visible:
            self.previous()

    def nextShortcut(self):
        if self.next_visible:
            self.next()

    def setVisibilities(self):
        self.setPrevNextVisibility()

        self.markwidget.setAnnotations(self.annotations[self.current_video_attrs["name"]]["annotations"])

    def annotate(self):


        self.current_video_attrs["annotations"][self.current_annotation] = [self.mediaplayer.get_position()] + self.current_video_attrs["annotations"].get(self.current_annotation, [])

        self.annotations[self.current_video_attrs["name"]] = self.current_video_attrs

        self.setVisibilities()


    def saveAnnotation(self, annotation):
        with open(os.path.join(self.annotations_dir, annotation["name"] + ".json"), "w+") as f:
            json.dump(annotation, f)

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

        self.action_annotate = QAction(QIcon("icons/plus.png"), "Annotate to current frame of the video", self)
        self.action_annotate.triggered.connect(self.annotate)
        self.action_annotate.setStatusTip("Annotate to current frame of the video [Space Key]")
        toolbar.addAction(self.action_annotate)

        self.action_remove_annotations = QAction(QIcon("icons/cancel.png"), "Remove current video's annotations", self)
        self.action_remove_annotations.triggered.connect(self.removeAnnotations)
        self.action_remove_annotations.setStatusTip("Remove current video's annotations [Shift Key]")
        toolbar.addAction(self.action_remove_annotations)


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

        self.saveAnnotation(self.current_video_attrs)

        if not self.isPaused:
            self.Stop()

        self.current_video -= 1
        video_path = self.video_paths[self.current_video]
        if "\\" in video_path:
            video_name = video_path.split("\\")[-1]
        else:
            video_name = video_path.split("/")[-1]


        self.file = self.OpenFile(video_path)

        if video_name in self.annotations:
            self.current_video_attrs = self.annotations[video_name]
        else:
            self.current_video_attrs = {
                "name": video_name,
                "path": video_path,
                "annotations": {}
            }

            self.annotations[video_name] = self.current_video_attrs


        self.progress.setValue(self.current_video)

        self.setVisibilities()
        self.play()

    def next(self):
        print("Next clicked")

        self.saveAnnotation(self.current_video_attrs)

        if not self.isPaused:
            self.Stop()

        self.current_video += 1

        if self.current_video == self.num_videos:
            QtWidgets.QMessageBox.question(self, "No more videos left.", "All videos are annotated. Now, opening the first video...",
            QtWidgets.QMessageBox.Ok)
            self.current_video = 0

        video_path = self.video_paths[self.current_video]

        if "\\" in video_path:
            video_name = video_path.split("\\")[-1]
        else:
            video_name = video_path.split("/")[-1]


        self.file = self.OpenFile(video_path)

        if video_name in self.annotations:
            self.current_video_attrs = self.annotations[video_name]
        else:
            self.current_video_attrs = {
                "name": video_name,
                "path": video_path,
                "annotations": {}
            }

            self.annotations[video_name] = self.current_video_attrs

        self.progress.setValue(self.current_video)

        self.setVisibilities()
        self.play()

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

        self.markwidget = MarkWidget()

        self.vboxlayout.addWidget(self.markwidget)


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
        self.setWindowTitle(self.title + " | " + self.media.get_meta(0))

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

            if not self.isPaused:
                self.Stop()
                self.next()

class MarkWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.annotations = {}
        self.setMaximumSize(5000, 30)


    def paintEvent(self, e):
        qp = QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()

    def setAnnotations(self, annotations):
        self.annotations = annotations

        self.repaint()


    def drawWidget(self, qp):
        MAX_CAPACITY  = 1000
        font = QFont('Serif', 8, QFont.Light)
        qp.setFont(font)
        size = self.size()
        w    = size.width()
        h    = size.height()
        step = int(round(w / 1000))
        full = int(((w / MAX_CAPACITY) * MAX_CAPACITY))

        qp.setPen(QColor(255, 255, 255))
        qp.setBrush(QColor(255, 255, 184))
        qp.drawRect(0, 0, full, h)

        pen = QPen(QColor(20, 20, 20), 1, Qt.SolidLine)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        qp.drawRect(0, 0, w-1, h-1)
        j = 0

        qp.setPen(QPen(QColor(255, 0, 0), 1, Qt.SolidLine))


        for key, poslist in self.annotations.items():
            for pos in poslist:
                x = int(w*pos)
                metrics = qp.fontMetrics()
                qp.drawLine(x, 0, x, h)
                fw = metrics.width(key)
                qp.drawText(x+fw/2, h/2, key)




if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    player = Player()
    player.show()
    player.resize(640, 480)
    sys.exit(app.exec_())
