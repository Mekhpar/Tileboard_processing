import zmq
import yaml
from time import sleep
import math
from nested_dict import nested_dict
import miscellaneous_functions as misc_func

def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

class zmqController:
    def __init__(self,ip,port,fname="configs/init.yaml"):
        context = zmq.Context()
        self.ip=ip
        self.port=port
        self.socket = context.socket( zmq.REQ )
        self.socket.connect("tcp://"+str(ip)+":"+str(port))
        with open(fname) as fin:
            self.yamlConfig=yaml.safe_load(fin)

    def reset(self):
        self.socket.close()
        context = zmq.Context()
        self.socket = context.socket( zmq.REQ )
        self.socket.connect("tcp://"+str(self.ip)+":"+str(self.port))

    def update_yamlConfig(self,fname="",yamlNode=None):
        if yamlNode:
            config=yamlNode
        elif fname :
            with open(fname) as fin:
                config=yaml.safe_load(fin)
        else:
            print("ERROR in %s"%(__name__))
        merge(self.yamlConfig,config)

    def initialize(self,fname="",yamlNode=None):
        self.socket.send_string("initialize",zmq.SNDMORE)
        if yamlNode:
            config=yamlNode
        elif fname :
            with open(fname) as fin:
                config=yaml.safe_load(fin)
        else:
            config = self.yamlConfig
        self.socket.send_string(yaml.dump(config))
        rep = self.socket.recv()
        print("returned status (from init) = %s"%rep)
        # return rep

    def configure(self,fname="",yamlNode=None):
        self.socket.send_string("configure",zmq.SNDMORE)
        if yamlNode:
            config=yamlNode
        elif fname :
            with open(fname) as fin:
                config=yaml.safe_load(fin)
        else:
            config = self.yamlConfig
        self.socket.send_string(yaml.dump(config))
        rep = self.socket.recv_string()
        print("returned status (from config) = %s"%rep)


