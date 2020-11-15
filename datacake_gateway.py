import pycom
from network import LTE
import config
import time
from time import sleep
import machine
from machine import Timer
from machine import RTC
import sys
import socket

class DatacakeGateway:

    def machine_callback(self, arg):
        evt = machine.events()
        if (evt & machine.PYGATE_START_EVT):
            self.machine_state = config.GATEWAY_STATE_OK
            pycom.rgbled(config.RGB_GATEWAY_OK)
        elif (evt & machine.PYGATE_ERROR_EVT):
            self.machine_state = config.GATEWAY_STATE_ERROR
            pycom.rgbled(config.RGB_GATEWAY_ERROR)
        elif (evt & machine.PYGATE_STOP_EVT):
            self.machine_state = config.GATEWAY_STATE_STOP
            pycom.rgbled(config.RGB_GATEWAY_STOP)

    def __init__(self):

        print("Init: Initialization of Gateway class...")

        # Machine
        machine.callback(trigger = (
            machine.PYGATE_START_EVT | 
            machine.PYGATE_STOP_EVT | 
            machine.PYGATE_ERROR_EVT
            ), handler=self.machine_callback)        
        self.machine_state = 0

        # LTE
        self.lte = LTE()
        self.lte_connection_state = 0

        # RTC
        self.rtc = RTC()
        
        # Gateway
        # Read the GW config file from Filesystem
        self.gateway_config_file = None
        
        # Timers
        self.rgb_breathe_timer = Timer.Chrono()

        # Startup
        # Should be called outside init
        # self.start_up()

    def lte_event_callback(self, arg):
        #self.blink_rgb_led(5, 0.25, config.RGB_LTE_ERROR)
        #self.lte.deinit()
        #machine.reset()
        print("\n\n\n#############################################################")
        print("CB LTE Callback Handler")
        ev = arg.events() # NB: reading the events clears them
        t = time.ticks_ms()
        print("CB", t, time.time(), ev, time.gmtime())
        self.blink_rgb_led(3, 0.25, config.RGB_LTE_ERROR)
        if ev & LTE.EVENT_COVERAGE_LOSS:
            print("CB", t, "coverage loss")
        if ev & LTE.EVENT_BREAK:
            print("CB", t, "uart break signal")
        try:
            self.lte.pppsuspend()
            if not self.lte.isattached():
                print("not attached ... reattach")
                self.lte.detach()
                self.init_lte()
            else:
                print("attached ... resume")
                self.lte.pppresume()
        except Exception as ex:
            sys.print_exception(ex)            
        print("#############################################################\n\n\n")

    def init_gateway(self):
        print("Init GW: Starting LoRaWAN Concentrator...")
        try:
            self.gateway_config_file = open(config.GW_CONFIG_FILE_PATH,'r').read()
        except Exception as e:
            print("Error opening Gateway Config: {}".format(e))
            # TODO: Handle Error
            return False
        else:
            machine.pygate_init(self.gateway_config_file)
            print("Init GW: LoRaWAN Concentrator UP!")
            return True

    def init_rtc(self):     
        print("Init RTC: Syncing RTC...")
        try:   
            self.rtc.ntp_sync(server="pool.ntp.org")
            while not self.rtc.synced():    
                self.blink_rgb_led(1, 0.25, config.RGB_RTC_IS_SYNCING, delay_end=False)      
            self.blink_rgb_led(3, 0.1, config.RGB_RTC_IS_SYNCING)
        except Exception as e:
            print("Exception syncing RTC: {}".format(e))
            return False
        else:
            print("Init RTC: Synced!")
            return True

    def init_lte(self):
        
        self.lte_connection_state = 0
        self.lte.init()
        #self.lte.lte_callback(LTE.EVENT_COVERAGE_LOSS, self.lte_event_callback)
        self.lte.lte_callback(LTE.EVENT_BREAK, self.lte_event_callback)

        while True:

            # attach LTE
            if self.lte_connection_state == 0:
                print("Init LTE: Attaching LTE...")
                self.lte.attach(band=config.LTE_BAND, apn=config.LTE_APN)
                while not self.lte.isattached():
                    self.blink_rgb_led(1, 0.25, config.RGB_LTE_IS_ATTACHING, delay_end=False)
                self.blink_rgb_led(3, 0.1, config.RGB_LTE_IS_ATTACHING)
                self.lte_connection_state += 1
                print("Init LTE: Attached!")
            
            # connect LTE
            if self.lte_connection_state == 1:
                print("Init LTE: Connecting LTE...")
                self.lte.connect()
                while not self.lte.isconnected():
                    self.blink_rgb_led(1, 0.25, config.RGB_LTE_IS_CONNECTING, delay_end=False)
                self.blink_rgb_led(3, 0.1, config.RGB_LTE_IS_CONNECTING)
                self.lte_connection_state += 1   
                print("Init LTE: Connected!")

            # done
            if self.lte_connection_state == 2:
                return True         

    def blink_rgb_led(self, times, speed, color_on, color_off=config.RGB_OFF, delay_end=True):
        for index in range(times):
            pycom.rgbled(config.RGB_OFF)
            time.sleep(speed)
            pycom.rgbled(color_on)
            time.sleep(speed)  
        pycom.rgbled(config.RGB_OFF)
        if delay_end is True:
            time.sleep(0.1)

    def start_up(self):
        print("Start Up: Now starting up Gateway...")
        self.init_lte()
        self.init_rtc()
        self.init_gateway()
        #self.main_loop()

    def main_loop(self):
        
        # Start Timers
        self.rgb_breathe_timer.start()

        while True:

            if self.rgb_breathe_timer.read() > config.TIMER_RGB_BREATHE_INTERVAL:
                self.rgb_breathe_timer.reset()

