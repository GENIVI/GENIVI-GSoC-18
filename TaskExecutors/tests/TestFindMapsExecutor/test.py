import time
from emucorebrain.data.carriers.ins_mechanism import InputMechanismCarrier
from emucorebrain.data.carriers.outs_mechanism import OutputMechanismCarrier
from emucorebrain.data.carriers.string import StringCarrier
from emucorebrain.data.containers.settings import SettingsContainer
from emucorebrain.io.mechanisms.ins_mechanism import Grabber, GrabberController
from FindMapsExecutor.FindMapsExecutor import FindMapsExecutor
from tests.io.ins_mechanisms import TerminalInputMechanism
from tests.io.outs_mechanisms import TerminalOutputMechanism
import emucorebrain.keywords.task_executor as keywords_task_executor

find_maps_executor: FindMapsExecutor = FindMapsExecutor()
ins_terminal_mechanism: TerminalInputMechanism = TerminalInputMechanism()
outs_terminal_mechanism: TerminalOutputMechanism = TerminalOutputMechanism()
ivi_settings = SettingsContainer("../../../EmulationCore/settings.json")

outs_terminal_mechanism.write_data("Please type in the sentence with location. Eg: \"Find me the city of New York\"\nEnter: \"@end_kill\" to terminate testing.")
def process_sentence(sentence, *disc_args):
    ins_terminal_mechanism.get_grabber_controller().pop_out_grabber(GrabberController.MAX_PRIORITY_INDEX)
    args = {
        keywords_task_executor.ARG_SPEECH_TEXT_DATA: StringCarrier(sentence),
        keywords_task_executor.ARG_SETTINGS_CONTAINER: ivi_settings,
        keywords_task_executor.ARG_INS_MECHANISMS_CARRIERS: {
            keywords_task_executor.ARG_INS_MECHANISMS_MECHANISM_DEFAULT: InputMechanismCarrier(ins_terminal_mechanism),
        },
        keywords_task_executor.ARG_OUTS_MECHANISMS_CARRIERS: {
            keywords_task_executor.ARG_OUTS_MECHANISMS_MECHANISM_DEFAULT: OutputMechanismCarrier(outs_terminal_mechanism),
        }
    }
    find_maps_executor.run(args)
ins_terminal_mechanism.get_grabber_controller().pop_in_grabber(Grabber(on_exec=process_sentence), GrabberController.MAX_PRIORITY_INDEX)

# Keeps the script alive and running, just to wait for other processes to happen.
while ins_terminal_mechanism.is_mechanism_alive():
    time.sleep(0.05)
