import zmq, datetime,  os, subprocess, sys, yaml, glob
from time import sleep
from nested_dict import nested_dict

import myinotifier,util
import sampling_scan_all as all_samp
import miscellaneous_functions as misc_func
import analysis.level0.sampling_scan_analysis as analyzer
import zmq_controler as zmqctrl

if __name__ == "__main__":
    parser = misc_func.options_run()#This will be constant for every test irrespective of the type of test
    
    #One extra option custommade just for this script - internal pulse height (calib)
    parser.add_option("-l","--LEDvolt", action="store", dest="LEDvolt",default='0', help="LED bias applied externally in mV")
    parser.add_option("-v","--overvoltage", action="store", dest="overvoltage",default='0', help="SiPM overvoltage applied externally")
 
    (options, args) = parser.parse_args()
    print(options)
    (daqsocket,clisocket,i2csocket) = zmqctrl.pre_init(options)

    injectionConfig = {
        'gain' : 1, # 0 in original
        'calib' : 0, #900 in original
        'injectedChannels' : [9, 10, 12, 28, 29, 30, 36, 37, 38, 59],
        # 'injectedChannels' : [3, 10, 21, 31, 35, 38, 45, 49, 61, 64],
    }
    
    all_samp.Sampling_scan(i2csocket = i2csocket,daqsocket = daqsocket, clisocket = clisocket, extra_text = 'LED_BV_'+ options.LEDvolt + '_OV_' + options.overvoltage, basedir = options.odir,device_name = options.dut, device_type = options.device_type, injectionConfig = injectionConfig, process = 'ext', subprocess = '', suffix="", active_menu = 'calibAndL1A', num_events = 2500, calibreq = 0x10, bxoffset = 24, noofoffsets = 2, stepBX = 1, startPhase=0, stopPhase=15, stepPhase=1)
