import zmq, datetime,  os, subprocess, sys, yaml, glob, csv

import myinotifier,util,math,time
import analysis.level0.pedestal_run_analysis as analyzer
import zmq_controler as zmqctrl
from TableController import TableController
from nested_dict import nested_dict 
import pandas as pd
from time import sleep

A_T = 3.9083e-3
B_T = -5.7750e-7
R0 = 1000


#OV = ["2V","4V"]
#OV = ["6V"] #=============================================change manually
OV = ["4V"]
convGain = "4" #ConvGain
tileboard = 'TB3_G8_6'
testName = "beam_run"
channel = '26' #=================================================change manually for the next 5 years
#configs = ["sipm_roc0_onbackup0_gainconv4_trimtoaNEW_Board2.yaml",
#           "sipm_roc0_onbackup0_gainconv1.yaml",
#           "sipm_roc0_onbackup0_gainconv2.yaml",
#           "sipm_roc0_onbackup0_gainconv4.yaml",
#           "sipm_roc0_onbackup0_gainconv8.yaml",
#           "sipm_roc0_onbackup0_gainconv12.yaml",
#           "sipm_roc0_onbackup0_gainconv15.yaml"]

#configs =  ["sipm_roc0_onbackup0_gainconv2_timingtests.yaml",
#	        "sipm_roc0_onbackup0_gainconv4_trimtoaNEW_timingtests_Board2.yaml",
#            "sipm_roc0_onbackup0_gainconv12_timingtests.yaml"]


configs = [
    #"sipm_roc0_onbackup0_gainconv4_trimtoaNEW_TB3_G8_Board1_beam_run.yaml"
    #"sipm_roc0_onbackup0_gainconv12_trimtoaNEW_TB3_G8_Board1_beam_run.yaml"
    #"sipm_roc0_config_ConvGain15_9mm2_Cf6.yaml"
    #"roc_config_ConvGain9mm2_from_Mathias.yaml"
    #"roc_config_ConvGain4_Cf2_Cfcomp2_Rf12_9mm2.yaml" #=============================================change manually
    #"roc_config_"+convGain+"_Cf10_Cfcomp10_Rf12_9mm2.yaml"
    #"sipm_roc0_onbackup0_gainconv"+convGain+"_trimtoa_trimtot.yml"
    #"sipm_roc0_onbackup0_gainconv4_Dacb_vb_conv5_trimtoa_trimtot_after_pedestal_adjustment.yaml"
    #"sipm_roc0_onbackup0_gainconv4_pre_series_TB_testing_bkp.yaml"
    "sipm_roc0_onbackup0_gainconv4_pre_series_TB_testing_expanded_triminv_A5_5.yaml"
    #"roc_config_ConvGain1_1ROCs_swamp.yaml"
    
    
]

#config_dict = {	"sipm_roc0_onbackup0_gainconv4_trimtoaNEW_TB3_G8_Board1_beam_run.yaml":"ConvGain4",
#               	"sipm_roc0_onbackup0_gainconv12_trimtoaNEW_TB3_G8_Board1_beam_run.yaml":"ConvGain12",
##                #"sipm_roc0_config_ConvGain15_9mm2_Cf6.yaml":"ConvGain15",
#                "roc_config_ConvGain15_Cf2_Rf12_G8_Board2_SPS.yaml":"ConvGain15"
#    }

