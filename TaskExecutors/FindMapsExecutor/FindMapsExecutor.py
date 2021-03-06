from emucorebrain.data.abstracts.TaskExecutor import TaskExecutor
import emucorebrain.keywords.task_executor as keywords_task_executor
from emucorebrain.data.carriers.ins_mechanism import InputMechanismCarrier
from emucorebrain.data.carriers.outs_mechanism import OutputMechanismCarrier
from emucorebrain.data.carriers.string import StringCarrier
from emucorebrain.data.containers.lockers import LockersContainer
from emucorebrain.data.containers.settings import SettingsContainer
from emucorebrain.data.models.lockers import LockerTypes
from emucorebrain.io.mechanisms.ins_mechanism import InputMechanism
from emucorebrain.io.mechanisms.outs_mechanism import OutputMechanism
from emucorebrain.io.mechanisms.ins_mechanism import Grabber
from emucorebrain.io.mechanisms.ins_mechanism import GrabberController
import FindMapsExecutor.config.locationdb as config_location_db
import FindMapsExecutor.consts.locationdb as consts_location_db
from FindMapsExecutor.db.bigdata import BigDataFile
from FindMapsExecutor.db.predictor import Predictor
from FindMapsExecutor.db.locationdb import GeoLocation, LocationDB
import inflect
import nltk
import operator
import FindMapsExecutor.consts.number_utils as consts_number_utils
from word2number import w2n
import speech_recognition as SR
import FindMapsExecutor.config.ner as config_ner
from nltk.tokenize import word_tokenize
import dependencies.entity_recognition.helpers.taggers as helper_ner_tagger
import dependencies.entity_recognition.consts.taggers as consts_taggers
import FindMapsExecutor.config.negative_locations_db as config_negative_locations_db
from FindMapsExecutor.db.preprocessors import LocationPreProcessor
import FindMapsExecutor.consts.settings as consts_settings
from FindMapsExecutor.helpers.negative_locations import NegativeLocationDB

# Temporarily used to open the Google Maps with the latitudes and longitudes
import webbrowser


