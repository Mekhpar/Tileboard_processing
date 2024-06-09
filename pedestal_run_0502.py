import zmq, datetime,  os, subprocess, sys, yaml, glob

import myinotifier,util

import zmq_controler as zmqctrl
import miscellaneous_functions as misc_func
from nested_dict import nested_dict 
from time import sleep

def pedestal_run(i2csocket,daqsocket, clisocket, basedir,device_name,device_type,suffix=""):
    	
    testName = "pedestal_run"
    odir = misc_func.mkdir(basedir,device_name,device_type,testName,suffix)
    print("Output directory returned from function", odir)
    
    mylittlenotifier = myinotifier.mylittleInotifier(odir=odir)
    mylittlenotifier.start()
    
    clisocket.yamlConfig['client']['outputDirectory'] = odir
    clisocket.yamlConfig['client']['run_type'] = testName
    clisocket.configure()
    
    daqsocket.daq_pedestal_settings('randomL1A',1000,0,45) #different number of events, should override the one in zmq_controler.py
    #Active menu for pedestal, number of events, log2_rand_bx_period, bx_min
    daqsocket.configure()
    	
    util.saveFullConfig(odir=odir,i2c=i2csocket,daq=daqsocket,cli=clisocket)
    util.saveMetaYaml(odir=odir,i2c=i2csocket,daq=daqsocket,runid=0,testName=testName,keepRawData=1,chip_params={})

    util.acquire(daq=daqsocket, client=clisocket)
    sleep(1)
    mylittlenotifier.stop()

    return odir
    
    print('*'*50, odir, '*'*50)


if __name__ == "__main__":
    parser = misc_func.options_run()#This will be constant for every test irrespective of the type of test
    (options, args) = parser.parse_args()
    print(options)
    
    (daqsocket,clisocket,i2csocket) = zmqctrl.pre_init(options)
    pedestal_run(i2csocket,daqsocket,clisocket,options.odir,options.dut,options.device_type,suffix=options.suffix)