OV_dict = {
    "TB2": {
        '2V': {'A':180,'B':125},
        '3V': {'A':185,'B':125},
        '3V5': {'A':187,'B':125},
        '4V': {'A':190,'B':125},
        '4V5': {'A':193,'B':125},
        '5V': {'A':195,'B':125},
        '5V5': {'A':195,'B':125},
        '6V': {'A':200,'B':125}},
     "TB2.1_2": {
        '2V': {'A':193,'B':120},
        '3V': {'A':198,'B':122},
        '3V5': {'A':201,'B':125},
        '4V': {'A':203,'B':122},
        '4V5': {'A':206,'B':125},
        '5V': {'A':209,'B':120},
        '5V5': {'A':211,'B':125},
        '6V': {'A':213,'B':122}},
     "TB2.1_3": {
        '2V': {'A':195,'B':122},
        '3V': {'A':200,'B':124},
        '3V5': {'A':203,'B':125},
        '4V': {'A':205,'B':126},
        '4V5': {'A':208,'B':127},
        '5V': {'A':210,'B':128},
        '5V5': {'A':213,'B':129},
        '6V': {'A':215,'B':130}},

      "TB3_1": {
        '2V': {'A':198,'B':113},
        '4V': {'A':208,'B':117}},
        
     "TB3_2": {
        '2V': {'C':183,'D':122},
        '4V': {'C':193,'D':122}},

     "TB3_G8_1": {
        #'1V':  {'A': 180, 'B': 127},  # 40.9 V  MPPC_BIAS1 =  40.8996
        '2V':  {'A': 183, 'B': 124},  # 41.9 V  MPPC_BIAS1 =  41.88 ------------------Aug2023
        '4V':  {'A': 193, 'B': 124},  # 43.9 V  MPPC_BIAS1 =  43.9136 ----------------Aug2023
        #'5V':  {'A': 202, 'B': 126},  # 44.9 V  MPPC_BIAS1 =  44.9348
        '6V':  {'A': 210, 'B': 112},  # 45.9 V  MPPC_BIAS1 =  46.6659 ----------------Aug2023
        #'6V6':  {'A': 210, 'B': 126},  # 46.5 V MPPC_BIAS1 =  46.4916
     },
    
     "TB3_G8_2": {
        #'1V':  {'A': 180, 'B': 127},  # 40.9 V  MPPC_BIAS1 =  40.8996
        '2V':  {'A': 186, 'B': 126},  # 41.9 V  MPPC_BIAS1 =  41.896 ----------------Aug2023
        '4V':  {'A': 197, 'B': 124},  # 43.9 V  MPPC_BIAS1 =  43.9385  --------------Aug2023
        #'5V':  {'A': 202, 'B': 126},  # 44.9 V  MPPC_BIAS1 =  44.9348
        '6V':  {'A': 210, 'B': 112},  # 45.9 V  MPPC_BIAS1 =  45.956 ----------------Aug2023
        #'6V6':  {'A': 210, 'B': 126},  # 46.5 V MPPC_BIAS1 =  46.4916
     },

    "TB3_D8_1": {
        '0V9': {'A':188,'B':136},  # 40.5
        '1V': {'A':189,'B':134},  # 40.6
        '1V1': {'A':190,'B':132}, # 40.7
        '1V2': {'A':191,'B':130}, # 40.8
        '1V3': {'A':192,'B':128}, # 40.9
        '1V4': {'A':193,'B':126}, # 41.0
        '2V': {'A':198,'B':113}, #from May 2023 test beam
        '4V': {'A':210,'B':118},#from Aug 2023 test beam, MPPC_BIAS1 = 43.98
        '1V9': {'A':196,'B':122},#correct, MPPC_BIAS1 = 41.5099
        '2V': {'A':197,'B':120},#correct, MPPC_BIAS1 = 41.6095
        '2V1': {'A':198,'B':118},#correct, MPPC_BIAS1 = 41.7092
        '2V2': {'A':199,'B':116},#correct, MPPC_BIAS1 = 41.8337
        '2V3': {'A':200,'B':114},#correct, MPPC_device_nameBIAS1 = 41.9209
        '2V4': {'A':201,'B':111},#correct, MPPC_BIAS1 = 41.9956
        '2V5': {'A':202,'B':107},#correct, MPPC_BIAS1 = 42.0205
        '2V6': {'A':203,'B':107},# correct, MPPC_BIAS1 = 42.1949
        '6V':  {'A': 219, 'B': 126},  # 45.9 V  MPPC_BIAS1 =  45.9934 ----------------Aug2023
     },
     
     
     "TB3_A5_1": {
        #'1V':  {'A': 180, 'B': 127},  # 40.9 V  MPPC_BIAS1 =  40.8996
        '2V':  {'A': 190, 'B': 122},  # 41.9 V  MPPC_BIAS1 =  43.9385  --------------Aug2023
        '4V':  {'A': 200, 'B': 124},  # 43.9 V  MPPC_BIAS1 =  41.896 ----------------Aug2023
        #'5V':  {'A': 202, 'B': 126},  # 44.9 V  MPPC_BIAS1 =  44.9348
        '6V':  {'A': 211, 'B': 122},  # 45.9 V  MPPC_BIAS1 =  45.956 ----------------Aug2023
        #'6V6':  {'A': 210, 'B': 126},  # 46.5 V MPPC_BIAS1 =  46.4916
     },
     
     
     #MAY testbeam
     "TB3_G8_6": {
        '4V': {'A': 197, 'B': 125}, #43.78V
     },
     "TB3_G8_4": {
        '4V': {'A': 187, 'B': 128}, #43.82V
     },
     
     "TB3_E8_2": {
        '4V': {'A': 188, 'B': 125}, #43.96V
     },
     "TB3_E8_3": {
        '4V': {'A': 200, 'B': 128}, #43.76V
     },
     "TB3_E8_4": {
        '4V': {'A': 196, 'B': 130}, #43.72V
     },
     "TB3_E8_5": {
        '4V': {'A': 180, 'B': 125}, #43.92V
     },
     "TB3_E8_6": { 
        '4V': {'A': 187, 'B': 122}, #43.89V
     },
     "TB3_A5_1": { 
        '4V': {'A': 200, 'B': 125}, #43.8V
     }, 
     "TB3_A5_2": { 
        '4V': {'A': 178, 'B': 120}, #43.97V
     }, 
     "TB3_A5_5": { 
        '4V': {'A': 181, 'B': 128}, #43.83V
     }, 
     "TB3_A5_6": { 
        '4V': {'A': 188, 'B': 125}, #43.83V
     } 
    
    }

