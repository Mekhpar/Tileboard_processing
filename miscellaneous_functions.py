from time import sleep
import os,datetime

def mkdir(basedir,device_name,device_type,testName,suffix):
    directory_index = 1
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if suffix:
        timestamp = timestamp + "_" + suffix

    while True:
        odir = "%s/%s/%s/%s_%s_%s/"%( os.path.realpath(basedir), device_name,device_type,testName,device_type,directory_index)
        #print("Output directory",odir) 
        dir_exist = os.path.exists(odir)
        if dir_exist:
            directory_index+=1
        elif not dir_exist:
            os.makedirs(odir)
            print("Output directory",odir) 
            break

    return odir

def options_run():
    from optparse import OptionParser
    parser = OptionParser()
    
    parser.add_option("-d", "--dut", dest="dut", help="device under test")

    parser.add_option("-t", "--device_type", dest="device_type", help="device sub type and board number for the sub directory")
    
    parser.add_option("-i", "--hexaIP", action="store", dest="hexaIP", help="IP address of the zynq on the hexactrl board")
    
    parser.add_option("-f", "--configFile",default="./configs/init.yaml", action="store", dest="configFile", help="initial configuration yaml file")
    
    parser.add_option("-o", "--odir", action="store", dest="odir",default='./data', help="output base directory")
    
    parser.add_option("-s", "--suffix", action="store", dest="suffix",default='', help="output base directory")

    parser.add_option("--daqPort", action="store", dest="daqPort",default='6000', help="port of the zynq waiting for daq config and commands (configure/start/stop/is_done)")
    
    parser.add_option("--i2cPort", action="store", dest="i2cPort",default='5555', help="port of the zynq waiting for I2C config and commands (initialize/configure/read_pwr,read/measadc)")
    
    parser.add_option("--pullerPort", action="store", dest="pullerPort",default='6001', help="port of the client PC (loccalhost for the moment) waiting for daq config and commands (configure/start/stop)")
    
    parser.add_option("-I", "--initialize",default=False, action="store_true", dest="initialize", help="set to re-initialize the ROCs and daq-server instead of only configuring")

    (options, args) = parser.parse_args()
    print(options)
    return options
    
def options_analyze():#No data taking
    from optparse import OptionParser
    parser = OptionParser()
    
    parser.add_option("-d", "--dut", dest="dut", help="device under test")

    parser.add_option("-t", "--device_type", dest="device_type", help="device sub type and board number for the sub directory")
    
    parser.add_option("-n", "--directory_index", dest="directory_index", help="Number of runs for the device and device type")

    parser.add_option("-o", "--odir", action="store", dest="odir",default='./data', help="output base directory")
    
    parser.add_option("-s", "--suffix", action="store", dest="suffix",default='', help="output base directory")

    (options, args) = parser.parse_args()
    print(options)
    return options
    
    
