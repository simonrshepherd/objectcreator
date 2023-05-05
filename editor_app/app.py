# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QMainWindow, QDialog, QApplication, QMessageBox, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout, QTabWidget, QDial, QSlider, QScrollBar, QGroupBox, QToolButton, QComboBox, QPushButton, QLineEdit, QLabel, QCheckBox, QDoubleSpinBox, QListWidget, QFileDialog
from PyQt5 import uic, QtGui, QtCore
from PIL import Image
from PIL.ImageQt import ImageQt
import traceback
import sys

if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


import io
from os import getcwd
from os.path import splitext, split
from json import load as jload
from json import dump as jdump
from enum import Enum

from customwidgets import ColorSelectWidget
import widgets as wdg
import auxiliaries as aux

from rctobject import constants as cts
from rctobject import objects as obj
from rctobject import palette as pal






class MainWindowUi(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('main_window.ui', self)

        self.new_object_count = 1

        self.loadSettings()
        self.bounding_boxes = aux.BoundingBoxes()

        ##### Tabs
        self.object_tabs = self.findChild(
            QTabWidget, "tabWidget_objects")
        self.sprite_tabs = self.findChild(
            QTabWidget, "tabWidget_sprites")

        self.object_tabs.removeTab(0)
        self.sprite_tabs.removeTab(0)

        # Tab actions
        self.object_tabs.tabCloseRequested.connect(self.closeObject)
        self.object_tabs.currentChanged.connect(self.changeTab)


        #### Tools
        self.widget_tools = self.findChild(QWidget, "widget_tools")
        container = QGridLayout()

        self.tool_buttons = {}

        for tool in self.Tools:
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setText(tool.fullname)
            btn.clicked.connect(lambda x, tool = tool: self.selectTool(tool))
            container.addWidget(btn, tool.value % 3, int(tool.value/3))
            self.tool_buttons[tool] = btn


        self.widget_tools.setLayout(container)
        self.tool = self.Tools.PEN
        self.tool_buttons[self.Tools.PEN].setChecked(True)


        # Brushes
        self.brush_buttons = {}

        for brush in self.Brushes:
            btn = self.findChild(QPushButton, f'pushButton_brush{brush.fullname}')

            btn.clicked.connect(lambda x, brush = brush: self.selectBrush(brush))
            self.brush_buttons[brush] = btn
            
        self.brush = self.Brushes.SOLID
        self.brush_buttons[self.Brushes.SOLID].setChecked(True)

        self.dial_brushsize = self.findChild(QDial, 'dial_Brushsize')

        self.dial_brushsize.valueChanged.connect(self.setBrushsize)
        
        self.brushsize = 1


        # Color Panel
        self.widget_color_panel = self.findChild(QGroupBox, "groupBox_selectedColor")

        self.color_select_panel = ColorSelectWidget(pal.orct, True, True, True)
        self.giveActiveShade = self.color_select_panel.giveActiveShade #this is a function wrapper to get the current active shade

        self.widget_color_panel.layout().addWidget(self.color_select_panel)

        # Color Manipulations
        self.checkbox_all_views = self.findChild(
            QCheckBox, "checkBox_allViews")

        self.button_remap_to = self.findChild(
            QPushButton, "pushButton_remapTo")
        self.combobox_remap_to_color = self.findChild(
            QComboBox, "comboBox_remapToColor")

        self.combobox_remap_to_color.addItems(
            list(self.current_palette.color_dict))
        self.combobox_remap_to_color.setCurrentIndex(
            self.current_palette.color_dict['1st Remap'])

        self.button_incr_brightness = self.findChild(
            QPushButton, "pushButton_incrBrightness")
        self.button_decr_brightness = self.findChild(
            QPushButton, "pushButton_decrBrightness")
        self.button_remove_color = self.findChild(
            QPushButton, "pushButton_deleteColor")

        self.button_remap_to.clicked.connect(self.colorRemapTo)
        self.button_incr_brightness.clicked.connect(lambda x, step = 1: self.colorChangeBrightness(step))
        self.button_decr_brightness.clicked.connect(lambda x, step = -1: self.colorChangeBrightness(step))
        self.button_remove_color.clicked.connect(self.colorRemove)




        #### Menubar
        self.actionSmallScenery.triggered.connect(lambda x: self.newObject(cts.Type.SMALL))
        self.actionOpenFile.triggered.connect(self.openObjectFile)
        self.actionSave.triggered.connect(self.saveObject)
        self.actionSaveObjectAt.triggered.connect(self.saveObjectAt)
        self.actionSettings.triggered.connect(self.changeSettings)

        self.actionBlack.triggered.connect(lambda x, mode=0: self.setCurrentImportColor(mode))
        self.actionWhite.triggered.connect(lambda x, mode=1: self.setCurrentImportColor(mode))
        self.actionUpper_Left_Pixel.triggered.connect(lambda x, mode=2: self.setCurrentImportColor(mode))
        self.actionCustom_Color.triggered.connect(lambda x, mode=3: self.setCurrentImportColor(mode))

        self.actionPaletteOpenRCT.triggered.connect(lambda x, palette=0: self.setCurrentPalette(palette))
        self.actionPaletteOld.triggered.connect(lambda x, palette=1: self.setCurrentPalette(palette))


        #Load empty object
        self.newObject(cts.Type.SMALL)

        self.show()

    def loadSettings(self):
        try:
            self.settings = jload(fp=open('config.json'))
        except FileNotFoundError:
            self.settings = {}
            self.changeSettings(update_widgets = False)

            #If user refused to enter settings, use hard coded settings
            if not self.settings:
                self.settings['openpath'] = "%USERPROFILE%/Documents/OpenRCT2"
                self.settings['savedefault'] = ''
                self.settings['opendefault'] =  "%USERPROFILE%/Documents/OpenRCT2/object"
                self.settings['author'] = ''
                self.settings['author_id'] = ''
                self.settings['no_zip'] = False
                self.settings['version'] = '1.0'
                self.settings['transparency_color'] = 0
                self.settings['import_color'] = [0,0,0]
                self.settings['palette'] = 0

        self.openpath = self.settings['openpath']
        self.setCurrentImportColor(self.settings['transparency_color'])
        self.setCurrentPalette(self.settings['palette'], update_widgets = False)



    def saveSettings(self):
        path = getcwd()
        with open(f'{path}/config.json', mode='w') as file:
            jdump(obj=self.settings, fp=file, indent=2)

    def changeSettings(self, update_widgets = True):
        dialog = wdg.ChangeSettingsUi(self.settings)

        if dialog.exec():
            self.settings = dialog.ret

            self.openpath = self.settings['openpath']
            self.setCurrentImportColor(self.settings['transparency_color'])
            self.setCurrentPalette(self.settings['palette'], update_widgets = update_widgets)

            self.saveSettings()


    def setCurrentImportColor(self, mode):
        if mode == 0:
            self.current_import_color = (0,0,0)
            self.actionBlack.setChecked(True)
            self.actionWhite.setChecked(False)
            self.actionUpper_Left_Pixel.setChecked(False)
            self.actionCustom_Color.setChecked(False)
        elif mode == 1:
            self.current_import_color = (255,255,255)
            self.actionBlack.setChecked(False)
            self.actionWhite.setChecked(True)
            self.actionUpper_Left_Pixel.setChecked(False)
            self.actionCustom_Color.setChecked(False)
        elif mode == 2:
            self.current_import_color = None
            self.actionBlack.setChecked(False)
            self.actionWhite.setChecked(False)
            self.actionUpper_Left_Pixel.setChecked(True)
            self.actionCustom_Color.setChecked(False)
        elif mode == 3:
            self.current_import_color = self.settings.get('import_color', (0,0,0))
            self.actionBlack.setChecked(False)
            self.actionWhite.setChecked(False)
            self.actionUpper_Left_Pixel.setChecked(False)
            self.actionCustom_Color.setChecked(True)

    def setCurrentPalette(self, palette, update_widgets = True):
        if palette == 0:
            self.current_palette = pal.orct
            self.actionPaletteOpenRCT.setChecked(True)
            self.actionPaletteOld.setChecked(False)
        elif palette == 1:
            self.current_palette = pal.green_remap
            self.actionPaletteOpenRCT.setChecked(False)
            self.actionPaletteOld.setChecked(True)
        
        if update_widgets:
            self.color_select_panel.switchPalette(self.current_palette)
            for index in range(self.object_tabs.count()):
                tab = self.object_tabs.widget(index)
                tab.o.switchPalette(self.current_palette)
                tab.spritesTab.updateAllViews()

    def changeTab(self, index):
        object_tab = self.object_tabs.widget(index)
        if object_tab and object_tab.locked:
            self.sprite_tabs.setCurrentIndex(self.sprite_tabs.indexOf(object_tab.locked_sprite_tab))



    def newObject(self, obj_type = cts.Type.SMALL):
        o = obj.newEmpty(obj_type)
        name = f'Object {self.new_object_count}'
        self.new_object_count += 1

        if not self.current_palette == pal.orct:
            o.switchPalette(self.current_palette)

        object_tab = wdg.ObjectTabSS(o, self, author = self.settings['author'], author_id = self.settings['author_id'])
        sprite_tab = wdg.SpriteTab(self, object_tab)

        object_tab.lockWithSpriteTab(sprite_tab)

        object_tab.settingsTab.setDefaults()

        self.object_tabs.addTab(object_tab, name)
        self.object_tabs.setCurrentWidget(object_tab)

        self.sprite_tabs.addTab(sprite_tab, f"{name} (locked)")
        self.sprite_tabs.setCurrentWidget(sprite_tab)

    def closeObject(self, index):
        object_tab = self.object_tabs.widget(index)
        if object_tab.locked:
            self.sprite_tabs.removeTab(self.sprite_tabs.indexOf(object_tab.locked_sprite_tab))

        self.object_tabs.removeTab(index)


    def openObjectFile(self):
        folder = self.settings.get('opendefault','')
        if not folder:
            folder = getcwd()
        filepaths, _ = QFileDialog.getOpenFileNames(
            self, "Open Object", folder, "All Object Type Files (*.parkobj *.DAT *.json);; Parkobj Files (*.parkobj);; DAT files (*.DAT);; JSON Files (*.json);; All Files (*.*)")

        if filepaths:
            for filepath in filepaths:
                try:
                    o = obj.load(filepath, openpath = self.openpath)
                    name = o.data.get('id', '').split('.',2)[-1]
                    if not name:
                        if o.old_id:
                            name = o.old_id
                        else:
                            name = f'Object {self.new_object_count}'
                            self.new_object_count += 1
                except Exception as e:
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Critical)
                    msg.setWindowTitle("Error")
                    msg.setText("Failed to load object")
                    msg.setInformativeText(str(e))
                    msg.show()
                    return

                extension = splitext(filepath)[1].lower()
                author_id = None
                if extension == '.parkobj':
                    filepath, filename = split(filepath)

                    # We assume that when the filename has more than 2 dots that the first part corresponds to the author id
                    if len(filename.split('.')) > 2:
                        author_id = filename.split('.')[0]
                else:
                    filepath = None

                if not self.current_palette == pal.orct:
                    o.switchPalette(self.current_palette)


                object_tab = wdg.ObjectTabSS(o, self, filepath, author_id = author_id)

                sprite_tab = wdg.SpriteTab(self, object_tab)

                self.object_tabs.addTab(object_tab, name)
                self.object_tabs.setCurrentWidget(object_tab)
                self.sprite_tabs.addTab(sprite_tab,  f"{name} (locked)")
                self.sprite_tabs.setCurrentWidget(sprite_tab)

    def saveObject(self):
        widget = self.object_tabs.currentWidget()

        widget.saveObject(get_path = False)

    def saveObjectAt(self):
        widget = self.object_tabs.currentWidget()

        widget.saveObject(get_path = True)



    #### Tool functions
    def selectTool(self, tool):
        if tool == self.tool:
            self.sender().setChecked(True)
            return

        self.tool_buttons[self.tool].setChecked(False)
        self.tool = tool

    def selectBrush(self, brush):
        if brush == self.brush:
            self.sender().setChecked(True)
            return

        self.brush_buttons[self.brush].setChecked(False)
        self.brush = brush

    def setBrushsize(self, val):
        self.brushsize = val

    def colorRemapTo(self):
        color_remap = self.combobox_remap_to_color.currentText()
        selected_colors = self.color_select_panel.selectedColors()

        if self.checkbox_all_views.isChecked():
            widget = self.object_tabs.currentWidget()

            widget.colorRemapToAll(color_remap, selected_colors)

        else:
            widget = self.sprite_tabs.currentWidget()

            widget.colorRemap(color_remap, selected_colors)


    def colorChangeBrightness(self, step):
        selected_colors = self.color_select_panel.selectedColors()

        if self.checkbox_all_views.isChecked():
            widget = self.object_tabs.currentWidget()

            widget.colorChangeBrightnessAll(step, selected_colors)

        else:
            widget = self.sprite_tabs.currentWidget()

            widget.colorChangeBrightness(step, selected_colors)

    def colorRemove(self):
        selected_colors = self.color_select_panel.selectedColors()

        if self.checkbox_all_views.isChecked():
            widget = self.object_tabs.currentWidget()

            widget.colorRemoveAll(selected_colors)

        else:
            widget = self.sprite_tabs.currentWidget()

            widget.colorRemove(selected_colors)

    class Tools(Enum):
        PEN = 0, 'Draw'
        ERASER = 1, 'Erase'
        EYEDROPPER = 2, 'Eyedrop'
        BRIGHTNESS = 3, 'Brightn.'
        REMAP = 4, 'Remap',
        FLOOD = 5, 'Fill'

        def __new__(cls, value, name):
            member = object.__new__(cls)
            member._value_ = value
            member.fullname = name
            return member

        def __int__(self):
            return self.value

    class Brushes(Enum):
        SOLID = 0, 'Solid'
        AIRBRUSH = 1, 'Airbrush'

        def __new__(cls, value, name):
            member = object.__new__(cls)
            member._value_ = value
            member.fullname = name
            return member

        def __int__(self):
            return self.value


def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("error catched!:")
    print("error message:\n", tb)


    sys._excepthook(exc_type, exc_value, exc_tb)
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("Error Trapper")
    msg.setText("Runtime error:")
    msg.setInformativeText(tb)
    msg.exec_()
    #sys.exit()

sys._excepthook = sys.excepthook
sys.excepthook = excepthook


def main():
    # if not QApplication.instance():
    #     app = QApplication(sys.argv)
    # else:
    #     app = QApplication.instance()

    app = QApplication(sys.argv)



    main = MainWindowUi()
    main.show()
    app.exec_()


    return main

if __name__ == '__main__':
    m = main()