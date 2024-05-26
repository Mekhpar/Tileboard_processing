import subprocess
import sys
import pandas as pd
import datetime
from TableController import TableController




positionData = pd.read_csv('hit_positions_A5_25p.csv')
#print(positionData.ch[0:1])
tableController = TableController()
tableController.connect()
for ch in positionData.ch:
    #if ch not in [3,1]:
    #    continue
    while True:
        try:
        
            positionData['ch'] = positionData['ch'].round(0).astype('int')
            #print(positionData)
            #if ch not in [7,52]:
            xpos = positionData[positionData['ch']==ch]['x'].values[0]
            ypos = positionData[positionData['ch']==ch]['y'].values[0]
            print ("Now moving to ch=",ch,'pos=',xpos,ypos)
            tableController.move_vertical(ypos)
            tableController.move_horizontal(xpos)
                
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            proc_bob = subprocess.Popen(
            args=['ssh','-T','reinecke@flchcallab7','cd /home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script;source /opt/hexactrl/ROCv3-0811/ctrl/etc/env.sh;python3 beam_run_remote_May2024.py -f configs/ -i 10.254.56.35 -d TB3_A5_6 -c %i -I'%(ch)],
            stdout=sys.stdout,
            stderr=sys.stderr,
            shell=False
            )
            #while(not proc.poll()):
          
            
            
            proc_alice = subprocess.Popen(
            args=['cd /home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script;source /opt/hexactrl/ROCv3-0811/ctrl/etc/env.sh;python3 beam_run_remote_May2024.py -f configs/ -i 10.254.56.32 -d TB3_A5_5 -c %i -I'%(ch)],
            stdout=sys.stdout,
            stderr=sys.stderr,
            shell=True
            )
            #while(not proc.poll()):

            proc_alice.wait()
            #proc_bob.wait()    
            
            break
        except KeyboardInterrupt:
            interrupt = input("press 1 to skip channel, /npress 2 to exit program /nand any key to retake the data for this channel")
               
            if interrupt ==1 :
                break
                
            if interrupt == 2:
                sys.exit()
         
