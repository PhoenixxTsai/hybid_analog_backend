
from ...touchcomm.touchcomm_manager import TouchcommManager
from .hybrid_analog import HybridAnalog
from ..tutor_utils import EventQueue
from ...configuration.config_handler import ConfigHandler
from ..tutor_thread import TutorThread

class HybridAnalogRoute():
    _tutor = None

    def get(handle):
        tc = TouchcommManager().getInstance()
        print("Hello SampleModuleRoute get request")
        #tutor = HybridAnalog(tc)
        #return {"status": tutor.test()}
        return HybridAnalogRoute.currentSetting()
        
    def post(handle, input_data):
        task = input_data["task"]

        if task == None:
            raise Exception('Unsupport input parameters: ', input_data)

        if task == "run":
            frame_count = input_data["settings"]["frameCount"]
            return HybridAnalogRoute.run(frame_count)
        elif task == "getSetting":
            return HybridAnalogRoute.currentSetting()
        elif task == "terminate":
            TutorThread.terminate()
            return {"state": "done"}
        else:
            raise Exception('Unsupport parameters: ', input_data)

    def run(params):
        tc = TouchcommManager().getInstance()
        h = HybridAnalog(tc)
        ret = h.run()
        return {"x":ret[0], "y":ret[1]}

    def currentSetting():
        print("hello")
        tc = TouchcommManager().getInstance()
        h = HybridAnalog(tc)
        ret = h.beforeTuning()
        print(ret[0],ret[1])
        return {"x":ret[0], "y":ret[1]}
