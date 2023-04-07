#import tornado
from ...touchcomm.touchcomm_manager import TouchcommManager
from .hybrid_analog import HybridAnalog
from ..tutor_utils import EventQueue
from ...configuration.config_handler import ConfigHandler

class HybridAnalogRoute():
    _tutor = None

    def get(handle):
        tc = TouchcommManager().getInstance()
        print("Hello SampleModuleRoute get request")
        tutor = HybridAnalog(tc)
        return {"status": tutor.test()}

        
    def post(handle, input_data):
        task = input_data["task"]

        print("Hello SampleModuleRoute post request", task)

        return {"status": "post alive"}

 