def run(i2csocket, daqsocket, nruns, odir, testName):
    index=0
    for run in range(nruns):
        util.acquire_scan(daq=daqsocket)
        chip_params = { }
        util.saveMetaYaml(odir=odir,i2c=i2csocket,daq=daqsocket,
                          runid=index,testName=testName,keepRawData=1,
                          chip_params=chip_params)
        index=index+1
    return
    
def config_ROC(options,config) :   
    daqsocket = zmqctrl.daqController(options.hexaIP,options.daqPort,config)
    clisocket = zmqctrl.daqController("localhost",options.pullerPort,config)
    clisocket.yamlConfig['client']['serverIP'] = options.hexaIP
    i2csocket = zmqctrl.i2cController(options.hexaIP,options.i2cPort,config)

    if options.initialize==True:
        i2csocket.initialize()
        daqsocket.initialize()
        clisocket.yamlConfig['client']['serverIP'] = daqsocket.ip
        clisocket.initialize()
    else:
        i2csocket.configure()

    print(" ############## Starting up the MASTER TDCs #################")
    nestedConf = nested_dict()
    for key in i2csocket.yamlConfig.keys():
        if key.find('roc_s')==0:
            nestedConf[key]['sc']['MasterTdc'][0]['EN_MASTER_CTDC_VOUT_INIT']=1
            nestedConf[key]['sc']['MasterTdc'][0]['VD_CTDC_P_DAC_EN']=1
            nestedConf[key]['sc']['MasterTdc'][0]['VD_CTDC_P_D']=16
            nestedConf[key]['sc']['MasterTdc'][0]['EN_MASTER_FTDC_VOUT_INIT']=1
            nestedConf[key]['sc']['MasterTdc'][0]['VD_FTDC_P_DAC_EN']=1
            nestedConf[key]['sc']['MasterTdc'][0]['VD_FTDC_P_D']=16

            nestedConf[key]['sc']['MasterTdc'][1]['EN_MASTER_CTDC_VOUT_INIT']=1
            nestedConf[key]['sc']['MasterTdc'][1]['VD_CTDC_P_DAC_EN']=1
            nestedConf[key]['sc']['MasterTdc'][1]['VD_CTDC_P_D']=16
            nestedConf[key]['sc']['MasterTdc'][1]['EN_MASTER_FTDC_VOUT_INIT']=1
            nestedConf[key]['sc']['MasterTdc'][1]['VD_FTDC_P_DAC_EN']=1
            nestedConf[key]['sc']['MasterTdc'][1]['VD_FTDC_P_D']=16
            # nestedConf[key]['sc']['MasterTdc']['all']['INV_FRONT_40MHZ']=1

    i2csocket.update_yamlConfig(yamlNode=nestedConf.to_dict())
    i2csocket.configure()
    nestedConf = nested_dict()
    for key in i2csocket.yamlConfig.keys():
        if key.find('roc_s')==0:
            nestedConf[key]['sc']['MasterTdc'][0]['EN_MASTER_CTDC_VOUT_INIT']=0
            nestedConf[key]['sc']['MasterTdc'][0]['EN_MASTER_FTDC_VOUT_INIT']=0

            nestedConf[key]['sc']['MasterTdc'][1]['EN_MASTER_CTDC_VOUT_INIT']=0
            nestedConf[key]['sc']['MasterTdc'][1]['EN_MASTER_FTDC_VOUT_INIT']=0
    i2csocket.update_yamlConfig(yamlNode=nestedConf.to_dict())
    i2csocket.configure()
    return i2csocket, clisocket, daqsocket

