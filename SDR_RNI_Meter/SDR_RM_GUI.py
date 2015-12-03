#!/usr/bin/python2
#
# Copyright 2012 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from gnuradio import blocks
from PyQt4 import Qt
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import uhd
from optparse import OptionParser
from remote_configurator import remote_configurator
import itertools
import sip
import RadioGIS
import sys

try:
    from gnuradio import qtgui
    from PyQt4 import QtGui, QtCore
    import sip
except ImportError:
    sys.stderr.write("Error: Program requires PyQt4 and gr-qtgui.\n")
    sys.exit(1)

try:
    from gnuradio import channels
except ImportError:
    sys.stderr.write("Error: Program requires gr-channels.\n")
    sys.exit(1)

class dialog_box(QtGui.QWidget):
    def __init__(self, header, display, control):
        QtGui.QWidget.__init__(self, None)
        self.setWindowTitle('SDR RNI Meter')
	self.showMaximized()

        self.vertlayout = QtGui.QVBoxLayout(self)
        self.vertlayout.addWidget(header)
        self.body = QtGui.QWidget()
        self.boxlayout = QtGui.QHBoxLayout()
        self.boxlayout.addWidget(control, 1)
        self.boxlayout.addWidget(display)
        self.body.setLayout(self.boxlayout)
        self.vertlayout.addWidget(self.body)


