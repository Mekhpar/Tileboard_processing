import zmq
import yaml
import util
import logging
from time import sleep
from nested_dict import nested_dict

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
    def __init__(self,ip,port,fname="configs/init.yaml",logging_level='INFO'):
        context = zmq.Context()
        self.ip=ip
        self.port=port
        self.socket = context.socket( zmq.REQ )
        self.socket.connect("tcp://"+str(ip)+":"+str(port))
        with open(fname) as fin:
            self.yamlConfig=yaml.safe_load(fin)
        self.logger = logging.getLogger('zmqController')
        util.setLoggingLevel(logging_level,'zmqController')

    def close(self):
        self.socket.close()

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
            self.logger.error('zmqController.update_yamlConfig should be called with either fname or yamlNode argument')
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
        self.logger.info(f'returned status (from initialize) = {rep}')
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
        self.logger.info(f'returned status (from configure) = {rep}')


class i2cController(zmqController):    
    def __init__(self,ip,port,fname="configs/init.yaml",logging_level='INFO'):
        super().__init__(ip,port,fname)
        #super(i2cController, self).__init__(ip,port,fname)
        self.logger = logging.getLogger('i2cController')
        util.setLoggingLevel(logging_level,'i2cController')
        self.maskedDetIds=[]
    
    def read_loop(self,yamlNode=None):
        self.socket.send_string("read_loop", zmq.SNDMORE)
        if yamlNode:
            self.socket.send_string( yaml.dump(yamlNode) )
        else:
            config = self.yamlConfig
            self.socket.send_string(yaml.dump(config))

        yamlread = yaml.safe_load( self.socket.recv_string() )
        return( yamlread )

    def break_loop(self):
        self.socket.send_string("break_loop")
        rep = self.socket.recv_string()
        print(rep)
    
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

    def initialize_adc(self,yamlNode):
        ## only valid for hexaboard/trophy systems
        self.socket.send_string("initialize_adc",zmq.SNDMORE)
        self.socket.send_string(yaml.dump(yamlNode))
        rep = self.socket.recv_string()
        return( yaml.safe_load(rep) )
    
    def calib_adc_offset(self,yamlNode):
        self.socket.send_string("calib_adc_offset",zmq.SNDMORE)
        if not yamlNode is None:
            config = yamlNode
        else:
            config = self.yamlConfig
        self.socket.send_string(yaml.dump(config))
        rep = self.socket.recv_string()
        offset = yaml.safe_load(rep)
        return( offset )

    def meas_adc_temp(self,yamlNode):
        self.socket.send_string("meas_adc_temp",zmq.SNDMORE)
        if not yamlNode is None:
            config = yamlNode
        else:
            config = self.yamlConfig
        self.socket.send_string(yaml.dump(config))
        rep = self.socket.recv_string()
        temperature = yaml.safe_load(rep)
        return( temperature )

    def meas_rtd_temp(self,yamlNode):
        self.socket.send_string("meas_rtd_temp",zmq.SNDMORE)
        if not yamlNode is None:
            config = yamlNode
        else:
            config = self.yamlConfig
        self.socket.send_string(yaml.dump(config))
        rep = self.socket.recv_string()
        temperature = yaml.safe_load(rep)
        return( temperature )
        
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

    def addMaskedDetId(self,detid):
        self.maskedDetIds.append(detid)

    def rmMaskedDetId(self,detid):
        self.maskedDetIds.remove(detid)

    def configure_injection(self,injectedChannels, activate=0, gain=0, phase=None, calib_dac=0):
        nestedConf = nested_dict()
        for key in self.yamlConfig.keys():
            if key.find('roc_s')==0:
                if calib_dac == -1:
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['IntCtest']=0
                else:
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['IntCtest'] = activate
                    nestedConf[key]['sc']['ReferenceVoltage']['all']['Calib'] = calib_dac
                if not None==phase: # no default phase, we don't change when not set
                    nestedConf[key]['sc']['Top']['all']['phase_ck'] = phase
                for injectedChannel in injectedChannels:
                    nestedConf[key]['sc']['ch'][injectedChannel]['LowRange'] = 0
                    nestedConf[key]['sc']['ch'][injectedChannel]['HighRange'] = 0
                    if gain==0:
                        nestedConf[key]['sc']['ch'][injectedChannel]['LowRange'] = activate
                    else:
                        nestedConf[key]['sc']['ch'][injectedChannel]['HighRange'] = activate
        self.configure(yamlNode=nestedConf.to_dict())
        if not None==phase:
            self.resettdc()	# Reset MasterTDCs

    def initMasterTDC(self):
        print(" ############## Starting up the MASTER TDCs #################")
        nestedConf = nested_dict()
        for key in self.yamlConfig.keys():
            if key.find('roc_s')==0:
                nestedConf[key]['sc']['MasterTdc']['all']['EN_MASTER_CTDC_VOUT_INIT']=1
                nestedConf[key]['sc']['MasterTdc']['all']['VD_CTDC_P_DAC_EN']=1
                nestedConf[key]['sc']['MasterTdc']['all']['VD_CTDC_P_D']=16
                nestedConf[key]['sc']['MasterTdc']['all']['EN_MASTER_FTDC_VOUT_INIT']=1
                nestedConf[key]['sc']['MasterTdc']['all']['VD_FTDC_P_DAC_EN']=1
                nestedConf[key]['sc']['MasterTdc']['all']['VD_FTDC_P_D']=16
        self.update_yamlConfig(yamlNode=nestedConf.to_dict())
        self.configure()
        nestedConf = nested_dict()
        for key in self.yamlConfig.keys():
            if key.find('roc_s')==0:
                nestedConf[key]['sc']['MasterTdc']['all']['EN_MASTER_CTDC_VOUT_INIT']=0
                nestedConf[key]['sc']['MasterTdc']['all']['EN_MASTER_FTDC_VOUT_INIT']=0

        self.update_yamlConfig(yamlNode=nestedConf.to_dict())
        self.configure()
       
    #==============================added the SCA function ===============Jia-Hao 28 June 2024 - start
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
    
    #==============================added the SCA function ===============Jia-Hao 28 June 2024 - end
    #======================================added by Jia-Hao, 4 July 2024 - start=========

    
    def set_gpio_direction(self, pin_number, pin_dir):
        self.socket.send_string("set_gpio_direction "+str(pin_number)+" "+str(pin_dir))
        return(self.socket.recv_string())
        
    def write_gpio(self, pin_number, pin_value):
        self.socket.send_string("write_gpio "+str(pin_number)+" "+str(pin_value))
        return(self.socket.recv_string()) 
 
    def read_gpio(self,pin):
        self.socket.send_string("read_gpio "+str(pin))
        gpio_val = self.socket.recv_string()
        return(gpio_val)    
        
    #======================================added by Jia-Hao, 4 July 2024 - end=========


class daqController(zmqController):
    def __init__(self,ip,port,fname="configs/init.yaml",logging_level='INFO'):
        #super(daqController, self).__init__(ip,port,fname)
        super().__init__(ip,port,fname)
        self.logger = logging.getLogger('daqController')
        util.setLoggingLevel(logging_level,'daqController')
        self.maskedDetIds=[]

    def start(self):
        status="none"
        while status.lower().find("running")<0: 
            self.socket.send_string("start")
            status = self.socket.recv_string()
            self.logger.info(f'status after start cmd : {status}')

    def is_done(self):
        self.socket.send_string("status")
        status = self.socket.recv_string()
        if status.lower().find("configured")<0:
            return False
        else:
            return True

    def delay_n(self):
        # only for daq server to run a delay scan
        rep=""
        while rep.lower().find("delay_scan_done")<0: 
            self.socket.send_string("delayscan")
            rep = self.socket.recv_string()
        self.logger.info(f'received from delay_scan cmd : {rep}')
	
    def stop(self):
        self.socket.send_string("stop")
        rep = self.socket.recv_string()
        self.logger.info(f'received from stop cmd : {rep}')
        
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
            
