from touchcomm import TouchComm
import numpy as np
import sys
import json

REPORT_ID = 0x13
marginHybridAnalogADC = 1000

def update_static_config(handle, config, config_to_set, bWrite=False):
    try:
        for key in config_to_set:
            config_value = config_to_set[key]
            #print(key, '->', config_value)
            if isinstance(config_value, list):
                for idx, x in enumerate(config_value):
                    config[key][idx] = int(x)
            else:
                config[key] = int(config_value)
        if(bWrite):
            handle.setStaticConfig(config)

    except Exception as e:
        raise Exception(str(e))
    return config   

class HybridAnalogParamVariables():
    def __init__(self, handle, onX=True):
        self.handle = handle


        self.SFTYPE_ABSRX = np.array(['subFrameId_t','SFTYPE_ABSRX'])
        self.SFTYPE_ABSTX = np.array(['subFrameId_t','SFTYPE_ABSTX'])

        self.CapGlobal = "cbcGlobalCap"
        self.GlobalGain0150 = "cbcGlobalGain0150"
        self.GlobalGain5174 = "cbcGlobalGain5174"
        self.gcbcIdx = 0
        if onX:
            self.gcbcIdx = self.getEnum(self.SFTYPE_ABSRX)
            self.CBCs = "hybridXCBCs"
            self.CBCDriverEnable = "hybridXCBCDriverEn"
            self.CBCEffective = "effectiveHybridAnalogXGlobalCBC"
        else:
            self.gcbcIdx = self.getEnum(self.SFTYPE_ABSTX)
            self.CBCs = "hybridYCBCs"
            self.CBCDriverEnable = "hybridYCBCDriverEn"
            self.CBCEffective = "effectiveHybridAnalogYGlobalCBC"

        self.GCBCCap = 'cbcGlobalCap[{0}]'.format(self.gcbcIdx)
        self.GCBCInScale = 'tchCbcGlobalConfigCtl1[{0}].cbcGlobalInScale'.format(self.gcbcIdx)
        self.GCBCOutScale = 'tchCbcGlobalConfigCtl2[{0}].cbcGlobalOutScale'.format(self.gcbcIdx)
        self.GCBCDecayRate = 'tchCbcGlobalConfigCtl1[{0}].cbcGlobalDecayrate'.format(self.gcbcIdx)
        self.CBCCapGain01916 = 'tchCbcGlobalGain012[{0}].cbcGlobalGain01916'.format(self.gcbcIdx)
        self.CBCCapGain1 = 'tchCbcGlobalGain012[{0}].cbcGlobalGain1'.format(self.gcbcIdx)
        self.CBCCapGain2 = 'tchCbcGlobalGain012[{0}].cbcGlobalGain2'.format(self.gcbcIdx)
        self.CBCCapGain3 = 'tchCbcGlobalGain345[{0}].cbcGlobalGain3'.format(self.gcbcIdx)
        self.CBCCapGain4 = 'tchCbcGlobalGain345[{0}].cbcGlobalGain4'.format(self.gcbcIdx)
        self.CBCCapGain530 = 'tchCbcGlobalGain345[{0}].cbcGlobalGain530'.format(self.gcbcIdx)

        
    def getEnum(self, name):
        handle = self.handle
        id = handle.identify()

        handle.decoder.loadJSONFile(id)
        if handle.decoder.jsonLoaded():
            j = handle.decoder.jsonConfig['enums']
            for str in name:
                j = j[str]
            return j['value']

