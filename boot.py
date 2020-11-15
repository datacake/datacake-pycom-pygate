import pycom
import machine
import socket

socket.dnsserver(0, '8.8.8.8')
socket.dnsserver(1, '4.4.4.4')

#pycom.nvs_set('pybytes_debug', 99)
pycom.heartbeat(False)
#pycom.pybytes_on_boot(True)
pycom.wifi_on_boot(False)
#pycom.lte_modem_en_on_boot(True)

machine.main('main.py')