class i2cController(zmqController):    
    def __init__(self,ip,port,fname="configs/init.yaml"):
        super(i2cController, self).__init__(ip,port,fname)
        self.maskedDetIds=[]
        					
    def read_config(self,yamlNode=None):
        # only for I2C server
        self.socket.send_string("read",zmq.SNDMORE)
        # rep = self.socket.recv_string()
        if yamlNode:
            self.socket.send_string( yaml.dump(yamlNode) )
        else:
            self.socket.send_string( "" )
        yamlread = yaml.safe_load( self.socket.recv_string() )
        return( yamlread )
		
    def read_pwr(self):
        ## only valid for hexaboard/trophy systems
        self.socket.send_string("read_pwr")
        rep = self.socket.recv_string()
        pwr = yaml.safe_load(rep)
        return( pwr )
        
    def resettdc(self):
        self.socket.send_string("resettdc")
        rep = self.socket.recv_string()
        return( yaml.safe_load(rep) )
       
    def set_gbtsca_dac(self,dac,val):
        self.socket.send_string("set_gbtsca_dac "+str(dac)+" "+str(val))
        return self.socket.recv_string()

    def read_gbtsca_dac(self,dac):
        self.socket.send_string("read_gbtsca_dac "+str(dac))
        dacval = self.socket.recv_string()
        return(dacval)

    def read_gbtsca_adc(self,channel):
        self.socket.send_string("read_gbtsca_adc "+str(channel))
        adcval = self.socket.recv_string()
        return(adcval)
 
    def read_gbtsca_gpio(self):
        self.socket.send_string("read_gbtsca_gpio")
        gpiovals=self.socket.recv_string()
        return(gpiovals)   

    def set_gbtsca_gpio_direction(self,direction):
        self.socket.send_string("set_gbtsca_gpio_direction "+str(direction))
        return(self.socket.recv_string())

    def get_gbtsca_gpio_direction(self):
        self.socket.send_string("get_gbtsca_gpio_direction")
        gpio_directions = self.socket.recv_string()
        return gpio_directions

    def set_gbtsca_gpio_vals(self,vals,mask):
        self.socket.send_string("set_gbtsca_gpio_vals "+str(vals)+" "+str(mask))
        return(self.socket.recv_string())

    def measadc(self,yamlNode):
        ## only valid for hexaboard/trophy systems
        self.socket.send_string("measadc",zmq.SNDMORE)
        # rep = self.socket.recv_string()
        # if rep.lower().find("ready")<0:
        #     print(rep)
        #     return
        if yamlNode:
            config=yamlNode
        else:
            config = self.yamlConfig
        self.socket.send_string(yaml.dump(config))
        rep = self.socket.recv_string()
        adc = yaml.safe_load(rep)
        return( adc )

    #For this set of ADCs the number of bits is always 12, so the maximum value is always 4095
    def read_convert(self,out_dir=0, variable_name = "", adc_pin = 0, bit_val = 4095, numerator = 1, denominator = 1, round_off = 1):
        ADC = self.read_gbtsca_adc(adc_pin)
        converted_value = round(float(ADC)/bit_val*numerator/denominator, round_off)
        print(variable_name," = ", str(converted_value))
        out_dir.write(variable_name + ": " + str(converted_value) + '\n')
        

    def meas_temp_bias(self,out_dir,A_T,B_T,R0): #individual functions are already available but this is something we might need frequently
        SCA_ADC_range = range(0, 8)
        for sca_adc in SCA_ADC_range: #8 temperatures
           ADC = self.read_gbtsca_adc(sca_adc)
           T1 = round(float((-R0*A_T + math.sqrt(math.pow(R0*A_T, 2) - 4*R0*B_T*(R0-(1800 / ((2.5*4095/float(ADC))-1))))) / (2*R0*B_T)),1)
           print("T", sca_adc,  ":", str(T1))
           out_dir.write("T" + str(sca_adc) +": "+str(T1) + '\n')

        ADC = self.read_gbtsca_adc(9)
        MPPC_BIAS1 = round(float(ADC)/4095*204000/4000, 4)
        print("MPPC_BIAS1 = ", str(MPPC_BIAS1))
        out_dir.write("MPPC_BIAS1: " + str(MPPC_BIAS1) + '\n')

        ADC = self.read_gbtsca_adc(10)
        MPPC_BIAS2 = round(float(ADC)/4095*204000/4000, 4)
        print("MPPC_BIAS2 = ", str(MPPC_BIAS2))
        out_dir.write("MPPC_BIAS2: " + str(MPPC_BIAS2) + '\n')

        ADC = self.read_gbtsca_adc(12)
        LED_BIAS = round(float(ADC)/4095*15000/1000, 3)
        print("LED_BIAS = ", str(LED_BIAS))
        out_dir.write("LED_BIAS: " + str(LED_BIAS) + '\n')
        
    def addMaskedDetId(self,detid):
        self.maskedDetIds.append(detid)

    def rmMaskedDetId(self,detid):
        self.maskedDetIds.remove(detid)


    #Very generic function, will cover the other two injections too
    #sipm_configure_injection = configure_injection(self,trim_val=0, calib_preamp = 0, calib_conv = calib_dac, gain=0,injectedChannels=[0,1,2], IntCtest = 0, choice_cinj = 0, cmd_120p = 0, L_g2 = 0, H_g2 = 1, L_g1 = 0, H_g1 = 1, L_g0 = 0, H_g0 = 1) - there are no lg and hg conditions depending on gain value, cmd_120p is to be set equal to the gain, and this assuming the activate is high (1)
    
    #configure_injection = configure_injection(self,trim_val=0, calib_preamp = calib_dac, calib_conv = 0, gain=0,injectedChannels=[0,1,2], IntCtest = 1, choice_cinj = 1 '''This choice is purely based on the value from the preamp injection script''', cmd_120p = 0, L_g2 = 0, H_g2 = 1, L_g1 = 0, H_g1 = 1, L_g0 = 1, H_g0 = 0)
    
    
    def configure_injection(self,trim_val = 0, process = 'int', calib_preamp = 0, calib_conv = 0, gain=1,injectedChannels=[0,1,2], IntCtest = 0, choice_cinj = 0, cmd_120p = 0, L_g2 = 0, H_g2 = 0, L_g1 = 0, H_g1 = 0, L_g0 = 0, H_g0 = 0): #Here all three conditions for the gain look exactly the same
        nestedConf = nested_dict()
        update = lambda conf, chtype, channel, Range, val : conf[chtype][channel].update({Range:val})
        for key in self.yamlConfig.keys():
            if key.find('roc_s')==0:
            
                if calib_preamp == -1 | calib_conv == -1: #Including both because the scope of the function is wider to have both preamp and conveyor injection
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['IntCtest'] = 0
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['Calib_2V5'] = 0
                else:
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['IntCtest'] = IntCtest
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['Calib'] = calib_preamp
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['Calib_2V5'] = calib_conv
                
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['choice_cinj'] = choice_cinj   # "1": inject to preamp input, "0": inject to conveyor input
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['cmd_120p'] = cmd_120p
                    if process == 'ext':
                        nestedConf[key]['sc']['ch']['all']['trim_inv'] = trim_val
                    elif process == 'int':
                        pass #Do nothing, DO NOT set the trim_val
                        print("Trim_inv value for pedestal not set")
                            
                if gain==2:
                    for inj_chs in injectedChannels:
                       [nestedConf[key]['sc']['ch'][inj_chs].update({'LowRange':L_g2}) for key in self.yamlConfig.keys() if key.find('roc_s')==0 ]
                       [nestedConf[key]['sc']['ch'][inj_chs].update({'HighRange':H_g2}) for key in self.yamlConfig.keys() if key.find('roc_s')==0 ]
                elif gain==1:
                    for inj_chs in injectedChannels:
                       print("Marke 3")
                       [nestedConf[key]['sc']['ch'][inj_chs].update({'LowRange':L_g1}) for key in self.yamlConfig.keys() if key.find('roc_s')==0 ]
                       [nestedConf[key]['sc']['ch'][inj_chs].update({'HighRange':H_g1}) for key in self.yamlConfig.keys() if key.find('roc_s')==0 ]
                   
                elif gain==0:
                    for inj_chs in injectedChannels:
                       [nestedConf[key]['sc']['ch'][inj_chs].update({'LowRange':L_g0}) for key in self.yamlConfig.keys() if key.find('roc_s')==0 ]
                       [nestedConf[key]['sc']['ch'][inj_chs].update({'HighRange':H_g0}) for key in self.yamlConfig.keys() if key.find('roc_s')==0 ]
                   
                else:
                    pass
        self.configure(yamlNode=nestedConf.to_dict())

    def phase_set(self,phase):
        nestedConf = nested_dict()
        for key in self.yamlConfig.keys():
            if key.find('roc_s')==0:
              
                nestedConf[key]['sc']['Top']['all']['phase_ck']=phase
        
        
        self.configure(yamlNode=nestedConf.to_dict())
        self.resettdc()	# Reset MasterTDCs
        print("Configure and tdc reset")
        

    def lg_hg_deactivate(self,process = 'int', subprocess = 'conv', injectedChannel = 0, lg=0, hg=0):
        nestedConf = nested_dict()
        if process == 'int':
            if subprocess == 'conv': #I.e. this step should only be performed for internal conveyor injection (still do not know why?)    
                print("Ruecksetzen High- LowRange Kanal: ", injectedChannel)
                [nestedConf[key]['sc']['ch'][injectedChannel].update({'LowRange':lg}) for key in self.yamlConfig.keys() if key.find('roc_s')==0 ] 
                [nestedConf[key]['sc']['ch'][injectedChannel].update({'HighRange':hg}) for key in self.yamlConfig.keys() if key.find('roc_s')==0 ]
            elif subprocess == 'preamp':
                pass #Do nothing
                print ("Low range and high range NOT reset")        
        elif process == 'ext':
            pass #Do nothing
            print ("Low range and high range NOT reset")        