class HybridAnalogParamValues():
    def __init__(self, val=None):
        self.GLOBALCAP_LENGTH = 5
        self.OUTSCALE_DEFAULT = 31
        self.CapGlobal = np.empty(self.GLOBALCAP_LENGTH, dtype=int) 
        
        self.GCBCOutScale = self.OUTSCALE_DEFAULT
        self.GCBCInScale = 0
        self.gcbcIdx = 0
        self.CapScore = 0
        self.CapBest = 0
        self.GCBCCap = 0 
        self.CapStep = 0
        self.CapGlobal.fill(np.iinfo(np.int32).min)

        if isinstance(val, HybridAnalogParamValues):
            self.GCBCOutScale = val.GCBCOutScale
            self.gcbcIdx = val.gcbcIdx
            self.CapScore = val.CapScore
            self.CapBest = val.CapBest
            self.GCBCCap = val.GCBCCap
            self.CapStep = val.CapStep
            self.CapGlobal = val.CapGlobal
            self.setGCBCCap(val.getGCBCCap())
            self.GCBCInScale = val.GCBCInScale
            print("isinstance GCBCCap ", self.getGCBCCap(), self.gcbcIdx)

    def getGCBCCap(self):
        return self.CapGlobal[self.gcbcIdx]
    def setGCBCCap(self, value):
        self.CapGlobal[self.gcbcIdx] = value

