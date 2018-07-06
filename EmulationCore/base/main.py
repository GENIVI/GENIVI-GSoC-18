# This is the main thread of the program / base of the entire system
import base.input_handler as input_handler
import base.output_handler as output_handler
from emucorebrain.data.containers.settings import SettingsContainer
import base.consts.consts as emucore_consts
from threading import Thread
import time

# Temporary content which is to be changed in the coming days
ivi_shutdown = False

# Initializes the Settings Container.
ivi_settings = SettingsContainer(emucore_consts.SETTINGS_FILEPATH)

# Initializes all the outputs(mechanisms)
output_handler.ivi_init_outputs()

# Initializes all the inputs(mechanisms)
input_handler.ivi_init_inputs(ivi_settings)
output_handler.output_via_mechanism(output_handler.default_output_mechanism, "Initialization successful. Waiting for Commands...", wait_until_completed=False, log=True)


def grab_text_input():
    global ivi_shutdown

    while not ivi_shutdown:
        user_input = input("Please type \"End\" to Finish or other Command to execute.\n")
        if user_input.lower() == "end":
            input_handler.ivi_stop_inputs(kill_permanently=True)
            output_handler.output_via_mechanism(mechanism=output_handler.default_output_mechanism, data="Stopped grabbing inputs.", wait_until_completed=True, log=False)

            ivi_shutdown = True
        else:
            splitted_command = user_input.split(" ")
            if splitted_command[0].lower() == "say":
                to_utter = ""
                for splitted_item in splitted_command[1:]:
                    to_utter += " " + splitted_item

                output_handler.output_via_mechanism(mechanism=output_handler.default_output_mechanism, data=to_utter, wait_until_completed=True, log=False)
            elif splitted_command[0].lower() == "exec_mic":
                to_proc = ""
                for splitted_item in splitted_command[1:]:
                    to_proc += " " + splitted_item

                input_handler.input_processor.process_data(input_handler.InputProcessor.PROCESS_TYPE_MICROPHONE_DATA, to_proc)


typed_input_thread = Thread(target=grab_text_input)
typed_input_thread.daemon = True
typed_input_thread.start()

while not ivi_shutdown:
    output_handler.ivi_run_outputs()
    time.sleep(0.05)
