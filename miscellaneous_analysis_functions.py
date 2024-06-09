from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
import seaborn as sns
sns.set_style("ticks")
from matplotlib.ticker import MultipleLocator
import yaml, os
from typing import List

from nested_dict import nested_dict

import pandas as pd
import numpy as np
import copy

#This assumes the config file is named in a somewhat specific format - either convgain"value" or gainconv"value" (no spaces and no underscore and the search is not case specific)
def get_conveyor_gain(config_file):
    search_string = config_file.lower()
    gain_start = search_string.find("gain")
    conv_start = search_string.find("conv")
    conveyor_gain = ''
    flag = 0
    
    if search_string[gain_start+4].isdigit():
        flag = 1
        search_begin = gain_start+4
        
    elif search_string[conv_start+4].isdigit():
        flag = 1
        search_begin = conv_start+4
    
    else:
        print("Wrong format for file name!")
    
    if flag == 1:
        for i in range(search_begin,len(search_string)):
            cur_char = search_string[i]
            print()
            if cur_char.isdigit():
                conveyor_gain+=cur_char
            else:
                break
        #print(conveyor_gain)
        return(float(conveyor_gain))
    
def set_key_dict(nestedConf:dict, level_keys:List[str], bottom_level_keys:List[str], key_values:List[float]):
    if len(bottom_level_keys) != len(key_values):
        print("Insufficient number of channelwise parameters")

    elif len(bottom_level_keys) == len(key_values):
        #print()
        #print(level_keys)
        level = len(level_keys)
        #print("Level of the key",level)
        if level > 0:
            cur_key = level_keys.pop()
            #print("Current level key",cur_key)

            if cur_key not in nestedConf:
                nestedConf.setdefault(cur_key,dict())
            
            #print(nestedConf)
            nestedConf[cur_key] = set_key_dict(nestedConf[cur_key], level_keys, bottom_level_keys, key_values)
        
        elif level == 0:
            for i in range(len(bottom_level_keys)):
                nestedConf.setdefault(bottom_level_keys[i],key_values[i])

    return nestedConf
    
def merge_nested(a:nested_dict,b:nested_dict):
    print("Original safe load array",b)
    for key in a.keys():
        if key in b.keys():
            print("common key exists")
            print(key)
            #print(a[key])
            #print(b[key])
            #print()
            merge_nested_pedestal(a[key],b[key])
        else:
            ("No common key")
            print(str(key))
            print(a[key])
            
            b[key] = copy.deepcopy(a[key])
            #print(type(b))
            #print(b[key])
    return b           
      