class HybridAnalog():

    def __init__(self, handle):
        self.handle = handle

        self._nGlobalSignalLimitMax = 8191
        self._nGlobalSignalScoreAdjustment = 8
        self._nGlobalSignalScoreDeviation = (self._nGlobalSignalLimitMax + 1) / 2
        self._nGlobalCapacitanceMaxCBC = 127
        self._nGlobalCapacitanceOutScaleInit = 31
        self._nGlobalCapacitanceInScaleInit = 11
        self._nGlobalCapacitanceDecayRateInit = 5
        self._arrGlobalCapGainsInitial = [15, 63, 63, 63, 63, 15, 65535, 16383]
        self._strGlobalVarEnableScan = "enableHybridCBCScan"
        self._sc = self.handle.getStaticConfig()
        self._dc = self.handle.getDynamicConfig()
        self.onX = True
        self.paraName = HybridAnalogParamVariables(self.handle, self.onX)

        self._reports = []
        self._count = 1

    def set_dynamic_config(self):
        self.handle.setDynamicConfig(self._dc)   

    def InitializeGlobalCBC(self, valsData): 
        print("InitializeGlobalCBC")
        valsData.gcbcIdx = self.paraName.gcbcIdx
        valsData.setGCBCCap(self._nGlobalCapacitanceMaxCBC)
        valsData.GCBCInScale = self._nGlobalCapacitanceInScaleInit
        valsData.GCBCOutScale = self._nGlobalCapacitanceOutScaleInit
        #check parameter are exist
        print("CapGlobal arr index", valsData.CapGlobal,  valsData.gcbcIdx)
        self.set(valsData, False)
        print("CapGlobal arr index", valsData.CapGlobal,  valsData.gcbcIdx)
        #enable lcbc servo (servo on)
        self._sc = update_static_config(self.handle, self._sc, {self._strGlobalVarEnableScan: 1})
        #Keys Specific
        p = self.paraName
        self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain01916: self._arrGlobalCapGainsInitial[0]})
        self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain1: self._arrGlobalCapGainsInitial[1]})
        self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain2: self._arrGlobalCapGainsInitial[2]})
        self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain3: self._arrGlobalCapGainsInitial[3]})
        self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain4: self._arrGlobalCapGainsInitial[4]})
        self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain530: self._arrGlobalCapGainsInitial[5]})

        array = self._sc[p.GlobalGain0150]
        array[p.gcbcIdx] = self._arrGlobalCapGainsInitial[6]
        self._sc = update_static_config(self.handle, self._sc, {p.GlobalGain0150: array})

        array = self._sc[p.GlobalGain5174]
        array[p.gcbcIdx] = self._arrGlobalCapGainsInitial[7]
        self._sc = update_static_config(self.handle, self._sc, {p.GlobalGain5174: array})
        #set decay rate to max
        self._sc = update_static_config(self.handle, self._sc, {p.GCBCDecayRate: self._nGlobalCapacitanceDecayRateInit})
        #turn off analog-display noise suppression (since tuning is looking for
        #"clipping" via adc's)
        self._sc = update_static_config(self.handle, self._sc, {"adnsEnabled": 0}, True)
        return valsData

    def SetGlobalCBC(self, arrDataGains, bWrite):
        if bWrite:
            p = self.paraName
            self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain01916: arrDataGains[0]})
            self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain1: arrDataGains[1]})
            self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain2: arrDataGains[2]})
            self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain3: arrDataGains[3]})
            self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain4: arrDataGains[4]})
            self._sc = update_static_config(self.handle, self._sc, {p.CBCCapGain530: arrDataGains[5]})

            array = self._sc[p.GlobalGain0150]
            array[p.gcbcIdx] = arrDataGains[6]
            self._sc = update_static_config(self.handle, self._sc, {p.GlobalGain0150: array})

            array = self._sc[p.GlobalGain5174]
            array[p.gcbcIdx] = arrDataGains[7]
            self._sc = update_static_config(self.handle, self._sc, {p.GlobalGain5174: array}, True)
        return True

    def ScoreTuningValue(self):
        print("ScoreTuningValue")
        if(len(self._reports) > 0):
            data = self._reports[0]
        else:
            print("no data")
            raise Exception("'cannot get valid report")

        fDataMax = np.amax(data) / self._nGlobalSignalScoreAdjustment
        fDataMin = np.amin(data) / self._nGlobalSignalScoreAdjustment
        score = max(abs(fDataMax - self._nGlobalSignalScoreDeviation), abs(fDataMin - self._nGlobalSignalScoreDeviation))
        print("SCORE ", score)
        return score

    def GetTuningLimits(self):
        nMarginADC = marginHybridAnalogADC
        nDataMax = self._nGlobalSignalLimitMax - nMarginADC;
        nDataMin = 0 + nMarginADC;
        return nDataMax, nDataMin

    def set(self, valsData, bWrite):
        p = self.paraName
        valsData.gcbcIdx = p.gcbcIdx
        array = self._sc[p.CapGlobal]
        
        if len(array) > 0:
           array[p.gcbcIdx] = valsData.getGCBCCap()
           self._sc = update_static_config(self.handle, self._sc, {p.CapGlobal: array})
        self._sc = update_static_config(self.handle, self._sc, {p.GCBCInScale: valsData.GCBCInScale}, bWrite)

    def ValidateGlobalCBC(self, valsData):
        self.RunTuningReport(valsData)
        nDataMax, nDataMin = self.GetTuningLimits()
        data = self._reports[0]
        fDataMax = np.amax(data) / self._nGlobalSignalScoreAdjustment
        if fDataMax > nDataMax:
            return False
        return True
    
    def RunTuningReport(self, valsDataReport):
        self.set(valsDataReport, True)
        self.get_report()
        valsDataReport.CapScore = self.ScoreTuningValue()
 

    def CompareTuningValue(self):
        if len(self._reports) == 0: return False
        data = self._reports[0]
        fDataMax = np.amax(data)/ self._nGlobalSignalScoreAdjustment
        fDataMin = np.amin(data) / self._nGlobalSignalScoreAdjustment
        if abs(fDataMax - self._nGlobalSignalScoreDeviation) >= abs(fDataMin - self._nGlobalSignalScoreDeviation):
            return (fDataMin >= 0x08)
        return False

    def SearchBestGlobalCBC(self, valsData):
        print("SearchBestGlobalCBC")
        valsScore = HybridAnalogParamValues(valsData)

        valsScore.setGCBCCap(self._nGlobalCapacitanceMaxCBC)
        print("valueScore ", valsScore.getGCBCCap())
        valsScore.CapStep = (self._nGlobalCapacitanceMaxCBC + 1) / 2
        valsScore.CapBest = valsScore.CapScore = self._nGlobalSignalScoreDeviation + 1;
        while(True):
            self.RunTuningReport(valsScore)
            fScoreTuning = self.ScoreTuningValue()
            if (fScoreTuning <= valsScore.CapBest):
                valsBest = HybridAnalogParamValues(valsScore);
                valsScore.CapBest = fScoreTuning;

            if self.CompareTuningValue():
                valsScore.setGCBCCap(valsScore.getGCBCCap() + valsScore.CapStep)
            else:
                valsScore.setGCBCCap(valsScore.getGCBCCap() - valsScore.CapStep)
            print("valsScore.getGCBCCap() ", valsScore.getGCBCCap())
            valsScore.setGCBCCap( min(valsScore.getGCBCCap(), self._nGlobalCapacitanceMaxCBC))
            print("valsScore.CapStep " , int(valsScore.CapStep))
            if (int(valsScore.CapStep) == 0):
                print("break")
                break;
            valsScore.CapStep /= 2;
        valsData = valsBest;

    def RestoreGlobalCBC(self):
        print("RestoreGlobalCBC")
        self._sc = update_static_config(self.handle, self._sc, {self.paraName.CBCDriverEnable: 1})
        self._sc = update_static_config(self.handle, self._sc, {self._strGlobalVarEnableScan: 1}, True)


    def ConvertGlobalCBC(self,nDataChannel, nDataElectrode):
        print("ConvertGlobalCBC")
        nBaseElectrode = 0
        nBaseChannel = 0
        nDataFound = 0
        mapData = [
            [21, 20,  1, 20],
            [ 9,  8, 21, 19],
            [29, 22, 17,  3],
            [19, 10, 18,  0],
            [ 7,  0, 17,  3],
            [59, 50, 41, 23],
            [49, 40, 40, 22],
            [39, 30, 41, 23]]

        for i in range(len(mapData)):
            nEndElectrode = mapData[i][0]
            nStartElectrode = mapData[i][1]
            nEndChannel = mapData[i][2]
            nStartChannel = mapData[i][3]
            if i < 2:
                if nDataElectrode == nStartElectrode:
                    nDataChannel = nStartChannel
                    nDataFound += 1
                    return (nDataFound == 1), nDataChannel
                elif nDataElectrode == nEndElectrode:
                    nDataChannel = nEndChannel
                    nDataFound += 1
                    return (nDataFound == 1), nDataChannel
            else:
                if nDataElectrode >= nStartElectrode and nDataElectrode <= nEndElectrode:
                    nBaseElectrode = nStartElectrode
                    nBaseChannel = nStartChannel
                    nDataFound += 1
            
        nDataChannel = (nDataElectrode - nBaseElectrode) * 2 + nBaseChannel
        print("nDataChannel",nDataChannel)
        return (nDataFound == 1), nDataChannel

    def _CheckGlobalCBC(self, arr):
        print("_CheckGlobalCBC")
        nDataMax = 0
        nDataMin = 0
        nDataMax, nDataMin = self.GetTuningLimits()
        strXvsY = "imageRxes" if self.onX else "imageTxes"
        imageTRxes = self._sc[strXvsY]
        data = self._reports[0]
        print("data", data)
        fReportMax = float(abs(np.amax(data)) / self._nGlobalSignalScoreAdjustment)
        fReportMin = float(abs(np.amin(data)) / self._nGlobalSignalScoreAdjustment)
        if ((fReportMax > nDataMax) or (fReportMin < nDataMin)):
            listReportFail = []
            nReportChannel = 0
            for i in range(len(data)):
                value = float(abs(data[i])) / self._nGlobalSignalScoreAdjustment
                if  value < nDataMin or value > nDataMax:
                    ret, nReportChannel = self.ConvertGlobalCBC(nReportChannel, imageTRxes[i])
                    if(ret):
                        listReportFail.append(nReportChannel)
                    print("nReportChannel", nReportChannel)
            if len(listReportFail) > 0:
                print("listReportFail > 0")
            print("arr", arr)
            print("listReportFail",listReportFail)
            arr = listReportFail if (len(listReportFail) > 0) else None
            
            return False
        arr = None;
        return True
    
    def _AdjustGlobalCBC(self, arrDataGains, nDataChannel):
        nDataIndex = 0
        nDataBit = 0
        bDataTurn = False
        bDataFound = False
        mapData = [
            [ 3, 0, 20, 19, 18, 21],
            [ 5, 0,  0,  0],
            [ 5, 0, 17, 17],
            [ 5, 0, 23, 23],
            [ 5, 0, 40, 40],
            [ 3, 0, 26, 25, 24, 22],
            [ 15, 0, 16, 15, 14, 13, 12, 11, 10,  9,  8,  7,  6,  5,  4,  3,  2,  1],
            [ 14, 0, 38, 41, 39, 38, 37, 36, 35, 34 ,33 ,32 ,31, 30, 29, 28, 27]]
        for i in range(len(mapData)) and bDataFound == False:
            nEndConveyor = mapData[i][0], nStartConveyor = mapData[i][1]
            for j in range(2,len(mapData[i])):
                if nDataChannel == mapData[i][j]:
                    nDataIndex = i
                    nDataBit = (len(mapData[i]) - j - 1) + nStartConveyor
                    bDataFound = True
        if bDataFound and (nDataIndex < len(arrDataGains)):
            nDataMask = ((long)(0x0001)) << nDataBit
            if bDataTurn: arrDataGains[nDataIndex] |= nDataMask
            else: arrDataGains[nDataIndex] &= ~nDataMask
            return True
        return False

    def AdjustGlobalCBC(self, arrDataGains, arrDataChannels):
        for n in arrDataChannels:
            if self._AdjustGlobalCBC(arrDataGains, n) == False:
                return False
        return True

    def CheckGlobalCBC(self, valsData):
        print("CheckGlobalCBC")
        bDataValid = False
        bDataSuccess = (valsData.getGCBCCap() <= self._nGlobalCapacitanceMaxCBC)
        arrDataGains = self._arrGlobalCapGainsInitial

        while not bDataValid and bDataSuccess:
            bDataSuccess = self.SetGlobalCBC(arrDataGains, True)
            if bDataSuccess:
                bDataSuccess = self.RunTuningReport(valsData)
                if bDataSuccess:
                    arrDataChannels = []
                    bDataValid = self._CheckGlobalCBC(arrDataChannels)
                    if bDataValid == False:
                        bDataSuccess = (arrDataChannels is None)
                        if(bDataSuccess):
                            bDataSuccess = self.AdjustGlobalCBC(arrDataGains, arrDataChannels)
                    if (bDataValid and bDataSuccess):
                        bDataSuccess = self.SetGlobalCBC(arrDataGains, False)
        return True

    def ConfirmGlobalCBC(self, valsData):
        if valsData.getGCBCCap() > self._nGlobalCapacitanceMaxCBC:
            raise Exception ("CBC Global {0} Capacitance is limited to never exceed {1}.".format( "X" if self.onX else "Y", self._nGlobalCapacitanceMaxCBC))
        self.RunTuningReport(valsData)
        nDataMax = 0
        nDataMin = 0
        nDataMax, nDataMin = self.GetTuningLimits()
        data = self._reports[0]
        fReportMax = float(abs(np.amax(data)) / self._nGlobalSignalScoreAdjustment)
        fReportMin = float(abs(np.amin(data)) / self._nGlobalSignalScoreAdjustment)
        if ((fReportMax > nDataMax) or (fReportMin < nDataMin)):
            for i in range(len(data)):
                value = float(abs(data[i])) / self._nGlobalSignalScoreAdjustment
                if  value < nDataMin:
                    print("Electrode {0} = {1} is less than {2}".format(i, data[i], nDataMin * self._nGlobalSignalScoreAdjustment))
                if value > nDataMax:
                    print("Electrode {0} = {1} is more than {2}".format(i, data[i], nDataMax * self._nGlobalSignalScoreAdjustment))
            print("Range of {0} C_b within profile is too large.".format( "X" if self.onX else "Y"))
            return False
        return True

    def RunGlobalTuning(self, valsInitTuning):
        print("RunGlobalTuning")
        p = self.paraName
        valsTuning = HybridAnalogParamValues(valsInitTuning)
        #self.ValidateGlobalCBC(valsTuning)

        #PrepareGlobalCBC
        array =  self._sc[p.CBCs]
        array = [0 for element in range(len(array))]
        self._sc = update_static_config(self.handle, self._sc, {p.CBCDriverEnable: 0})
        self._sc = update_static_config(self.handle, self._sc, {self._strGlobalVarEnableScan: 0})
        self._sc = update_static_config(self.handle, self._sc, {p.CBCs: array}, True)
        self.SearchBestGlobalCBC(valsTuning)
        self.RestoreGlobalCBC()
        self.CheckGlobalCBC(valsTuning)
        self.ConfirmGlobalCBC(valsTuning)
        return valsTuning

    #phoenix
    def collect(self, count):
        self._count = count
        self.handle.reset()
        self.handle.disableReport(17)
        self.handle.enableReport(18)

        for x in range(count):
            report = self.handle.getReport()
            if report[0] == 'raw':
                report = report[1]['image']
                self._reports.append(report)
                print(json.dumps({"progress": x}))

        self.handle.disableReport(18)
        self.handle.enableReport(17)

    def DoGlobalTuning(self):
        valsBestTuning  = HybridAnalogParamValues()
        valsInitTuning = HybridAnalogParamValues()

        self.InitializeGlobalCBC(valsInitTuning)  
        valsBestTuning = self.RunGlobalTuning(valsInitTuning)
        # Save
        self.CalculateGlobalCBC(valsBestTuning)
        print("done")

    def SplitTuningResult(self, value):
        arrBits = [0] * 8
        print("value", value)
        for i in range(len(arrBits)):
            arrBits[i] = value & 0x01
            value = value >> 1
        reversed_list = arrBits[::-1]
        return arrBits

    def CalculateGlobalCBC(self, valsData):
        bitsCapGlobal = self.SplitTuningResult(valsData.getGCBCCap())
        bitsOutScale = self.SplitTuningResult(valsData.GCBCOutScale)
        bitsInScale = self.SplitTuningResult(valsData.GCBCInScale)
        fGCBC = float((200 * bitsCapGlobal[6]) + (100 * bitsCapGlobal[5]) + (50 * bitsCapGlobal[4]) + (25 * bitsCapGlobal[3]) + (12.5 * bitsCapGlobal[2]) + (6.25 * bitsCapGlobal[1]) + (3.125 * bitsCapGlobal[0]))
        fNumerGCBC = float((bitsOutScale[4] * 16) + (bitsOutScale[3] * 16) + (bitsOutScale[2] * 8) + (bitsOutScale[1] * 4) + (bitsOutScale[0] * 2)) # (nGlobalGainPerChannel * 2));  nGlobalGainPerChannel = 0
        fDenomGCBC = float((bitsInScale[4] * 16) + (bitsInScale[3] * 16) + (bitsInScale[2] * 8) + (bitsInScale[1] * 4) + (bitsInScale[0] * 2) + 2)
        fGainGCBC = fNumerGCBC / (2 * fDenomGCBC);
        fGlobalEffective = (fGCBC * fGainGCBC);

        print("fGCBC", fGCBC )
        print("valsData.GCBCOutScale", valsData.GCBCOutScale)
        print("valsData.GCBCInScale", valsData.GCBCInScale)
        print("fGlobalEffective", fGlobalEffective)
        return fGlobalEffective

    def get_report(self, clear=True):
        if(clear):
            self._reports = []
        self.handle.enableReport(REPORT_ID)
        for i in range(5):
            try:
                report = self.handle.getReport()
                if report == ('timeout', None):
                    continue
                if report[0] == 'raw':
                    report = report[1]['hybridx'] if self.onX else report[1]['hybridy']
                    self._reports.append(report)
                    print("get report", report)
                    break
            except:
                pass
            raise Exception('cannot get valid report')
        self.handle.disableReport(REPORT_ID)
    
    def beforeTuning(self):
        self.handle.disableReport(0x11)
        self.handle.disableReport(0x12)
        self.handle.disableReport(0x13)
        self._dc["noLowPower"] = 1
        self._dc["disableNoiseMitigation"] = 1
        self._dc["requestedNoiseMode"] = 5   
        self.set_dynamic_config()

        valsInitTuning = HybridAnalogParamValues()
        valsInitTuning.gcbcIdx = self.paraName.gcbcIdx
        valsInitTuning.setGCBCCap(self._sc[self.paraName.CapGlobal][ valsInitTuning.gcbcIdx])
        valsInitTuning.GCBCInScale = self._sc[self.paraName.GCBCInScale]
        self.CalculateGlobalCBC(valsInitTuning)


    def tuning(self):
        self.beforeTuning()
        self.DoGlobalTuning()

        self.onX = False
        self.paraName = HybridAnalogParamVariables(self.handle, False)
        self.DoGlobalTuning()

        return self._sc["saturationLevel"]