import zmq, datetime,  os, subprocess, sys, yaml, glob, math
from time import sleep
import myinotifier,util
import analysis.level0.pedestal_scan_analysis as analyzer
import zmq_controler as zmqctrl
from nested_dict import nested_dict
import uproot
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import miscellaneous_functions as misc_func


RUNID = 0

def pedestal_scan(i2csocket, daqsocket, clisocket, basedir, device_name, config, odir, trim_invs, dacbs, sign_dacs):
    global RUNID
    
    mylittlenotifier = myinotifier.mylittleInotifier(odir=odir)
    mylittlenotifier.start()

    clisocket.yamlConfig['client']['outputDirectory'] = odir
    clisocket.yamlConfig['client']['run_type'] = "pedestal_scan"
    clisocket.yamlConfig['client']['serverIP'] = daqsocket.ip
    clisocket.configure()
    daqsocket.yamlConfig['daq']['active_menu']='randomL1A'
    daqsocket.yamlConfig['daq']['menus']['randomL1A']['NEvents']=1000
    daqsocket.yamlConfig['daq']['menus']['randomL1A']['log2_rand_bx_period']=0
    daqsocket.yamlConfig['daq']['menus']['randomL1A']['bx_min']=45
    daqsocket.configure()

    util.saveFullConfig(odir=odir,i2c=i2csocket,daq=daqsocket,cli=clisocket)
            
    clisocket.start()
    
    testName='pedestal_scan'
    
    
    runconfigs = []
    ch_range = [72,4,2]
    ch_keys = ['ch','cm','calib']
    
    for trim_inv in trim_invs:
    #for ref_val in ref_vals:
        for dacb in dacbs:
            for sign in sign_dacs:
                nestedConf = nested_dict()
                #for rocId in configFile.keys():
                for rocId in config.keys():
                    if rocId.find('roc_s')==0:
                        #if rocId in triminv.keys():
                        for i in range(0,3):
                            for channel in range(0,ch_range[i]):
                                nestedConf[rocId]['sc'][ch_keys[i]][channel]['trim_inv'] = trim_inv
                            
                        #if rocId in dacb.keys():
                        for i in range(0,3):
                            for channel in range(0,ch_range[i]):
                                nestedConf[rocId]['sc'][ch_keys[i]][channel]['dacb'] = dacb
                                nestedConf[rocId]['sc'][ch_keys[i]][channel]['sign_dac'] = sign

        
                print("Pedestal scan for trim_inv",trim_inv,"dacb",dacb, "sign_dac", sign)
                runconfigs.append({"runid":RUNID, "trim_inv": trim_inv, "dacb": dacb, "sign_dac": sign})
                i2csocket.configure(yamlNode=nestedConf.to_dict())
                util.acquire_scan(daq=daqsocket)
                chip_params = {'trim_inv' : trim_inv, 'dacb': dacb, 'sign_dac': sign}
                util.saveMetaYaml(odir=odir,i2c=i2csocket,daq=daqsocket,
                                  runid=RUNID,testName=testName,keepRawData=0,
                                  chip_params=chip_params)
                RUNID+=1
        
        
    clisocket.stop()
    mylittlenotifier.stop()
        
def optimize_pedestal(i2csocket,daqsocket, clisocket, basedir,device_name,configFile):
    
    if type(i2csocket) != zmqctrl.i2cController:
	    print( "ERROR in pedestal_run : i2csocket should be of type %s instead of %s"%(zmqctrl.i2cController,type(i2csocket)) )
	    sleep(1)
	    return

    if type(daqsocket) != zmqctrl.daqController:
	    print( "ERROR in pedestal_run : daqsocket should be of type %s instead of %s"%(zmqctrl.daqController,type(daqsocket)) )
	    sleep(1)
	    return

    if type(clisocket) != zmqctrl.daqController:
	    print( "ERROR in pedestal_run : clisocket should be of type %s instead of %s"%(zmqctrl.daqController,type(clisocket)) )
	    sleep(1)
	    return
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    odir = "%s/%s/pedestal_scan/run_%s/"%( os.path.realpath(basedir), device_name, timestamp ) # a comlete path is needed
    #odir = "%s/%s/pedestal_scan/run_%s/"%( os.path.realpath(basedir), device_name, directory_index) # a comlete path is needed
    os.makedirs(odir)
    
    trim_invs = [i for i in range(0,64)]
    dacbs = [i for i in range(0,5)]
    sign_dacs = [0,1]
    
    with open(configFile) as f:
        config = yaml.safe_load(f)
    
    pedestal_scan(i2csocket,daqsocket, clisocket, basedir, device_name, config, odir, trim_invs, dacbs, sign_dacs)
    return odir
    
    
def main():
    
    parser = misc_func.options_run() #This will be constant for every test irrespective of the type of test
    #(options, args) = parser.parse_args()
    options = parser.parse_args()
    print(options)
    
    daqsocket = zmqctrl.daqController(options.hexaIP,options.daqPort,options.configFile)
    clisocket = zmqctrl.daqController("localhost",options.pullerPort,options.configFile)
    i2csocket = zmqctrl.i2cController(options.hexaIP,options.i2cPort,options.configFile)

    i2csocket.configure()
    optimize_pedestal(i2csocket,daqsocket,clisocket,options.odir,options.dut,options.configFile)

if __name__ == "__main__":
	main()
    