class daqController(zmqController):
    def start(self):
        status="none"
        while status.lower().find("running")<0: 
            self.socket.send_string("start")
            status = self.socket.recv_string()
            print(status)

    def is_done(self):
        self.socket.send_string("status")
        status = self.socket.recv_string()
        if status.lower().find("configured")<0:
            return False
        else:
            return True

    def delay_scan(self):
        # only for daq server to run a delay scan
        rep=""
        while rep.lower().find("delay_scan_done")<0: 
            self.socket.send_string("delayscan")
            rep = self.socket.recv_string()
        print(rep)
	
    def stop(self):
        self.socket.send_string("stop")
        rep = self.socket.recv_string()
        print(rep)
        
    def enable_fast_commands(self,random=0,external=0,sequencer=0,ancillary=0):
        self.yamlConfig['daq']['l1a_enables']['random_l1a']         = random
        self.yamlConfig['daq']['l1a_enables']['external_l1as']      = external
        self.yamlConfig['daq']['l1a_enables']['block_sequencer']    = sequencer

    def l1a_generator_settings(self,name='A',enable=0x0,BX=0x10,length=43,flavor='L1A',prescale=0,followMode='DISABLE'):
        for gen in self.yamlConfig['daq']['l1a_generator_settings']:
            if gen['name']==name:
                gen['BX']         = BX
                gen['enable']     = enable
                gen['length']     = length
                gen['flavor']     = flavor
                gen['prescale']   = prescale
                gen['followMode'] = followMode
        
    def l1a_settings(self,bx_spacing=43,external_debounced=0,ext_delay=0,prescale=0,log2_rand_bx_period=0):#,length=43
        self.yamlConfig['daq']['l1a_settings']['bx_spacing']          = bx_spacing
        self.yamlConfig['daq']['l1a_settings']['external_debounced']  = external_debounced
        # self.yamlConfig['daq']['l1a_settings']['length']              = length
        self.yamlConfig['daq']['l1a_settings']['ext_delay']           = ext_delay
        self.yamlConfig['daq']['l1a_settings']['prescale']            = prescale
        self.yamlConfig['daq']['l1a_settings']['log2_rand_bx_period'] = log2_rand_bx_period
        
    def ancillary_settings(self,bx=0x10,prescale=0,length=100):
        self.yamlConfig['daq']['ancillary_settings']['bx']       = bx
        self.yamlConfig['daq']['ancillary_settings']['prescale'] = prescale
        self.yamlConfig['daq']['ancillary_settings']['length']   = length
        
    def daq_pedestal_settings(self,active_menu = 'randomL1A', num_events=10000, log2_rand_bx_period=0, bx_min=45):
        self.yamlConfig['daq']['active_menu']=active_menu
        self.yamlConfig['daq']['menus'][active_menu]['NEvents']=num_events 
        self.yamlConfig['daq']['menus'][active_menu]['log2_rand_bx_period']=log2_rand_bx_period
        self.yamlConfig['daq']['menus'][active_menu]['bx_min']=bx_min
        
    def daq_sampling_scan_settings(self,active_menu = 'calibAndL1A', num_events = 2500, calibType = 'CALPULEXT', lengthCalib = 1, lengthL1A = 1, bxCalib = 16, bxL1A = 20, prescale = 0, repeatOffset = 0):
        self.yamlConfig['daq']['active_menu']=active_menu
        self.yamlConfig['daq']['menus'][active_menu]['NEvents']=num_events #-----1000 in original
        self.yamlConfig['daq']['menus'][active_menu]['calibType']=calibType #-----1000 in original
        
        self.yamlConfig['daq']['menus'][active_menu]['lengthCalib']=lengthCalib
        self.yamlConfig['daq']['menus'][active_menu]['lengthL1A']=lengthL1A
        
        self.yamlConfig['daq']['menus'][active_menu]['bxCalib']=bxCalib
        self.yamlConfig['daq']['menus'][active_menu]['bxL1A']=bxL1A
        
        self.yamlConfig['daq']['menus'][active_menu]['prescale']=prescale
        self.yamlConfig['daq']['menus'][active_menu]['repeatOffset']=repeatOffset    # was 700
        

def pre_init(options):
    
    daqsocket = daqController(options.hexaIP,options.daqPort,options.configFile)
    clisocket = daqController("localhost",options.pullerPort,options.configFile)
    clisocket.yamlConfig['client']['serverIP'] = options.hexaIP
    i2csocket = i2cController(options.hexaIP,options.i2cPort,options.configFile)

    if options.initialize==True:
        i2csocket.initialize()
        daqsocket.initialize()
        clisocket.yamlConfig['client']['serverIP'] = daqsocket.ip
        clisocket.initialize()
    else:
        i2csocket.configure()
        
    print("Port objects",daqsocket,clisocket)
    
    if type(i2csocket) != i2cController:
        print( "ERROR in pedestal_run : i2csocket should be of type %s instead of %s"%(i2cController,type(i2csocket)) )
        sleep(1)
        return
    if type(daqsocket) != daqController:
        print( "ERROR in pedestal_run : daqsocket should be of type %s instead of %s"%(daqController,type(daqsocket)) )
        sleep(1)
        return
    
    if type(clisocket) != daqController:
        print( "ERROR in pedestal_run : clisocket should be of type %s instead of %s"%(daqController,type(clisocket)) )
        sleep(1)
        return
    
    return daqsocket, clisocket, i2csocket
    
