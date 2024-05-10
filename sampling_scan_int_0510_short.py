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
    parser.add_option("-c","--calib", action="store", dest="calib",default='0', help="pulse height for internal injection")
 
    (options, args) = parser.parse_args()
    print(options)
    (daqsocket,clisocket,i2csocket) = zmqctrl.pre_init(options)

    injectionConfig = {
        'gain' : 1,   # gain=0: LowRange, gain=1: HighRange
        'calib' : int(options.calib),
        #'injectedChannels' : [0, 2, 4, 6, 8, 10, 12, 14, 16]  # scan 5
        'injectedChannels' : [6, 10, 45, 52]  # scan 8

    }
    all_samp.Sampling_scan(i2csocket = i2csocket,daqsocket = daqsocket, clisocket = clisocket, extra_text = 'Calib_'+ options.calib, basedir = options.odir,device_name = options.dut, device_type = options.device_type, injectionConfig = injectionConfig, process = 'int', subprocess = 'preamp', suffix="", active_menu = 'calibAndL1A', num_events = 500, calibreq = 0x10, bxoffset = 21, noofoffsets = 2, stepBX = 1, startPhase=0, stopPhase=15, stepPhase=1)
