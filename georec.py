# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Georec
                                 A QGIS plugin
 Geo recommendation
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-06-05
        git sha              : $Format:%H$
        copyright            : (C) 2019 by GiSGeeks
        email                : HanwGeek@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from qgis.gui import *
from qgis.core import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .ExtractToPoints_dialog import *
import os.path
from .IDW_Interpolation_dialog import IDW_InterpolationDialog
from .interpolation import Interpolation
from .georec_train_dlg import GeorecTrainDlg
from .georec_train_param_dlg import GeorecTrainParamDlg
from .georec_res_dlg import GeorecResDlg
from .georec_app_dlg import GeorecAppDlg
import xgboost as xgb
from xgboost import plot_tree
import numpy as np
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.metrics import explained_variance_score
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class Georec:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Georec_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Geo Rec')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Georec', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.add_action(
          os.path.join(os.path.dirname(__file__), 'raster.png'),
          text=self.tr(u'vector to raster'),
          callback=self.vector_to_raster,
          parent=self.iface.mainWindow())

        self.add_action(
          os.path.join(os.path.dirname(__file__), 'vector.png'),
          text=self.tr(u'raster to vector'),
          callback=self.raster_to_vector,
          parent=self.iface.mainWindow())

        self.add_action(
          os.path.join(os.path.dirname(__file__), 'train.png'),
          text=self.tr(u'train'),
          callback=self.train,
          parent=self.iface.mainWindow())

        self.add_action(
          os.path.join(os.path.dirname(__file__), 'app.png'),
          text=self.tr(u'Application'),
          callback=self.app,
          parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        self.figure = plt.figure(facecolor='#F0F0F0') #可选参数,facecolor为背景颜色
        self.canvas = FigureCanvas(self.figure)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Geo Rec'),
                action)
            self.iface.removeToolBarIcon(action)

    def vector_to_raster(self):
        if self.first_start == True:
            self.first_start = False
        self.dlg1 = IDW_InterpolationDialog()
        self.interpolation = Interpolation()
        # show the dialog
        self.dlg1.show()
        #init the dialog
        self.init_input()
        
        self.insert_layers_into_combobox(self.dlg1.comboBox_layers)
        self.insert_attributes_into_table()
          
        #connect signals and slots 
        self.dlg1.pushButton_start.clicked.connect(self.start_interpolation)
        self.dlg1.comboBox_layers.currentIndexChanged.connect(self.insert_attributes_into_table)
        self.dlg1.pushButton_output.clicked.connect(self.choose_output_directory)
        # Run the dialog event loop
        result = self.dlg1.exec_()

    def init_input(self):
        self.dlg1.comboBox_layers.clear()
        self.dlg1.tableWidget_attributes.setRowCount(0)
        self.dlg1.lineEdit_output.setText("")
        self.dlg1.spinBox_pixelSize.setValue(0)
        self.dlg1.progressBar.setValue(0)
            
    def insert_layers_into_combobox(self, combobox):
        """Populate the layer-combobox during start of the plugin."""
        combobox.clear()
        self.populate_layer_list(self.iface, combobox)
    
    def populate_layer_list(self, iface, combobox):
        #populate the instance variable
        self.layers= [layer for layer in QgsProject.instance().mapLayers().values()] 
        
        #populate the combobox
        for layer in self.layers:
            combobox.addItem(layer.name())   
        
    def insert_attributes_into_table(self):
        """Populate the table with the attributes of the selected layer."""
        self.dlg1.tableWidget_attributes.setRowCount(0)
        self.populate_attribute_list(self.dlg1.comboBox_layers.currentText(), self.dlg1.tableWidget_attributes)
        
    def populate_attribute_list(self, layername, table):
        #clear the table
        table.clearSpans()
        
        #find the selected layer
        for layer in self.layers:
            if layer.name() == layername:
                #get all fields/attributes of the selected layer
                fields = layer.fields()
                fieldnames = [field.name() for field in fields]
                
                #populate the table
                for fieldname in fieldnames:
                    current_row = table.rowCount()
                    table.insertRow(current_row)
                    table.setRowCount(current_row + 1)
                    
                    #insert name of the attribute
                    table.setItem(current_row, 1, QTableWidgetItem(fieldname))
                
                    #insert the chechbox
                    checkbox_item = QTableWidgetItem()
                    checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    checkbox_item.setCheckState(Qt.Unchecked)
                    table.setItem(current_row, 0, QTableWidgetItem(checkbox_item))
                break
       
    def choose_output_directory(self):
        """Opens a file dialog to choose a directory for storing the output of this plugin."""
        #load settings
        s = QSettings()
        output_from_settings = str(s.value("qgis_batch-interpolation_output", ""))
        
        #open file dialog and store the selected path in the settings
        filename = QFileDialog.getExistingDirectory(self.dlg1, "Select Output Directory", output_from_settings, QFileDialog.ShowDirsOnly)
        self.dlg1.lineEdit_output.setText(filename)
        s.setValue("qgis_batch-interpolation_output", filename)
         
    def start_interpolation(self):
        """Start the interpolation."""
        #store infomration in the settings
        s = QSettings()
        s.setValue("qgis_batch-interpolation_output", self.dlg1.lineEdit_output.text())
        #QMessageBox.about(None,"sss","1")
        
        #check whether an output path is inserted
        if self.dlg1.lineEdit_output.text() == "":
            self.iface.messageBar().pushMessage("Info", "No directory choosed for storing the output.")
            return True
        
        #check whether the pixel size is unequal 0
        if self.dlg1.spinBox_pixelSize.value() == 0:
            self.iface.messageBar().pushMessage("Info", "The pixel size of the resulting raster layer has to be unequal 0.")
            return True
        
        #call the start-method
        try:
            #QMessageBox.about(None,"sss","2")
            table=self.dlg1.tableWidget_attributes
            layer_name=self.dlg1.comboBox_layers.currentText()
            out_dir=self.dlg1.lineEdit_output.text()
            resolution=self.dlg1.spinBox_pixelSize.value()
            pb=self.dlg1.progressBar
            gb_input=self.dlg1.groupBox_input
            gb_settings=self.dlg1.groupBox_setting
            self.start_batch_process(table, layer_name, out_dir, resolution, pb, gb_input, gb_settings)
            #QMessageBox.about(None,"sss","6")
        except:
            self.iface.messageBar().pushMessage("Error", "Interpolation failed. Look into the QGIS-Log and/or the python-window for the stack trace.")
            #QgsMessageLog.logMessage(traceback.print_exc())
    
    def start_batch_process(self, table, layer_name, out_dir, resolution, pb, gb_input, gb_settings):
        #QMessageBox.about(None,"sss","3")
        #disable gui elements during processing
        gb_input.setEnabled(False)
        gb_settings.setEnabled(False)
        
        #init the progressbar
        pb.setValue(0)
        max = 0
        
        for row in range(0, table.rowCount()):
            if table.item(row, 0).checkState() == Qt.Checked:
                max += 1
    
        pb.setMaximum(max)
        
        QApplication.processEvents()
        
        #get the layer with the specified name
        layer = None
        for layers_entry in self.layers:
            if layers_entry.name() == layer_name:
                layer = layers_entry
                break
        
        #iterate over all rows and detect the checked rows
        for row in range(0, table.rowCount()):
            if table.item(row, 0).checkState() == Qt.Checked:
                attribute = table.item(row, 1).text()
                #get the index of the attribute
                attr_index = 0
                fields = layer.fields()
                for field in fields:
                    if field.name() == attribute:
                        break
                    attr_index += 1
            
                #interpolate the layer with the current attribute
                self.interpolation.interpolation(layer, attr_index, attribute, out_dir, resolution)
                pb.setValue(pb.value() + 1)
                QApplication.processEvents()
        
        #enable gui elements after processing
        gb_input.setEnabled(True)
        gb_settings.setEnabled(True)
    
    def raster_to_vector(self):
        dialog = ExtractToPointsDialog(self.iface)
        dialog.exec_()
        
    def train(self):
      if self.first_start == True:
          self.first_start = False
      self.dlg = GeorecTrainDlg()

      # Init params
      self.dlg.layerComboBox.clear()
      self.layers = list(QgsProject.instance().mapLayers().values())
      for layer in self.layers:
        if layer.type() == layer.VectorLayer:
          self.dlg.layerComboBox.addItem(layer.name())

      self.dlg.layerComboBox.currentIndexChanged.connect(self._get_layer_field)
      self._get_layer_field()
      #self.dlg.layerAttrView.setModel(self.model)
      self.featMap = {}

      # show the dialog
      self.dlg.show()
      # Run the dialog event loop
      result = self.dlg.exec_()
  
      if result:
        self.featLayer = self.layers[self.dlg.layerComboBox.currentIndex()]
        self.target = self.dlg.fieldComboBox.currentText()
        self.featField = [f.name() for f in self.featLayer.fields() if f.name() != self.target]
        
        featCount = self.featLayer.featureCount()
        self.train_data = np.zeros([featCount, len(self.featField) + 2])
        self.target_data = np.zeros([featCount, 1])
        self.featIter = self.featLayer.getFeatures()

        self._gen_train_data()
        self.paramDlg = GeorecTrainParamDlg()
        self.paramDlg.show()
        res = self.paramDlg.exec_()
        if res:
          self._train()

          self.testDlg = GeorecResDlg()
          self.testDlg.editAcc.setText(str(self.accuracy)[:6])
          self.testDlg.layout.addWidget(self.canvas)

          from xgboost import plot_importance
          os.environ["PATH"] += os.pathsep + 'E:\qgis3.2\graphviz-2.38\release\bin'
          
          ax = self.figure.add_axes([0.1,0.1,0.8,0.8])
          fig = plot_importance(self.xlf, ax=ax)

          self.canvas.draw()
          self.testDlg.editAcc.setFocusPolicy(QtCore.Qt.NoFocus)
          self.testDlg.show()
          self.testDlg.exec_()

    def app(self):
      # Init gui
      if self.first_start == True:
        self.first_start = False
        

      # Init params
      self.appDlg = GeorecAppDlg()
      self.appDlg.layerComboBox.clear()
      self.layers = list(QgsProject.instance().mapLayers().values())
      for layer in self.layers:
        if layer.type() == layer.VectorLayer:
          self.appDlg.layerComboBox.addItem(layer.name())

      self.appDlg.show()
      # Run the dialog event loop
      result = self.appDlg.exec_()
  
      if result:
        self.appLayer = self.layers[self.appDlg.layerComboBox.currentIndex()]
        self.app_data = np.zeros([self.appLayer.featureCount(), len(self.featField) + 2])

        self._gen_app_data()
        self.pred = self.xlf.predict(self.app_data)

        scoreField = QgsField()
        scoreField.setName('Score')
        scoreField.setType(QVariant.Double)
        self.appLayer.startEditing()
        self.appLayer.addAttribute(scoreField)
        self.appLayer.commitChanges()

        self.appLayer.startEditing()
        fieldIdx = len(self.featField)
        featIter = self.appLayer.getFeatures()
        for idx, feat in enumerate(featIter):

          self.appLayer.changeAttributeValue(feat.id(), fieldIdx, float(pred[idx]))
        
        print(self.appLayer.commitChanges())

    
    def _gen_train_data(self):
      for idx, feat in enumerate(self.featLayer.getFeatures()):
        geom_point = feat.geometry().asPoint()
        self.train_data[idx][0] = geom_point.x()
        self.train_data[idx][1] = geom_point.y()
        for i, attr in enumerate(self.featField):
          if isinstance(feat[attr], str):
            self.train_data[idx][i + 2] = 0
          else:
            self.train_data[idx][i + 2] = feat[attr]
        self.target_data[idx] = feat[self.target]

    def _get_layer_field(self):
      self.dlg.fieldComboBox.clear()
      for field in self.layers[self.dlg.layerComboBox.currentIndex()].fields():
        self.dlg.fieldComboBox.addItem(field.name())

    def _gen_app_data(self):
      for idx, feat in enumerate(self.appLayer.getFeatures()):
        geom_point = feat.geometry().asPoint()
        self.app_data[idx][0] = geom_point.x()
        self.app_data[idx][1] = geom_point.y()
        for i, attr in enumerate(self.featField):
          if isinstance(feat[attr], str):
            self.app_data[idx][i + 2] = 0
          else:
            self.app_data[idx][i + 2] = feat[attr]

    def _train(self):
      self.xlf = xgb.XGBRegressor(max_depth=14, 
                      learning_rate=0.005, 
                      n_estimators=420, 
                      silent=True, 
                      objective='reg:linear', 
                      nthread=-1, 
                      gamma=0.5,
                      min_child_weight=1.5, 
                      max_delta_step=1, 
                      subsample=0.8, 
                      colsample_bytree=0.7, 
                      colsample_bylevel=1, 
                      reg_alpha=0.5, 
                      reg_lambda=1, 
                      scale_pos_weight=1, 
                      seed=1440, 
                      missing=None)
      self.pBar = WaitProgressDialog()
      cancelButton = QPushButton("Cancel")
      self.pBar.setCancelButton(cancelButton)
      # cancelButton.clicked.connect(self.thread.terminate)
      cancelButton.setGeometry(100, 100, 100, 100)
      self.pBar.show() 
      # self.thread.start()
      
      # Start train
      X_train, X_test, y_train, y_test = train_test_split(self.train_data,self.target_data,test_size=0.25, random_state=33)
      bst = self.xlf.fit(X_train, y_train, eval_metric='rmse', verbose=True, eval_set = [(X_test, y_test)], early_stopping_rounds=100)
      self.pBar.close()
      
      # Validation 
      y_pred = self.xlf.predict(X_test)
      self.accuracy = explained_variance_score(y_test, y_pred)

class TrainThread(QThread):
  closeTrigger = pyqtSignal()
  def __init__(self, rec, parent=None):
    super(TrainThread, self).__init__(parent)
    self.rec = rec
    self.closeTrigger.connect(self.rec.pBar.close)

  def __del__(self):
    self.wait()

  def run(self):
    print("----- thread start -----")
    self.rec._train()
    self.closeTrigger.emit()

class AppThread(QThread):
  closeTrigger = pyqtSignal()
  def __init__(self, rec, parent=None):
    super(AppThread, self).__init__(parent)
    self.rec = rec
    self.closeTrigger.connect(self.rec.pBar.close)

  def __del__(self):
    self.wait()

  def run(self):
    print("----- thread start -----")
    self.rec._train()
    self.closeTrigger.emit()

class WaitProgressDialog(QProgressDialog):
  def __init__(self, parent=None):
    super(WaitProgressDialog, self).__init__(parent)
    self.setMaximum(0)
    self.setMinimum(0)
    self.setWindowTitle("Training... ")
    self.setFixedSize(400, 100)