def beam_run(i2csocket,daqsocket, clisocket, basedir,device_name, nruns,OV_val,config,timestamp, channel):
    if type(i2csocket) != zmqctrl.i2cController:
        print( "ERROR in beam_run : i2csocket should be of type %s instead of %s"%(zmqctrl.i2cController,type(i2csocket)) )
        sleep(1)
        return
    if type(daqsocket) != zmqctrl.daqController:
        print( "ERROR in beam_run : daqsocket should be of type %s instead of %s"%(zmqctrl.daqController,type(daqsocket)) )
        sleep(1)
        return
    
    if type(clisocket) != zmqctrl.daqController:
        print( "ERROR in beam_run : clisocket should be of type %s instead of %s"%(zmqctrl.daqController,type(clisocket)) )
        sleep(1)
        return
    	
    
    # config_name = config[config.find("sipm_roc0_"):]
    odir = "%s/%s/beam_run/run_ch_%s_%s/OV%s/%s/"%( os.path.realpath(basedir), device_name, channel, timestamp, OV_val, convGain )
    os.makedirs(odir,exist_ok=True) #config_dict[config_name]
    
    
     
     
    print("Set DACs")
    ######################
    # Set DACs of GBT_SCA TB3
    
    diff = 0
    if tileboard=="TB3_2":

        diff += abs(OV_dict[tileboard][OV_val]['C']-int(i2csocket.read_gbtsca_dac("C")))
        diff += abs(OV_dict[tileboard][OV_val]['D']-int(i2csocket.read_gbtsca_dac("D")))

        if (diff>0):
            i2csocket.set_gbtsca_dac("A",100)
        print("Dac A value is now",i2csocket.read_gbtsca_dac("A"))
        if (diff>0):
	        i2csocket.set_gbtsca_dac("B",100)
        print("Dac B value is now",i2csocket.read_gbtsca_dac("B"))
        
        # i2csocket.set_gbtsca_dac("A",200)
        # print("Dac A value is now",i2csocket.read_gbtsca_dac("A"))
        # i2csocket.set_gbtsca_dac("B",125)
        # print("Dac B value is now",i2csocket.read_gbtsca_dac("B"))
        
        if (diff>0):
	        i2csocket.set_gbtsca_dac("C",OV_dict[tileboard][OV_val]['C'])
        print("Dac C value is now",i2csocket.read_gbtsca_dac("C"))
        if (diff>0):
        	i2csocket.set_gbtsca_dac("D",OV_dict[tileboard][OV_val]['D'])
        print("Dac D value is now",i2csocket.read_gbtsca_dac("D"))


    else:
        diff += abs(OV_dict[tileboard][OV_val]['A']-int(i2csocket.read_gbtsca_dac("A")))
        diff += abs(OV_dict[tileboard][OV_val]['B']-int(i2csocket.read_gbtsca_dac("B")))

        if (diff>0):
        	i2csocket.set_gbtsca_dac("A",OV_dict[tileboard][OV_val]['A'])
        print("Dac A value is now",i2csocket.read_gbtsca_dac("A"))
        if (diff>0):
        	i2csocket.set_gbtsca_dac("B",OV_dict[tileboard][OV_val]['B'])
        print("Dac B value is now",i2csocket.read_gbtsca_dac("B"))
        
        # i2csocket.set_gbtsca_dac("A",200)
        # print("Dac A value is now",i2csocket.read_gbtsca_dac("A"))
        # i2csocket.set_gbtsca_dac("B",125)
        # print("Dac B value is now",i2csocket.read_gbtsca_dac("B"))
        
        if (diff>0):
        	i2csocket.set_gbtsca_dac("C",100)
        print("Dac C value is now",i2csocket.read_gbtsca_dac("C"))
        if (diff>0):
        	i2csocket.set_gbtsca_dac("D",100)
        print("Dac D value is now",i2csocket.read_gbtsca_dac("D"))



    # "sleep" is only required when SiPM bias voltage is changed:
    if (diff>0):
        # "sleep" is only required when SiPM bias voltage is changed:
        print(" ")
        print(" Please wait for voltage stabilization (5seconds)")
        time.sleep(5)   # wait 5s for stabilization of voltages before readback
    else:
        print("Voltage not changed")
    
    
    #======================measure temperature and bias voltage=====================
    fout=open(odir+"TB3_G8_info.txt", "w")
    fout.write("####  Before data capture ####" + '\n')
    fout.write("#  Tileboard2 Slow Control Data" + '\n')
    fout.write("#  Date, Time: " + timestamp + '\n')


    SCA_ADC_range = range(0, 8)
    for sca_adc in SCA_ADC_range:
       ADC = i2csocket.read_gbtsca_adc(sca_adc)
       T1 = round(float((-R0*A_T + math.sqrt(math.pow(R0*A_T, 2) - 4*R0*B_T*(R0-(1800 / ((2.5*4095/float(ADC))-1))))) / (2*R0*B_T)),1)
       print("T", sca_adc,  ":", str(T1))
       fout.write("T" + str(sca_adc) +": "+str(T1) + '\n')

    ADC = i2csocket.read_gbtsca_adc(9)
    MPPC_BIAS1 = round(float(ADC)/4095*204000/4000, 4)
    print("MPPC_BIAS1 = ", str(MPPC_BIAS1))
    fout.write("MPPC_BIAS1: " + str(MPPC_BIAS1) + '\n')

    ADC = i2csocket.read_gbtsca_adc(10)
    MPPC_BIAS2 = round(float(ADC)/4095*204000/4000, 4)
    print("MPPC_BIAS2 = ", str(MPPC_BIAS2))
    fout.write("MPPC_BIAS2: " + str(MPPC_BIAS2) + '\n')

    ADC = i2csocket.read_gbtsca_adc(12)
    LED_BIAS = round(float(ADC)/4095*15000/1000, 3)
    print("LED_BIAS = ", str(LED_BIAS))
    fout.write("LED_BIAS: " + str(LED_BIAS) + '\n')

    #===============================================================================


    mylittlenotifier = myinotifier.mylittleInotifier(odir=odir)
    
    clisocket.yamlConfig['client']['outputDirectory'] = odir
    clisocket.yamlConfig['client']['run_type'] = testName
    clisocket.configure()
    daqsocket.yamlConfig['daq']['active_menu']='externalL1A'
    daqsocket.yamlConfig['daq']['menus']['externalL1A']['NEvents']=200000
    daqsocket.yamlConfig['daq']['menus']['externalL1A']['loopBack']=False
    daqsocket.yamlConfig['daq']['menus']['externalL1A']['prescale']=0
    daqsocket.yamlConfig['daq']['menus']['externalL1A']['trg_fifo_latency']=5
    daqsocket.yamlConfig['daq']['menus']['externalL1A']['trgphase_fifo_latency']=20
    daqsocket.configure()

    nestedConf = nested_dict()
    for key in i2csocket.yamlConfig.keys():
        if key.find('roc_s')==0:
            nestedConf[key]['sc']['DigitalHalf'][0]['CalibrationSC'] = 0
            nestedConf[key]['sc']['DigitalHalf'][1]['CalibrationSC'] = 0
            nestedConf[key]['sc']['DigitalHalf'][0]['L1Offset'] = 13 #13 #=============================================change manually
            nestedConf[key]['sc']['DigitalHalf'][1]['L1Offset'] = 13 #13 #=============================================change manually
            nestedConf[key]['sc']['Top'][0]['phase_ck']= 7 #=============================================change manually

    print("before updating yaml")
    i2csocket.update_yamlConfig(yamlNode=nestedConf.to_dict())
    print("before i2csocekt configure")
    i2csocket.configure()
    print("before resettdc")
    i2csocket.resettdc()
    	
    util.saveFullConfig(odir=odir,i2c=i2csocket,daq=daqsocket,cli=clisocket)
    clisocket.start()
    mylittlenotifier.start()
    run(i2csocket, daqsocket, nruns, odir, testName)
    mylittlenotifier.stop()
    clisocket.stop()
    
    #======================measure temperature and bias voltage=====================    
    fout.write("####  After data capture ####" + '\n')
    fout.write("#  Tileboard2 Slow Control Data" + '\n')
    fout.write("#  Date, Time: " + timestamp + '\n')
   
    SCA_ADC_range = range(0, 8)
    for sca_adc in SCA_ADC_range:
       ADC = i2csocket.read_gbtsca_adc(sca_adc)
       T1 = round(float((-R0*A_T + math.sqrt(math.pow(R0*A_T, 2) - 4*R0*B_T*(R0-(1800 / ((2.5*4095/float(ADC))-1))))) / (2*R0*B_T)),1)
       print("T", sca_adc,  ":", str(T1))
       fout.write("T" + str(sca_adc) +": "+str(T1) + '\n')

    ADC = i2csocket.read_gbtsca_adc(9)
    MPPC_BIAS1 = round(float(ADC)/4095*204000/4000, 4)
    print("MPPC_BIAS1 = ", str(MPPC_BIAS1))
    fout.write("MPPC_BIAS1: " + str(MPPC_BIAS1) + '\n')

    ADC = i2csocket.read_gbtsca_adc(10)
    MPPC_BIAS2 = round(float(ADC)/4095*204000/4000, 4)
    print("MPPC_BIAS2 = ", str(MPPC_BIAS2))
    fout.write("MPPC_BIAS2: " + str(MPPC_BIAS2) + '\n')
    #===============================================================================
    

    return odir