class FindMapsExecutor(TaskExecutor):

    CONTAINER_KEY_INPUT_MICROPHONE = "ins_mechanism_microphone"

    def __init__(self):
        pass

    # Executes the negative run method of FindMapsExecutor.
    def run_negative(self, args):
        data: StringCarrier = args[keywords_task_executor.ARG_SPEECH_TEXT_DATA]
        ivi_settings: SettingsContainer = args[keywords_task_executor.ARG_SETTINGS_CONTAINER]
        ivi_outs_mechanisms_carriers = args[keywords_task_executor.ARG_OUTS_MECHANISMS_CARRIERS]
        ivi_outs_mechanism_carrier_default: OutputMechanismCarrier = ivi_outs_mechanisms_carriers[keywords_task_executor.ARG_OUTS_MECHANISMS_MECHANISM_DEFAULT]
        ivi_outs_mechanism_default: OutputMechanism = ivi_outs_mechanism_carrier_default.get_data()
        tasks_namespaces_folderpath = ivi_settings.get_setting(consts_settings.KEY_TASKS_NAMESPACES_FOLDERPATH)

        ivi_outs_mechanism_default.write_data("Please wait while we process the locations.", wait_until_completed=True)

        negative_location_db = NegativeLocationDB(tasks_namespaces_folderpath + "/FindMapsExecutor/" + config_negative_locations_db.DB_FILE_PATH)

        tokenized_data = word_tokenize(data.get_data())
        check_classes = [consts_taggers.TAG_CLASS_ORGANIZATION, consts_taggers.TAG_CLASS_LOCATION]

        location_name_to_process = None

        classified_c3 = helper_ner_tagger.get_classified_by(tokenized_data, tasks_namespaces_folderpath + "/" + config_ner.PATH_NER_CLASSIFIER_C3, tasks_namespaces_folderpath + "/" + config_ner.PATH_NER_JAR)
        # Used nested ifs to reduce the time taken by classifications.
        if helper_ner_tagger.at_least_one_class_visible_in(check_classes, classified_c3):
            location_name_to_process = helper_ner_tagger.get_location_name_to_process(check_classes, classified_c3)
        else:
            classified_c4 = helper_ner_tagger.get_classified_by(tokenized_data, tasks_namespaces_folderpath + "/" + config_ner.PATH_NER_CLASSIFIER_C4, tasks_namespaces_folderpath + "/" + config_ner.PATH_NER_JAR)
            if helper_ner_tagger.at_least_one_class_visible_in(check_classes, classified_c4):
                location_name_to_process = helper_ner_tagger.get_location_name_to_process(check_classes, classified_c4)
            else:
                classified_c7 = helper_ner_tagger.get_classified_by(tokenized_data, tasks_namespaces_folderpath + "/" + config_ner.PATH_NER_CLASSIFIER_C7, tasks_namespaces_folderpath + "/" + config_ner.PATH_NER_JAR)
                if helper_ner_tagger.at_least_one_class_visible_in(check_classes, classified_c7):
                    location_name_to_process = helper_ner_tagger.get_location_name_to_process(check_classes, classified_c7)

        if location_name_to_process is not None:
            location_name_pre_preprocessor = LocationPreProcessor([location_name_to_process])
            location_name_pre_preprocessor.pre_process()
            pre_processed_location_name = location_name_pre_preprocessor.get_locations()[0]

            db_location_filepath = ivi_settings.get_setting(consts_location_db.SETTING_LOCATION_DB_NAMES_FILEPATH_KEY)
            db_mapper_filepath = ivi_settings.get_setting(consts_location_db.SETTING_LOCATION_DB_MAPPERS_FILEPATH_KEY)
            location_db = LocationDB(db_location_filepath, LocationDB.FLAG_DB_RDONLY)
            mapper_db = LocationDB(db_mapper_filepath, LocationDB.FLAG_DB_RDONLY)

            real_location_for_location_name = location_db.get(pre_processed_location_name).split(BigDataFile.TEXT_FILE_DATA_SUB_SEPARATOR)[0]
            str_geo_location_for_real_location = mapper_db.get(real_location_for_location_name)

            if str_geo_location_for_real_location is not None:
                kwargs = {
                    GeoLocation.ARG_LOCATION_NAME: real_location_for_location_name,
                    GeoLocation.ARG_PARSE_STRING_GEOLOCATION: str_geo_location_for_real_location
                }
            else:
                kwargs = {
                    GeoLocation.ARG_LOCATION_NAME: real_location_for_location_name,
                    GeoLocation.ARG_LATITUDE: None,
                    GeoLocation.ARG_LONGITUDE: None
                }

            geo_location = GeoLocation(**kwargs)
            negative_location_db.add_location(geo_location)
            ivi_outs_mechanism_default.write_data("OK. I will remember that.", wait_until_completed=True)
        else:
            ivi_outs_mechanism_default.write_data("I didn't hear a location in your speech to remember. Please try again.")

    # Method to open any type of string query which Google Maps supports in web browser.
    @staticmethod
    def _open_location_in_browser(location : str):
        gmaps_url = "https://maps.google.com/?q=" + location
        webbrowser.open(gmaps_url)

    # Method to open GeoLocation instances in the web browser.
    @staticmethod
    def _open_geo_location_in_browser(geo_location : GeoLocation):
        geo_latitude = geo_location.get_latitude()
        geo_longitude = geo_location.get_longitude()

        if geo_latitude is not None and geo_longitude is not None:
            FindMapsExecutor._open_location_in_browser(geo_latitude + "," + geo_longitude)
            return True
        else:
            return False

    # Handles the opening process of a geo location through the web browser completely together with the output.
    def _manage_location_and_open_in_browser(self, geo_location : GeoLocation, ivi_outs_mechanism_default : OutputMechanism):
        location_name = geo_location.get_location_name()

        geo_data_open_state = self._open_geo_location_in_browser(geo_location)
        if not geo_data_open_state:
            ivi_outs_mechanism_default.write_data("We could not find the geological data for the location you've requested. We'll try with the location name.", wait_until_completed=True)
            self._open_location_in_browser(location_name)

    # Used to obtain a progressive list of chunks of word-sets for the given phrase.
    @staticmethod
    def _get_progressive_word_combinations(phrase):
        words_in_phrase = nltk.tokenize.word_tokenize(phrase.lower())
        word_combinations = []
        for word_begin_index in range(len(words_in_phrase)):
            for word_end_index in range(word_begin_index + 1, len(words_in_phrase) + 1):
                word_set = words_in_phrase[word_begin_index:word_end_index]
                sub_phrase = " ".join(word for word in word_set)
                word_combinations.append(sub_phrase)

        return word_combinations

    # Checks whether the sub phrases built from the original phrase are really ordinal numbers or numbers in text form.
    # Returns the number meant by the phrase or None if there isn't any recognizable number in the phrase.
    def _extract_index_using_mode(self, mode : int, phrase : str):
        scores_for_numbers = {}

        combinations_in_phrase = self._get_progressive_word_combinations(phrase.lower())
        for sub_phrase in combinations_in_phrase:
            number = None
            if mode == consts_number_utils.INDEX_EXTRACTION_MODE_ORDINALS:
                if sub_phrase in consts_number_utils.ORDINALS_TO_NUMBERS:
                    number = consts_number_utils.ORDINALS_TO_NUMBERS[sub_phrase]
                else:
                    number = None
            elif mode == consts_number_utils.INDEX_EXTRACTION_MODE_NUMBERS_IN_WORDS:
                try:
                    number = w2n.word_to_num(sub_phrase)

                except:
                    number = None
            elif mode == consts_number_utils.INDEX_EXTRACTION_MODE_NUMBERS_AS_INTEGERS:
                numbers_in_phrase = [int(token) for token in phrase.split() if token.isdigit()]
                if len(numbers_in_phrase) == 1:
                    number = numbers_in_phrase[0]
                else:
                    number = None

            if number is not None:
                score = len(sub_phrase)
                scores_for_numbers[number] = score

        if len(scores_for_numbers) > 0:
            return max(scores_for_numbers.items(), key=operator.itemgetter(1))[0]
        else:
            return None

    # Extracts the index of a location out of the spoken
    # Checks whether a number is included in the phrase as an ordinal or a number in words.
    # If ordinal check returns None, i.e. No ordinal included, checks for the words(of number).
    # Returns the number meant in the phrase or None if there weren't any.
    def _extract_index_from_phrase(self, phrase):
        number_inc_as_ordinal = self._extract_index_using_mode(mode=consts_number_utils.INDEX_EXTRACTION_MODE_ORDINALS, phrase=phrase)
        if number_inc_as_ordinal is not None:
            return number_inc_as_ordinal
        else:
            number_inc_as_word = self._extract_index_using_mode(mode=consts_number_utils.INDEX_EXTRACTION_MODE_NUMBERS_IN_WORDS, phrase=phrase)
            if number_inc_as_word is not None:
                return number_inc_as_word
            else:
                return self._extract_index_using_mode(mode=consts_number_utils.INDEX_EXTRACTION_MODE_NUMBERS_AS_INTEGERS, phrase=phrase)

    # Executes the FindMapsExecutor.
    # The main method executed when prediction is directed to this class.
    def run(self, args):
        data: StringCarrier = args[keywords_task_executor.ARG_SPEECH_TEXT_DATA]
        ivi_settings: SettingsContainer = args[keywords_task_executor.ARG_SETTINGS_CONTAINER]
        ivi_lockers: LockersContainer = args[keywords_task_executor.ARG_LOCKERS_CONTAINER]
        ivi_ins_mechanisms_carriers = args[keywords_task_executor.ARG_INS_MECHANISMS_CARRIERS]
        ivi_ins_mechanism_carrier_default: InputMechanismCarrier = ivi_ins_mechanisms_carriers[keywords_task_executor.ARG_INS_MECHANISMS_MECHANISM_DEFAULT]
        ivi_ins_mechanism_default: InputMechanism = ivi_ins_mechanism_carrier_default.get_data()
        ivi_outs_mechanisms_carriers = args[keywords_task_executor.ARG_OUTS_MECHANISMS_CARRIERS]
        ivi_outs_mechanism_carrier_default: OutputMechanismCarrier = ivi_outs_mechanisms_carriers[keywords_task_executor.ARG_OUTS_MECHANISMS_MECHANISM_DEFAULT]
        ivi_outs_mechanism_default: OutputMechanism = ivi_outs_mechanism_carrier_default.get_data()
        tasks_namespaces_folderpath = ivi_settings.get_setting(consts_settings.KEY_TASKS_NAMESPACES_FOLDERPATH)

        te_locker_id_ins_mechanisms = ivi_lockers.add_locker(LockerTypes.INPUT_MECHANISMS)
        te_locker_id_outs_mechanisms = ivi_lockers.add_locker(LockerTypes.OUTPUT_MECHANISMS)

        ivi_outs_mechanism_default.write_data("Please wait while we look for the location for you.", wait_until_completed=True)

        # Temporary code used for demonstrations.
        # if "favorite place" in data.get_data().lower() or "favorite places" in data.get_data().lower() or "favourite place" in data.get_data().lower() or "favourite places" in data.get_data().lower():
        #     from FindMapsExecutor.temp.preferredgeolocations import PreferredGeoLocationsModel
        #     from haversine import haversine, Unit
        #     import reverse_geocoder as rgc
        #
        #     preferred_locations_model_path = "D:/Dev/GENIVI/Projects/Processes/commons/storage/universalmodel/prefgeolocs.json"
        #     preferred_locations_model: PreferredGeoLocationsModel = PreferredGeoLocationsModel(preferred_locations_model_path)
        #     preferred_locations = preferred_locations_model.get_all_locations()
        #
        #     # Current location is hardcoded here for easy demonstration as support for obtaining current
        #     # geo-location in a task executor is not added yet.
        #     current_location = {
        #         "latitude": 25.761681,
        #         "longitude": -80.191788
        #     }
        #     current_location_tuple = (current_location["latitude"], current_location["longitude"])
        #
        #     least_distance = -1
        #     location_least_distance = None
        #     for preferred_location in preferred_locations:
        #         preferred_location_tuple = (preferred_location["latitude"], preferred_location["longitude"])
        #         distance_gap = abs(haversine(current_location_tuple, preferred_location_tuple, unit=Unit.KILOMETERS))
        #         if distance_gap <= least_distance or least_distance == -1:
        #             least_distance = distance_gap
        #             location_least_distance = preferred_location
        #
        #     # Reverse Geo-Coding for location_least_distance
        #     location_least_distance_tuple = (location_least_distance["latitude"], location_least_distance["latitude"])
        #     result_reverse_geo_code = rgc.search(location_least_distance_tuple, mode=1)[0]
        #     location_least_distance_name = result_reverse_geo_code["name"]
        #
        #     ivi_outs_mechanism_default.write_data("Your favorite location " + location_least_distance_name + " is " + str(round(least_distance, 2)) + " kilometers away from here.", wait_until_completed=True)
        #
        #     ivi_lockers.remove_locker(te_locker_id_ins_mechanisms)
        #     ivi_lockers.remove_locker(te_locker_id_outs_mechanisms)
        #
        #     return

        db_location_filepath = ivi_settings.get_setting(consts_location_db.SETTING_LOCATION_DB_NAMES_FILEPATH_KEY)
        db_mapper_filepath = ivi_settings.get_setting(consts_location_db.SETTING_LOCATION_DB_MAPPERS_FILEPATH_KEY)
        predictor = Predictor(db_location_filepath, db_mapper_filepath)

        negative_location_db = NegativeLocationDB(tasks_namespaces_folderpath + "/FindMapsExecutor/" + config_negative_locations_db.DB_FILE_PATH)

        accept_min_threshold = ivi_settings.get_setting(consts_location_db.SETTING_LOCATION_ACCEPTANCE_MIN_THRESHOLD)
        geo_locations_and_scores = predictor.get_geo_locations_and_norm_frequencies_for_phrase(data.get_data())
        geo_locations_and_scores = {k: v for k, v in geo_locations_and_scores.items() if v > float(accept_min_threshold)}

        # Checks whether at least one suspected location is found.
        if len(geo_locations_and_scores) > 0:
            # If there are more than one geo location in the returned location set, we try first to filter out the rest
            # with the location having the maximum score based on its score difference with the "next-maximum" just
            # after it.
            # If there is only one location we would open it up in the web browser.
            if len(geo_locations_and_scores) > 1:
                # Sorts the geo locations in descending order by their scores.
                # The dictionary would be converted to a list of 2-tuple where the first item would be the key while the
                # the value is placed in the second index.
                sorted_geo_locations_and_scores = sorted(geo_locations_and_scores.items(), key=lambda kv: kv[1], reverse=True)

                # Checks whether there is a halfway difference between the maximum and the next geo location in their
                # scores.
                maximum_score_location_obviousness = sorted_geo_locations_and_scores[0][1] - sorted_geo_locations_and_scores[1][1]
                if maximum_score_location_obviousness > config_location_db.CUTOFF_SCORE_DIFFERENCE_FOR_MULTIPLE_LOCATIONS:
                    # Since the gap is so high, it is obvious that the first location is the only location meant by
                    # the user.
                    maximum_score_geo_location: GeoLocation = sorted_geo_locations_and_scores[0][0]
                    self._manage_location_and_open_in_browser(maximum_score_geo_location, ivi_outs_mechanism_default)
                else:
                    # The gap between the scores of first and the adjacent location were not so huge, so we continue
                    # to provide locations progressively along the list until such a large gap is found.

                    ivi_outs_mechanism_default.write_data("We have several locations identified. Let me list them down for you.", wait_until_completed=True)

                    word_convert_engine = inflect.engine()
                    broken_out = False
                    for index_geo_location in range(len(sorted_geo_locations_and_scores) - 1):
                        high_score_geo_location_tuple = sorted_geo_locations_and_scores[index_geo_location]
                        high_score_geo_location, high_score_geo_location_score = high_score_geo_location_tuple[0], high_score_geo_location_tuple[1]
                        low_score_geo_location_tuple = sorted_geo_locations_and_scores[index_geo_location + 1]
                        low_score_geo_location, low_score_geo_location_score = low_score_geo_location_tuple[0], low_score_geo_location_tuple[1]

                        geo_location_index_in_words = word_convert_engine.number_to_words(word_convert_engine.ordinal(index_geo_location + 1))
                        location_name = high_score_geo_location.get_location_name()
                        ivi_outs_mechanism_default.write_data(geo_location_index_in_words + " one is " + location_name, wait_until_completed=True)

                        # Try to find out whether there is a huge gap between this location and the next one.
                        # If the gap is large, breaks out the loop WITHOUT providing other locations as recognized ones.
                        high_low_score_difference = high_score_geo_location_score - low_score_geo_location_score
                        if high_low_score_difference > config_location_db.CUTOFF_SCORE_DIFFERENCE_FOR_MULTIPLE_LOCATIONS:
                            broken_out = True
                            break

                    # The last element of the list should be spoken out if not the loop was exited by a break (because
                    # a break indicates that a huge score difference was found.
                    if not broken_out:
                        last_geo_location_index_in_words = word_convert_engine.number_to_words(word_convert_engine.ordinal(len(sorted_geo_locations_and_scores)))
                        last_geo_location_and_score = sorted_geo_locations_and_scores[len(sorted_geo_locations_and_scores) - 1]
                        last_geo_location = last_geo_location_and_score[0]
                        last_geo_location_location_name = last_geo_location.get_location_name()
                        ivi_outs_mechanism_default.write_data(last_geo_location_index_in_words + " one is " + last_geo_location_location_name, wait_until_completed=True)

                    ivi_outs_mechanism_default.write_data("Which one did you mean?", wait_until_completed=True)

                    # Define a Grabber to get the inputs focused onto FindMapsExecutor until the user responds.
                    ins_default_mechanism_grabber_controller: GrabberController = ivi_ins_mechanism_default.get_grabber_controller()

                    locker_id_ins_mechanisms = ivi_lockers.add_locker(LockerTypes.INPUT_MECHANISMS)
                    locker_id_outs_mechanisms = ivi_lockers.add_locker(LockerTypes.OUTPUT_MECHANISMS)

                    def ins_default_mechanism_grab_next_inputs(*args, _locker_id_ins_mechanisms=locker_id_ins_mechanisms, _locker_id_outs_mechanisms=locker_id_outs_mechanisms):
                        if ivi_ins_mechanism_default.CONTAINER_KEY == FindMapsExecutor.CONTAINER_KEY_INPUT_MICROPHONE:
                            # If Default Input Mechanism is InputMicrophone
                            heard_text = args[0]
                            exception = args[1]

                            if exception is None:
                                print("Read from Microphone: " + heard_text)
                                # Check for index then cancel commands.
                                # If any of the above ones are not found, say that the command is unrecognized.
                                number_in_phrase = self._extract_index_from_phrase(heard_text)
                                if number_in_phrase is not None:
                                    # TODO: Find a way to check whether the phrase is a positive expression before
                                    # moving into conclusions. If a phrase like "not the first one" is uttered, this
                                    # method would identify the meant index as the first one. Find a remedy for this
                                    # by having something like sentimental analysis(not the exact idea of it though)
                                    index_for_number_in_phrase = number_in_phrase - 1
                                    geo_location_to_open: GeoLocation = sorted_geo_locations_and_scores[index_for_number_in_phrase][0]

                                    if negative_location_db.location_exists(geo_location_to_open):
                                        ivi_outs_mechanism_default.write_data("This location has been saved as a location that you don't want to visit. However I'll open that up.", wait_until_completed=True)
                                    else:
                                        ivi_outs_mechanism_default.write_data("Sure! I will open that up for you.", wait_until_completed=True)

                                    self._manage_location_and_open_in_browser(geo_location=geo_location_to_open, ivi_outs_mechanism_default=ivi_outs_mechanism_default)

                                    ins_default_mechanism_grabber_controller.pop_out_grabber(GrabberController.MAX_PRIORITY_INDEX)
                                    ivi_lockers.remove_locker(_locker_id_ins_mechanisms)
                                    ivi_lockers.remove_locker(_locker_id_outs_mechanisms)
                                else:
                                    # TODO: Extract the number or "Cancel" from the heard speech if there is no exception.
                                    # If cancel was heard pop out the Grabber.

                                    ivi_outs_mechanism_default.write_data("I'm extremely sorry. I cannot recognize which one to be opened. Can you please try saying again?", wait_until_completed=True)
                            else:
                                if exception == SR.UnknownValueError:
                                    pass
                                elif exception == SR.RequestError:
                                    ivi_outs_mechanism_default.write_data("Google Cloud API Error. Could not interpret your speech.", wait_until_completed=True)

                                ivi_lockers.remove_locker(_locker_id_ins_mechanisms)
                                ivi_lockers.remove_locker(_locker_id_outs_mechanisms)

                        # For any other InputMechanisms

                    ins_default_mechanism_grabber_controller.pop_in_grabber(Grabber(ins_default_mechanism_grab_next_inputs), GrabberController.MAX_PRIORITY_INDEX)
            else:
                only_geo_location: GeoLocation = list(geo_locations_and_scores.keys())[0]
                if negative_location_db.location_exists(only_geo_location):
                    ivi_outs_mechanism_default.write_data("This location has been saved as a location that you don't want to visit. However I'll open that up.", wait_until_completed=True)

                self._manage_location_and_open_in_browser(only_geo_location, ivi_outs_mechanism_default)
        else:
            ivi_outs_mechanism_default.write_data("We could not find such a place. We're extremely sorry.", wait_until_completed=True)

        ivi_lockers.remove_locker(te_locker_id_ins_mechanisms)
        ivi_lockers.remove_locker(te_locker_id_outs_mechanisms)
