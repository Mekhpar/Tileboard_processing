import zmq, datetime,  os, subprocess, sys, yaml, glob

import myinotifier,util,math, datetime
import analysis.level0.pedestal_run_analysis as analyzer
import zmq_controler as zmqctrl
import miscellaneous_functions as misc_func
from nested_dict import nested_dict
from time import sleep

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
        '1V': {'A':192,'B':121},
        '1V4': {'A':192,'B':121},
        '1V6': {'A':193,'B':121},
        '1V8': {'A':194,'B':122},
        '2V': {'A':195,'B':122},
        '2V2': {'A':196,'B':124},
        '3V': {'A':200,'B':124},
        '3V5': {'A':203,'B':125},
        '4V': {'A':205,'B':126},
        '4V5': {'A':208,'B':127},
        '5V': {'A':210,'B':128},
        '5V5': {'A':213,'B':129},
        '6V': {'A':215,'B':130}}
    }



def read_sca_config(i2csocket,daqsocket, clisocket, basedir,device_name,tileboard,OV):

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    testName = "TB2_SlowControl"
    odir = "%s/%s/slow_control/run_%s/"%( os.path.realpath(basedir), device_name, timestamp )
    os.makedirs(odir)

    mylittlenotifier = myinotifier.mylittleInotifier(odir=odir)
    mylittlenotifier.start()

    #======================================change for v3 tile board test==============
    #daqsocket.yamlConfig['daq']['NEvents']='0'   # was 10000
    #daqsocket.enable_fast_commands(random=1)
    #daqsocket.l1a_settings(bx_spacing=45)
    #daqsocket.configure()
 
    clisocket.yamlConfig['client']['outputDirectory'] = odir
    clisocket.yamlConfig['client']['run_type'] = testName
    clisocket.configure()
    
    daqsocket.daq_pedestal_settings('randomL1A',0,0,45) #different number of events, should override the one in zmq_controler.py
    daqsocket.configure()
    
    nestedConf = nested_dict()

    print(" ")
    print(" ")
    print(" Slow-Control from GBT_SCA ")
    print(" ")

    outdir = odir
    path=outdir
    fout=open(outdir+"TB3_info.txt", "x")
    print("Text file object type", type(fout))
    fout.write("#  Tileboard3 Slow Control Data" + '\n')
    fout.write("#  Date, Time: " + timestamp + '\n')


    ##### Set GPIOs  ################

    print("Set GPIOs")
    i2csocket.set_gbtsca_gpio_direction(0x0fffff9C) # '0': input, '1': output

    # enable MPPC_BIAS1 ("1"), disable MPPC_BIAS2 ("0"): GPIOs 20, 21
    i2csocket.set_gbtsca_gpio_vals(0x00100000,0x00300000) # First argument: GPIO value, 2nd argument: Mask

    # global enable LED system: LED_ON_OFF ('1': LED system ON), GPIO7:
    #i2csocket.set_gbtsca_gpio_vals(0x00000000,0x00000080) # LED OFF First argument: GPIO value, 2nd argument: Mask
    i2csocket.set_gbtsca_gpio_vals(0x00000080,0x00000080) # LED ON First argument: GPIO value, 2nd argument: Mask

    # put LED_DISABLE1 and LED_DISABLE2 to '0' ('0': LED system ON), GPIOs 8-15
    #i2csocket.set_gbtsca_gpio_vals(0x00000000,0x0000ff00) # First argument: GPIO value, 2nd argument: Mask
    i2csocket.set_gbtsca_gpio_vals(0x00000000,0x0000ff00) # First argument: GPIO value, 2nd argument: Mask
    
    # switch on Enable of LDOs and Softstart
    
    print("switch on LDOs in softstart mode")
    
    i2csocket.set_gbtsca_gpio_vals(0x00800000,0x00800000) # First argument: GPIO value, 2nd argument: Mask. Set SOFTSTART ON
    sleep(1)
    
    i2csocket.set_gbtsca_gpio_vals(0x00400000,0x00400000) # First argument: GPIO value, 2nd argument: Mask. Set EN_LDO ON
    sleep(1)
    
    '''
    # enable this section to include a HARD RESET of the HGCROC
    print(" ")
    print("HARD RESET of HGCROC")
     # set HARD_RSTB to 0 and back to 1
    i2csocket.set_gbtsca_gpio_vals(0x00000000,0x00000010) # First argument: GPIO value, 2nd argument: Mask
    i2csocket.set_gbtsca_gpio_vals(0x00000010,0x00000010) # First argument: GPIO value, 2nd argument: Mask
    print("HARD RESET of HGCROC done")
    print(" ")
    sleep(1)
    '''
    
    '''
    # enable this section to change the LDO output voltages
    print(" ")
    print("LDO adjustment")
    i2csocket.set_gbtsca_gpio_vals(0x00000000,0x0F000000) # First argument: GPIO value, 2nd argument: Mask
    # i2csocket.set_gbtsca_gpio_vals(0x02000000,0x02000000) # VDDD up by 50mV
    # i2csocket.set_gbtsca_gpio_vals(0x01000000,0x01000000) # VDDD down by 50mV
    # i2csocket.set_gbtsca_gpio_vals(0x04000000,0x02000000) # VDDA down by 50mV
    # i2csocket.set_gbtsca_gpio_vals(0x08000000,0x01000000) # VDDA up by 50mV
    # i2csocket.set_gbtsca_gpio_vals(0x00000000,0x0F000000) # set LDOs to default
    sleep(1)
    print("LDO adjustment done")
    print(" ")
    '''

    print("GPIO values are",hex(int(i2csocket.read_gbtsca_gpio())))   # should give 0x1000Cf in normal operation with MPPC_BIAS1 ON
    print("GPIO directions are",hex(int(i2csocket.get_gbtsca_gpio_direction())))
    
    daqsocket.configure()


    ##### Set GBT_SCA DACs for MPPC Bias Voltage (Reference)  ################

    '''
    first column: DAC0 ('DAC A') setting
    2nd column: DAC1 ('DAC B') setting
    3rd column: MPPC_BIAS1, measured at ALDOv2 output with multimeter

    BV_IN = 46.5V (Tileboard BV input)

    Caution: Do not apply higher voltages than 6V overvoltage
    Caution: Do never supply BV_IN > 50V to the Tileboard


    '''
    print("Set DACs")
    ######################
    # Set DACs of GBT_SCA TB2
    # Bias Voltage = 41.5V (OV = 2.0V)
    
    
    dac_array = ["A","B","C","D"]
    value_array = [194,122,182,120]
    for i in range(0,len(dac_array)):
        i2csocket.set_gbtsca_dac(dac_array[i],value_array[i])
        print("Dac",dac_array[i],"value is now",i2csocket.read_gbtsca_dac(dac_array[i]))


    # "sleep" is only required when SiPM bias voltage is changed:
    print(" ")
    print(" Please wait for voltage stabilization (5seconds)")
    sleep(3)   # wait 3s for stabilization of voltages before readback


    ########################   ADCs   ####################

    print(" ")
    print(" ADCs: ")

    A_T = 3.9083e-3
    B_T = -5.7750e-7
    R0 = 1000
    SCA_ADC_range = range(0, 8)
    for sca_adc in SCA_ADC_range:
       ADC = i2csocket.read_gbtsca_adc(sca_adc)
       T1 = round(float((-R0*A_T + math.sqrt(math.pow(R0*A_T, 2) - 4*R0*B_T*(R0-(1800 / ((2.5*4095/float(ADC))-1))))) / (2*R0*B_T)),1)
       print("T", sca_adc,  ":", str(T1))
       fout.write("T" + str(sca_adc) +": "+str(T1) + '\n')
       
    #SiPM bias values (input, Ch 1 and Ch 2)   
    i2csocket.read_convert(out_dir = fout, variable_name = "MPPC_BIAS_IN", adc_pin = 18, numerator = 330500, denominator = 6490, round_off = 4)
    i2csocket.read_convert(out_dir = fout, variable_name = "MPPC_BIAS1", adc_pin = 9, numerator = 330500, denominator = 6490, round_off = 4)
    i2csocket.read_convert(out_dir = fout, variable_name = "MPPC_BIAS2", adc_pin = 10, numerator = 330500, denominator = 6490, round_off = 4)
    
    ADC = i2csocket.read_gbtsca_adc(29)
    CURHV0 = round(float(ADC)/4095, 4)
    print("CURHV0 = ", str(CURHV0), ", current [mA] (U/27kOhm*800): ", str(round(float(CURHV0/27000*800*1000), 3)))
    fout.write("CURHV0: " + str(CURHV0) + '\n')
    
    ADC = i2csocket.read_gbtsca_adc(30)
    CURHV1 = round(float(ADC)/4095, 4)
    print("CURHV1 = ", str(CURHV1), ", current [mA] (U/27kOhm*800): ", str(round(float(CURHV1/27000*800*1000), 3)))
    fout.write("CURHV1: " + str(CURHV1) + '\n')

    #Other supplied voltages (tileboard and LED)
    i2csocket.read_convert(out_dir = fout, variable_name = "VCC_IN", adc_pin = 11, numerator = 60700, denominator = 4700, round_off = 3)
    i2csocket.read_convert(out_dir = fout, variable_name = "LED_BIAS", adc_pin = 12, numerator = 60700, denominator = 4700, round_off = 3)
    
    #Chip input voltages (from the ALDO)
    i2csocket.read_convert(out_dir = fout, variable_name = "VPA (HGCROC -> +2.5V)", adc_pin = 13, numerator = 4000, denominator = 1000, round_off = 3)
    i2csocket.read_convert(out_dir = fout, variable_name = "VCC_GBTSCA (+1.5V)", adc_pin = 8, numerator = 2000, denominator = 1000, round_off = 3)
    i2csocket.read_convert(out_dir = fout, variable_name = "PRE_VPA (around +3.5V)", adc_pin = 14, numerator = 4000, denominator = 1000, round_off = 3)
    
    #LDO input and output voltages
    i2csocket.read_convert(out_dir = fout, variable_name = "VDDA (+1.2V)", adc_pin = 15, numerator = 2000, denominator = 1000, round_off = 3)
    i2csocket.read_convert(out_dir = fout, variable_name = "VDDD (+1.2V)", adc_pin = 16, numerator = 2000, denominator = 1000, round_off = 3)
    i2csocket.read_convert(out_dir = fout, variable_name = "PRE_VDDA (+1.5V)", adc_pin = 17, numerator = 2000, denominator = 1000, round_off = 3)
    
    #??
    i2csocket.read_convert(out_dir = fout, variable_name = "TB_ID0 (+0.2V)", adc_pin = 26, numerator = 1, denominator = 1, round_off = 2)
    i2csocket.read_convert(out_dir = fout, variable_name = "TB_ID1 (+0.0V)", adc_pin = 27, numerator = 1, denominator = 1, round_off = 2)

    i2csocket.read_convert(out_dir = fout, variable_name = "PROBE_DC_L1", adc_pin = 22, numerator = 1, denominator = 1, round_off = 2)
    i2csocket.read_convert(out_dir = fout, variable_name = "PROBE_DC_L2", adc_pin = 23, numerator = 1, denominator = 1, round_off = 2)
    i2csocket.read_convert(out_dir = fout, variable_name = "PROBE_DC_R1", adc_pin = 24, numerator = 1, denominator = 1, round_off = 2)
    i2csocket.read_convert(out_dir = fout, variable_name = "PROBE_DC_R2", adc_pin = 25, numerator = 1, denominator = 1, round_off = 2)

    ########################   GPIOs    ####################

    print(" ")
    print(" GPIOs")

    SCA_IOS = int(i2csocket.read_gbtsca_gpio())

    print("PLL_LCK (no error = 1): ", hex(SCA_IOS & 0x00000001))
    fout.write("PLL_LCK " + str(hex(SCA_IOS & 0x00000001)) + '\n')

    print("ERROR (no error = 1): ", hex((SCA_IOS & 0x00000002)>>1))
    fout.write("ERROR: " + str(hex((SCA_IOS & 0x00000002)>>1)) + '\n')

    print("SOFT_RSTB (no reset = 1): ", hex((SCA_IOS & 0x00000004)>>2))
    fout.write("SOFT_RSTB: " + str(hex((SCA_IOS & 0x00000004)>>2)) + '\n')

    print("I2C_RSTB (no reset = 1): ", hex((SCA_IOS & 0x00000008)>>3))
    fout.write("I2C_RSTB: " + str(hex((SCA_IOS & 0x00000008)>>3)) + '\n')

    print("HARD_RSTB (no reset = 1): ", hex((SCA_IOS & 0x00000010)>>4))
    fout.write("HARD_RSTB: " + str(hex((SCA_IOS & 0x00000010)>>4)) + '\n')
    
    print("PLL_LCK 2nd ROC (no error = 1): ", hex((SCA_IOS & 0x00000020)>>5))
    fout.write("PLL_LCK 2nd ROC: " + str(hex((SCA_IOS & 0x00000020)>>4)) + '\n')

    print("ERROR 2nd ROC (no error = 1): ", hex((SCA_IOS & 0x00000040)>>6))
    fout.write("ERROR 2nd ROC: " + str(hex((SCA_IOS & 0x00000040)>>6)) + '\n')

    print("LED_ON_OFF (1: ON): ", hex((SCA_IOS & 0x00000080)>>7))
    fout.write("LED_ON_OFF: " + str(hex((SCA_IOS & 0x00000080)>>7)) + '\n')

    for i in range(1,9):
        bit_pos = 0x00000100*(2**(i-1))
        print(hex(bit_pos))
        print("LED_DISABLE",i," (1: OFF): ", hex((SCA_IOS & bit_pos)>>i+7))
        fout.write("LED_DISABLE"+str(i)+": " + str(hex((SCA_IOS & bit_pos)>>i+7)) + '\n')
    
    print("EN_HV0 (ALDOV2 BV1 (1: ON): ", hex((SCA_IOS & 0x00100000)>>20))
    fout.write("EN_HV0: " + str(hex((SCA_IOS & 0x00100000)>>20)) + '\n')

    print("EN_HV1 (ALDOV2 BV2 (1: ON): ", hex((SCA_IOS & 0x00200000)>>21))
    fout.write("EN_HV1: " + str(hex((SCA_IOS & 0x00200000)>>21)) + '\n')
    
    print("EN_LDO VDDA and VDDD (1: ON): ", hex((SCA_IOS & 0x00400000)>>22))
    fout.write("EN_LDO: " + str(hex((SCA_IOS & 0x00400000)>>22)) + '\n')

    print("EN_SOFTSTART VDDA and VDDD (1: ON): ", hex((SCA_IOS & 0x00800000)>>23))
    fout.write("EN_SOFTSTART: " + str(hex((SCA_IOS & 0x00800000)>>23)) + '\n')

    ########################   DACs   ####################

    print(" ")
    print(" DACs:")
    for i in range(0,len(dac_array)):
        print("SCA DAC",dac_array[i],"(BV1 coarse) value: ",i2csocket.read_gbtsca_dac(dac_array[i]))
        fout.write("DAC_"+dac_array[i]+": " + i2csocket.read_gbtsca_dac(dac_array[i]) + '\n')

    fout.close()

    i2csocket.configure(yamlNode=nestedConf.to_dict())


    # nestedConf = nested_dict()
    # for key in i2csocket.yamlConfig.keys():
    #     if key.find('roc_s')==0:
    #         for ch in range(0,36):
    #             nestedConf[key]['sc']['ch'][ch]['Channel_off']=1
    #         nestedConf[key]['sc']['calib'][0]['Channel_off']=1
    # i2csocket.update_yamlConfig(yamlNode=nestedConf.to_dict())
    # i2csocket.configure()

    # util.saveFullConfig(odir=odir,i2c=i2csocket,daq=daqsocket,cli=clisocket)
    # util.saveMetaYaml(odir=odir,i2c=i2csocket,daq=daqsocket,runid=0,testName=testName,keepRawData=1,chip_params={})

    # util.acquire(daq=daqsocket, client=clisocket)
    mylittlenotifier.stop()
    

    # ped_analyzer = analyzer.pedestal_run_analyzer(odir=odir)
    files = glob.glob(odir+"/*.root")

    for f in files:
        print("files:",f)
        ped_analyzer.add(f)

    # ped_analyzer.mergeData()
    # ped_analyzer.makePlots()
    return odir




if __name__ == "__main__":
    parser = misc_func.options_run()#This will be constant for every test irrespective of the type of test
    
    #Two extra options custommade just for this slow control script
    parser.add_option("-b","--tileboard", action="store", dest="tileboard",default='TB2.1_3', help="tileboard in use")
    parser.add_option("-v","--overvoltage", action="store", dest="OV",default='2V', help="overvoltage to be used")

    (options, args) = parser.parse_args()
    print(options)

    (daqsocket,clisocket,i2csocket) = zmqctrl.pre_init(options)
    
    read_sca_config(i2csocket,daqsocket,clisocket,options.odir,options.dut,options.tileboard,options.OV)