if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    
    parser.add_option("-d", "--dut", dest="dut",
                      help="device under test")
    
    parser.add_option("-i", "--hexaIP",
                      action="store", dest="hexaIP",
                      help="IP address of the zynq on the hexactrl board")
    
    parser.add_option("-f", "--configFile",default="./configs/init.yaml",
                      action="store", dest="configFile",
                      help="initial configuration yaml folder")
    
    parser.add_option("-o", "--odir",
                      action="store", dest="odir",default='./data',
                      help="output base directory")
    
    parser.add_option("--daqPort",
                      action="store", dest="daqPort",default='6000',
                      help="port of the zynq waiting for daq config and commands (configure/start/stop/is_done)")
    
    parser.add_option("--i2cPort",
                      action="store", dest="i2cPort",default='5555',
                      help="port of the zynq waiting for I2C config and commands (initialize/configure/read_pwr,read/measadc)")
    
    parser.add_option("--pullerPort",
                      action="store", dest="pullerPort",default='6001',
                      help="port of the client PC (loccalhost for the moment) waiting for daq config and commands (configure/start/stop)")
    
    parser.add_option("-I", "--initialize",default=False,
                      action="store_true", dest="initialize",
                      help="set to re-initialize the ROCs and daq-server instead of only configuring")

    parser.add_option("-n", "--nruns",type=int,default=1,
                      action="store", dest="nruns",
                      help="number of subruns")
                      
    parser.add_option("-c", "--channel",type=int,default=1,
                      action="store", dest="channel",
                      help="channel number")
                      
    (options, args) = parser.parse_args()
    print(options)
    

                
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for OV_val in OV:
        configFile = list(map(lambda x: options.configFile +x,configs)) 
        for config in configFile:
            print("Config File:"+config)
            i2csocket , clisocket, daqsocket = config_ROC(options,config)

            print("Beam_run start!")
            odir = beam_run(i2csocket,daqsocket,clisocket,options.odir,options.dut,options.nruns,OV_val,config,timestamp, options.channel)
            print("Beam_run Finished")
            