class header(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setWindowTitle('Header')

        self.hbox = QtGui.QHBoxLayout(self)
        self.image = QtGui.QLabel()
        self.image.setPixmap(QtGui.QPixmap(QtCore.QString.fromUtf8('image.jpeg')))
        self.hbox.addWidget(self.image)
        self.title = QtGui.QLabel()
        font = QtGui.QFont( "Helvetica", 30, QtGui.QFont.Bold)
        self.title.setText("SDR RNI Meter")
        self.title.setFont(font)
        self.hbox.addWidget(self.title)

class display_box(QtGui.QWidget):
    def __init__(self, plot_handler, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setWindowTitle('Display')

        self.vbox = QtGui.QVBoxLayout(self)
        self.vbox.addWidget(plot_handler)

class control_box(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setMaximumWidth(300)
        self.setWindowTitle('Control Panel')

        self.tabs = QtGui.QTabWidget()
        self.tab1 = QtGui.QWidget()
        self.tab2 = QtGui.QWidget()

        self.startButton = QtGui.QPushButton("Iniciar")
        self.connect(self.startButton, QtCore.SIGNAL('clicked()'), self.send_start_signal)

        self.stopButton = QtGui.QPushButton("Parar")
        self.connect(self.stopButton, QtCore.SIGNAL('clicked()'), self.send_stop_signal)

        self.hbox = QtGui.QHBoxLayout()
        self.hbox.addWidget(self.startButton)
        self.hbox.addWidget(self.stopButton)

        self.vbox = QtGui.QVBoxLayout(self)
        self.vbox_2 = QtGui.QWidget()
        self.vbox_2.setLayout(self.hbox)
        self.vbox.addWidget(self.vbox_2)

        self.conf_an = QtGui.QFormLayout()
        self.conf_usrp = QtGui.QFormLayout()

        self.sel_fi = QtGui.QLineEdit(self)
        self.sel_fi.setMinimumWidth(100)
        self.conf_an.addRow("Frecuencia Inicial:", self.sel_fi)
        self.connect(self.sel_fi, QtCore.SIGNAL("editingFinished()"),
                     self.fi_edit_text)

        self.sel_sc = QtGui.QLineEdit(self)
        self.sel_sc.setMinimumWidth(100)
        self.conf_an.addRow("N. Barridos:", self.sel_sc)
        self.connect(self.sel_sc, QtCore.SIGNAL("editingFinished()"),
                     self.sc_edit_text)

        self.sel_t = QtGui.QLineEdit(self)
        self.sel_t.setMinimumWidth(100)
        self.conf_an.addRow("tiempo de barrido [s]:", self.sel_t)
        self.connect(self.sel_t, QtCore.SIGNAL("editingFinished()"),
                     self.t_edit_text)

        f_dsp = 32000000
        ab_stop = 100000
        ab = [str(i) for i in itertools.takewhile(lambda x: x > ab_stop, (f_dsp/2**i for i in range(100)))]
        self.sel_ab = QtGui.QComboBox(self)
        self.sel_ab.addItems(ab)
        self.sel_ab.setMinimumWidth(100)
        self.conf_an.addRow("Ancho de Banda:", self.sel_ab)
        self.connect(self.sel_ab, QtCore.SIGNAL("editingFinished()"),
                     self.ab_edit_text)

        self.sel_ganancia = QtGui.QLineEdit(self)
        self.sel_ganancia.setMinimumWidth(100)
        self.conf_an.addRow("Ganancia:", self.sel_ganancia)
        self.connect(self.sel_ganancia, QtCore.SIGNAL("editingFinished()"),
                     self.ganancia_edit_text)

        self.sel_ventana = QtGui.QComboBox(self)
        ventanas = ["Bartlett",
                  "Blackman",
                  "Blackman Harris",
                  "Flat top",
                  "Hamming",
                  "Hanning",
                  "Kaiser",
                  "Rectangular"]
        self.sel_ventana.addItems(ventanas)
        self.sel_ventana.setMinimumWidth(100)
        self.conf_an.addRow("Ventana:", self.sel_ventana)
        self.connect(self.sel_ventana, QtCore.SIGNAL("currentTextChanged(const QString & text)"),
                     self.ventana_edit_text)
        self.sel_ventana.currentIndexChanged.connect(self.ventana_edit_text)

        self.sel_base = QtGui.QComboBox(self)
        bases = ["Exponencial Compleja",
                  "Triangular",
                  "Potencia",
                   "Binomial"]
        self.sel_base.addItems(bases)
        self.sel_base.setMinimumWidth(100)
        self.conf_an.addRow("Base:", self.sel_base)
        self.connect(self.sel_base, QtCore.SIGNAL("currentTextChanged(const QString & text)"),
                     self.base_edit_text)
        self.sel_base.currentIndexChanged.connect(self.base_edit_text)

        self.sel_escala = QtGui.QComboBox(self)
        escalas = ["dBm",
                  "Lineal"]
        self.sel_escala.addItems(escalas)
        self.sel_escala.setMinimumWidth(100)
        self.conf_an.addRow("Escala:", self.sel_escala)

        self.sel_IP = QtGui.QLineEdit(self)
        self.sel_IP.setMinimumWidth(100)
        self.conf_usrp.addRow("IP:", self.sel_IP)
        self.connect(self.sel_IP, QtCore.SIGNAL("editingFinished()"),
                     self.IP_edit_text)

        self.sel_puerto = QtGui.QLineEdit(self)
        self.sel_puerto.setMinimumWidth(100)
        self.conf_usrp.addRow("Puerto:", self.sel_puerto)
        self.connect(self.sel_puerto, QtCore.SIGNAL("editingFinished()"),
                     self.puerto_edit_text)

        self.sel_y1 = QtGui.QLineEdit(self)
        self.sel_y1.setMaximumWidth(50)
        self.conf_an.addRow("y1:", self.sel_y1)
        self.connect(self.sel_y1, QtCore.SIGNAL("editingFinished()"),
                     self.y1_edit_text)

        self.sel_y0 = QtGui.QLineEdit(self)
        self.sel_y0.setMaximumWidth(50)
        self.conf_an.addRow("y0:", self.sel_y0)
        self.connect(self.sel_y0, QtCore.SIGNAL("editingFinished()"),
                     self.y0_edit_text)

        self.tab1.setLayout(self.conf_an)
        self.tab2.setLayout(self.conf_usrp)
        self.vbox.addWidget(self.tabs)

        self.tabs.addTab(self.tab1, "Medidor de RNI")
        self.tabs.addTab(self.tab2, "USRP")

    def attach_signal(self, signal):
        self.signal = signal
        self.sel_IP.setText(QtCore.QString("%1").arg(self.signal.get_IP()))
        self.sel_puerto.setText(QtCore.QString("%1").arg(self.signal.get_port()))
        self.sel_fi.setText(QtCore.QString("%1").arg(self.signal.get_fi()))
        self.sel_sc.setText(QtCore.QString("%1").arg(self.signal.get_sc()))
        self.sel_t.setText(QtCore.QString("%1").arg(self.signal.get_t()))
        self.sel_ganancia.setText(QtCore.QString("%1").arg(self.signal.get_gan()))
        self.sel_y0.setText(QtCore.QString("%1").arg(self.signal.get_y0()))
        self.sel_y1.setText(QtCore.QString("%1").arg(self.signal.get_y1()))

    def send_start_signal(self):
        try:
            conf_ini = {"gan": self.signal.get_gan(), "fi": self.signal.get_fi(), "ab": self.signal.get_ab(), "sc": self.signal.get_sc(), "t": self.signal.get_t(), "start": True}
            self.signal.get_dino().send(conf_ini)
            print("Application successfully started")
        except:
            print "Something went wrong while starting the application"

    def send_stop_signal(self):
        try:
            self.signal.get_dino().send({"stop": True})
            print("Application successfully stopped")
        except:
            print "Unable to stop the application D:"

    def IP_edit_text(self):
        try:
	    newIP = str(self.sel_IP.text())
            self.signal.set_IP(newIP)
        except ValueError:
	    print("Wrong IP format")

    def puerto_edit_text(self):
        try:
	    newPuerto = str(self.sel_IP.text())
            self.signal.set_puerto(newPuerto)
        except ValueError:
	    print("Invalid port")

    def ab_edit_text(self):
        try:
	    newab = float(self.sel_ab.currentText())
            self.signal.set_ab(newab)
        except ValueError:
	    print("Unsupported ab value")

    def fi_edit_text(self):
        try:
	    newfi = float(self.sel_fi.text())
            self.signal.set_fi(newfi)
        except ValueError:
	    print("Invalid center frequency")
        self.sel_fi.setText("{0:.0f}".format(self.signal.get_fi()))

    def sc_edit_text(self):
        try:
	    newsc = float(self.sel_sc.text())
            self.signal.set_sc(newsc)
        except ValueError:
	    print("Invalid center frequency")
        self.sel_sc.setText("{0:.0f}".format(self.signal.get_sc()))

    def t_edit_text(self):
        try:
	    newt = float(self.sel_t.text())
            self.signal.set_t(newt)
        except ValueError:
	    print("Invalid center frequency")
        self.sel_sc.setText("{0:.0f}".format(self.signal.get_t()))

    def ganancia_edit_text(self):
        try:
	    newGanancia = float(self.sel_ganancia.text())
            self.signal.set_gan(newGanancia)
        except ValueError:
	    print("Gain out of range")

    def ventana_edit_text(self):
        try:
	    newVentana = str(self.sel_ventana.currentText())
            self.signal.set_ventana(newVentana)
        except ValueError:
	    print("Something went wrong with the selected window")

    def base_edit_text(self):
        try:
	    newBase = str(self.sel_base.currentText())
            self.signal.set_base(newBase)
        except ValueError:
	    print("Something went wrong with the selected base")

    def y0_edit_text(self):
        try:
	    newy0 = float(self.sel_y0.text())
            self.signal.set_y0(newy0)
        except ValueError:
	    print("Invalid center frequency")

    def y1_edit_text(self):
        try:
	    newy1 = float(self.sel_y1.text())
            self.signal.set_y1(newy1)
        except ValueError:
	    print("Invalid center frequency")


class sdr_rni_meter(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self)

        self.qapp = QtGui.QApplication(sys.argv)
        ss = open('style.qss')
        sstext = ss.read()
        ss.close()
        self.qapp.setStyleSheet(sstext)

        ##################################################
        # Variables
        ##################################################
        self.port = port = 9999
        self.gan = gan = 10
        self.fi = fi = 70000000
        self.sc = sc = 8
        self.t = t = 1
        self.ab = ab = 32000000
        self.N = N = 1024
        self.m = m = (sc - fi) / ab
        self.IP = IP = "192.168.1.102"
        self.Antena = Antena = "RX2"
	self.remote_IP = "192.168.1.101"
        self.dino = remote_configurator(self.remote_IP, self.port)
        self.ventana = "Hamming"
        self.base = "exponencial"
        self.y0 = y0 = -100
        self.y1 = y1 = 0

        ##################################################
        # Blocks
        ##################################################
        self.qtgui_vector_sink_f_0 = qtgui.vector_sink_f(
            N * sc,
            fi,
            ab / N,
            "Frecuencia",
            "Amplitud",
            "",
            1 # Number of inputs
        )
        self.qtgui_vector_sink_f_0.set_update_time(0.10)
        self.qtgui_vector_sink_f_0.set_y_axis(y0, y1)
        self.qtgui_vector_sink_f_0.enable_autoscale(False)
        self.qtgui_vector_sink_f_0.enable_grid(True)
        self.qtgui_vector_sink_f_0.set_x_axis_units("Hz")
        self.qtgui_vector_sink_f_0.set_y_axis_units("dBm")
        self.qtgui_vector_sink_f_0.set_ref_level(0)
        
        labels = ["", "", "", "", "",
                  "", "", "", "", ""]
        widths = [1, 1, 1, 1, 1,
                  1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
                  "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]
        for i in xrange(1):
            if len(labels[i]) == 0:
                self.qtgui_vector_sink_f_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_vector_sink_f_0.set_line_label(i, labels[i])
            self.qtgui_vector_sink_f_0.set_line_width(i, widths[i])
            self.qtgui_vector_sink_f_0.set_line_color(i, colors[i])
            self.qtgui_vector_sink_f_0.set_line_alpha(i, alphas[i])
        
        self._qtgui_vector_sink_f_0_win = sip.wrapinstance(self.qtgui_vector_sink_f_0.pyqwidget(), Qt.QWidget)
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_float*1, N)
        self.udp_source_0 = blocks.udp_source(gr.sizeof_float*1, IP, port, 1472, True)
        self.RadioGIS_dynamic_sink_0 = RadioGIS.dynamic_sink(N, sc)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.RadioGIS_dynamic_sink_0, 0), (self.qtgui_vector_sink_f_0, 0))
        self.connect((self.udp_source_0, 0), (self.blocks_stream_to_vector_0, 0))
        self.connect((self.blocks_stream_to_vector_0, 0), (self.RadioGIS_dynamic_sink_0, 0))

        self.ctrl_win = control_box()
        self.head_win = header()
        self.ctrl_win.attach_signal(self)

        self.main_box = dialog_box(self.head_win, display_box(self._qtgui_vector_sink_f_0_win), self.ctrl_win)
        self.main_box.show()

    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "SDR_SA_GUI")
        self.settings.setValue("geometry", self.saveGeometry())
        event.accept()

    def get_dino(self):
        return self.dino

    def get_port(self):
        return self.port

    def set_port(self, port):
        self.port = port

    def get_gan(self):
        return self.gan

    def set_gan(self, gan):
        self.gan = gan
	self.dino.send({"gan": self.gan})

    def get_fi(self):
        return self.fi

    def set_fi(self, fi):
        if(34000000 < fi < 6016000000 - self.ab / 2):
            self.fi = fi
            self.update_x_axis()
            self.dino.send({"fi": self.fi})

    def get_ab(self):
        return self.ab

    def set_ab(self, ab):
        self.ab = ab
        self.update_x_axis()
	self.dino.send({"ab": self.ab})

    def get_N(self):
        return self.N

    def set_N(self, N):
        self.N = N

    def get_sc(self):
        return self.sc

    def set_sc(self, sc):
        self.sc = sc
        self.update_x_axis()
        self.dino.send({"sc": self.sc})
        self.RadioGIS_dynamic_sink_0.set_n(self.sc)

    def get_t(self):
        return self.t

    def set_t(self, t):
        self.t = t
        self.dino.send({"t": self.t})

    def get_IP(self):
        return self.IP

    def set_IP(self, IP):
        self.IP = IP
	self.dino.send({"IP": self.IP})

    def get_Antena(self):
        return self.Antena

    def set_Antena(self, Antena):
        self.Antena = Antena

    def get_ventana(self):
        return self.ventana

    def set_ventana(self, ventana):
        self.ventana = ventana
	self.dino.send({"ventana": self.ventana})

    def get_base(self):
        return self.base

    def set_base(self, base):
        self.base = base
	self.dino.send({"base": self.base})

    def get_y0(self):
        return self.y0

    def set_y0(self, y0):
        self.y0 = y0
        self.update_y_axis()

    def get_y1(self):
        return self.y1

    def set_y1(self, y1):
        self.y1 = y1
        self.update_y_axis()

    def update_x_axis(self):
        self.qtgui_vector_sink_f_0.set_x_axis(self.fi, self.fi + self.sc * self.ab)

    def update_y_axis(self):
        self.qtgui_vector_sink_f_0.set_y_axis(self.y0, self.y1)

if __name__ == "__main__":
    tb = sdr_rni_meter();
    tb.start()
    tb.qapp.exec_()
    tb.stop()
