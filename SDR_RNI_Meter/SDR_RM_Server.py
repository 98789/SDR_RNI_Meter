#!/usr/bin/env python2
##################################################
# GNU Radio Python Flow Graph
# Title: SDR - SA Server
# Generated: Fri Oct 16 18:12:32 2015
##################################################

from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import gr
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from gnuradio.fft import window
from optparse import OptionParser
from remote_configurator import remote_configurator
import RadioGIS
import time


class SDR_SA_Server(gr.top_block):

    def __init__(self, gan=10, fi=70000000, ab=32000000, sc=10, t=1):
        gr.top_block.__init__(self, "SDR RNI Meter")

        ##################################################
        # Variables
        ##################################################
        self.port = port = 9999
        self.gan = gan
        self.fi = fi
        self.ab = ab
        self.fc = fc = fi + ab / 2
        self.N = N = 1024
        self.sc = sc
        self.t = t
        self.IP = IP = "192.168.1.102"
        self.Antena = Antena = "RX2"
        self.ventana = ventana = window.blackmanharris
        self.base = base = "exponencial"
        self.gps = gps = "n: 0.0 deg 0.0 deg 0.0m lat/lon/al"

        ##################################################
        # Blocks
        ##################################################
        self.src = uhd.usrp_source(
        	",".join(("", "")),
        	uhd.stream_args(
        		cpu_format="fc32",
        		channels=range(1),
        	),
        )
        self.src.set_samp_rate(ab)
        self.src.set_center_freq(fc, 0)
        self.src.set_gain(gan, 0)
        self.src.set_antenna("RX2", 0)
        self.dbm = RadioGIS.dbm()
        self.blocks_vector_to_stream_0 = blocks.vector_to_stream(gr.sizeof_float*1, N)
        self.blocks_stream_to_vector_0 = blocks.stream_to_vector(gr.sizeof_gr_complex*1, N)
        self.blocks_complex_to_mag_0 = blocks.complex_to_mag(N)
        self.RadioGIS_time_averager_0 = RadioGIS.time_averager(N, t)
        self.udp_sink_0 = blocks.udp_sink(gr.sizeof_float*1, IP, port, 1472, True)
        self.RadioGIS_fft_0 = RadioGIS.fft(N, base, (ventana(N)))

        ##################################################
        # Connections
        ##################################################
        self.connect((self.RadioGIS_fft_0, 0), (self.blocks_complex_to_mag_0, 0))
        self.connect((self.blocks_complex_to_mag_0, 0), (self.RadioGIS_time_averager_0, 0))
        self.connect((self.blocks_stream_to_vector_0, 0), (self.RadioGIS_fft_0, 0))
        self.connect((self.RadioGIS_time_averager_0, 0), (self.blocks_vector_to_stream_0, 0))
        self.connect((self.blocks_vector_to_stream_0, 0), (self.dbm, 0))
        self.connect((self.dbm, 0), (self.udp_sink_0, 0))
        self.connect((self.src, 0), (self.blocks_stream_to_vector_0, 0))

    def get_gps(self):
        gps_position = self.src.get_mboard_sensor("gps_position").to_pp_string()[11:-1]
        self.gps = str(gps_position)
        return self.gps

    def get_port(self):
        return self.port

    def set_port(self, port):
        self.port = port

    def get_gan(self):
        return self.gan

    def set_gan(self, gan):
        self.gan = gan
        self.src.set_gain(self.gan, 0)

    def get_fi(self):
        return self.fi

    def set_fi(self, fi):
        f_range = self.src.get_freq_range(0)
        if f_range.start() < fi < f_range.stop():
            self.fi = fi
            self.set_fc()

    def get_sc(self):
        return self.sc

    def set_sc(self):
        self.sc = sc

    def get_fc(self):
        return self.fc

    def set_fc(self):
        self.fc = [self.fi + x * self.ab for x in range(self.sc)]
        for freq in self.fc:
            time.sleep(self.t)
            self.src.set_center_freq(freq, 0)

    def get_t(self):
        return self.t

    def set_t(self, t):
        self.t = t

    def get_ab(self):
        return self.ab

    def set_ab(self, ab):
        self.ab = ab
        self.src.set_samp_rate(self.ab)

    def get_N(self):
        return self.N

    def set_N(self, N):
        self.N = N

    def get_IP(self):
        return self.IP

    def set_IP(self, IP):
        self.IP = IP

    def get_Antena(self):
        return self.Antena

    def set_Antena(self, Antena):
        self.Antena = Antena
        self.src.set_antenna(self.Antena, 0)

    def get_ventana(self):
        return self.ventana

    def set_ventana(self, ventana):
        self.ventana = getattr(window, ventana.replace(" ", "").lower())
        if ventana != "Kaiser":
            self.RadioGIS_fft_0.set_window(self.ventana(self.N))
        else:
            self.RadioGIS_fft_0.set_window(self.ventana(self.N, 6.76))

    def get_base(self):
        return self.base

    def set_base(self, base):
        self.base = base.split()[0].lower()
        self.RadioGIS_fft_0.set_W(self.base)


if __name__ == '__main__':
    parser = OptionParser(option_class=eng_option, usage="%prog: [options]")
    (options, args) = parser.parse_args()
    dino = remote_configurator("192.168.1.101", 9999)
    dino.bind()
    while 1:
        data = dino.listen({"gps":tb.get_gps()})
        print(data)
        if data.get("start"):
            tb = SDR_SA_Server(data.get("gan"), data.get("fi"), data.get("ab"), data.get("sc"), data.get("t"))
            tb.start()
            break
    start_time = time.time()
    print(start_time)
    tb.set_fi(tb.get_fi())
    while 1:
    	data = dino.listen({"gps":tb.get_gps()})
        if "gan" in data:
            tb.set_gan(data.get("gan"))
        elif "fi" in data:
            tb.set_fi(data.get("fi"))
        elif "sc" in data:
            tb.set_sc(data.get("sc"))
        elif "ab" in data:
            tb.set_ab(data.get("ab"))
        elif "IP" in data:
            tb.set_IP(data.get("IP"))
        elif "base" in data:
            tb.set_base(data.get("base"))
        elif "t" in data:
            tb.set_t(data.get("t"))
        elif "ventana" in data:
            tb.set_ventana(data.get("ventana"))
        elif data.get("stop"):
            break       
    tb.stop()
    tb.wait()
    stop_time = time.time() - start_time
    print(stop_time)
