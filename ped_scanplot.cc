#include "TStyle.h"
#include "TGraph.h"
#include "TH1.h"
#include "TCanvas.h"
#include "TPad.h"
#include "TAxis.h"
#include "TGaxis.h"
#include "TLegend.h"
#include <TMath.h>
#include <TString.h>
#include <vector>
#include <iostream>
#include <sstream>
#include <cmath>
#include <utility>
#include <fstream>
#include <algorithm>
#include <TMultiGraph.h>

void ped_scanplot()
{
TFile *_file0 = new TFile("/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3/TB3_D8_11/PreampInjection_scan_TB3_D8_11_2/injection_scan79.root");

TTree *adc = (TTree *)_file0->Get("runsummary/summary");
adc->SetMarkerStyle(20);
adc->SetMarkerSize(0.5);
adc->Draw("adc_median:channel","channeltype==0 & corruption==0");
}
