import random
import openai
import datetime
import time
import json
import gpiod
import sys
import azure.cognitiveservices.speech as speechsdk
import settings
from periphery import PWM
import subprocess
import numpy
import threading
import tiktoken

#CHANGE THESE ONCE WORKING
viseme_event_now = False
viseme_num = 0
kill_viseme = False

#need to run this with root privilege because of ldto enable/disable
def activate_pwm(pwm_name, pwm_chip_num):
    #you can get the pwm chip numbers in ldto list and:
    # https://hub.libre.computer/t/how-to-enable-and-control-pwm-on-aml-s905x-cc/243
    already_active = False
    for i in subprocess.getoutput('ldto status').split('\n'):
        if i == pwm_name:
            print(f"PWM name: {pwm_name} already set")
            already_active = True
    if not already_active:
        print(f"PWM name: {pwm_name} setting...")
        subprocess.getoutput(f'sudo ldto enable {pwm_name}')
        subprocess.getoutput(f'sudo echo 1 > /sys/class/pwm/pwmchip{pwm_chip_num}/export')
        #set export to be writable by all so that PWM will succeed on the first time. Not fully sure why permission denied the first time, then succeeds second time. FIXME
        subprocess.getoutput(f'sudo chmod 222 /sys/class/pwm/pwmchip{pwm_chip_num}/export')

def deactivate_pwm(pwm_name):
    already_active = False
    for i in subprocess.getoutput('ldto status').split('\n'):
        if i == pwm_name:
            print(f"PWM name: {pwm_name} set")
            already_active = True
    if already_active:
        print(f"PWM name: {pwm_name} disabling...")
        subprocess.getoutput(f'sudo ldto disable {pwm_name}')
    else:
        print(f"PWM name: {pwm_name} already not active")
class pwm_runner:
    def __init__(self, chip_num, channel_num, secs_per_deg = (0.1/60), period_ns=2400000, duty_cycle_ns=400000, step_ns=100000):
        self.chip_num = chip_num
        self.channel_num = channel_num
        self.secs_per_deg = secs_per_deg
        self.period_ns = period_ns
        self.duty_cycle_ns = duty_cycle_ns
        self.step_ns = step_ns
        self.__pwm_obj = PWM(chip_num, channel_num)
        self.__pwm_obj.period_ns = period_ns
        self.__pwm_obj.duty_cycle_ns = period_ns
        self.__pwm_obj.enable()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.__pwm_obj.close()

    def set_pos(self, angle):
        self.__pwm_obj.duty_cycle_ns = int(self.duty_cycle_ns + (self.period_ns - self.duty_cycle_ns)* (int(angle)/180))

    def close(self):
        self.__pwm_obj.close()

def push_button_record(button_pin_num, button_chip_num):
    curr_text_index = 0
    finalized_text = ['']
    audio_config = speechsdk.AudioConfig(device_name=settings.mic_device_name)
    speech_config = speechsdk.SpeechConfig(subscription=settings.azure_sub, region=settings.azure_region)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    done = False

    def recognizing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        nonlocal finalized_text
        nonlocal curr_text_index
        if len(finalized_text) < curr_text_index + 1:
            finalized_text.append('')
        finalized_text[curr_text_index] = str(evt.result.text)

    def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        nonlocal finalized_text
        nonlocal curr_text_index
        if len(finalized_text) < curr_text_index + 1:
            finalized_text.append('')
        finalized_text[curr_text_index] = str(evt.result.text)
        print(finalized_text[curr_text_index])
        curr_text_index += 1

    def stop_cb(evt: speechsdk.SessionEventArgs):
        """callback that signals to stop continuous recognition"""
        nonlocal done
        done = True

    # Connect callbacks to the events fired by the speech recognizer
    speech_recognizer.recognizing.connect(recognizing_cb)
    speech_recognizer.recognized.connect(recognized_cb)
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    with gpiod.Chip('gpiochip'+str(button_chip_num)) as chip:
      lines = chip.get_line(button_pin_num)
      lines.request(consumer=sys.argv[0], type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP | gpiod.LINE_REQ_FLAG_ACTIVE_LOW)
      last_time = time.time()*1000
      operation = 'noop'
      kicked_off = False
      while True:
        curr_time = time.time()*1000
        time_diff = curr_time - last_time
        if time_diff >= 50:
          val = lines.get_value()
          if val > 0:
            operation = 'rec'
          else:
            operation = 'noop'
        curr_speech_pointer = None
        if operation == 'rec':
            if not kicked_off:
                curr_speech_pointer = speech_recognizer.start_continuous_recognition_async()
                curr_speech_pointer.get()
                kicked_off = True
        else:
            if kicked_off:
                speech_recognizer.stop_continuous_recognition_async()
                kicked_off = False
                while not done:
                    pass
                combined_text = ""
                for i in finalized_text:
                    combined_text = combined_text + " " + i 
                return combined_text

def gen_system_content(convo_dict, system_start_file):
    speech_guide_file = open(system_start_file, "r")
    file_read_data = speech_guide_file.read()
    convo_dict["curr_convo"].append({ "role" : "system", "content" : file_read_data })
    curr_enc = tiktoken.encoding_for_model(convo_dict["model"])
    convo_dict["curr_token_count"] += len(curr_enc.encode(file_read_data)) + 10 #10 is magic for now
    #convo_dict["raw_text"] += file_read_data

def gen_assistant_content(convo_dict, assistant_response):
    convo_dict["curr_convo"].append({ "role" : "assistant", "content" : assistant_response })
    convo_dict["raw_text"] += " " + assistant_response
    curr_enc = tiktoken.encoding_for_model(convo_dict["model"])
    convo_dict["curr_token_count"] += len(curr_enc.encode(assistant_response)) + 10 #10 is magic


def gen_user_response(convo_dict, user_response):
    convo_dict["curr_convo"].append({ "role" : "user", "content" : user_response })
    convo_dict["raw_text"] += " " + user_response
    curr_enc = tiktoken.encoding_for_model(convo_dict["model"])
    convo_dict["curr_token_count"] += len(curr_enc.encode(user_response)) + 5 #5 is magic for internal tokesn used

def visemes2servo(*pwm_run):
    #pass in low as 0 high as 1 and pwm_runner as 2
    low = pwm_run[0]
    high = pwm_run[1]
    secs_per_deg = (0.1/60)
    last_setting = False
    global kill_viseme
    global viseme_event_now
    global viseme_num
    open_mouths = [1, 2, 9, 11, 20]
    closed_mouths = [0, 18, 21 ]
    oooo_mouths = [3, 7, 10, 13]
    mid_mouths = [4, 5, 8, 12, 14, 17, 19 ]
    mid_low_mouths = [6, 15, 16 ]
    last_angle = 0
    curr_angle = 0
    while not kill_viseme:
        if viseme_event_now: 
            if viseme_num in open_mouths:
                pwm_run[2].set_pos(high)
                curr_angle = high
            elif viseme_num in oooo_mouths or viseme_num in mid_mouths:
                pwm_run[2].set_pos(low + (high-low)//2)
                curr_angle = low + (high-low)//2
            elif viseme_num in mid_low_mouths: 
                pwm_run[2].set_pos(low + (high-low)//4)
                curr_angle = low + (high-low)//4
            else: 
                pwm_run[2].set_pos(low)
                curr_angle = low 
            time.sleep(int(abs(curr_angle-last_angle)*secs_per_deg))
            last_angle = curr_angle
            viseme_event_now = False
    return last_setting

def gpt35_summ_gen(*thread_args):
        print("Summarizing... Hit", thread_args[0]["curr_token_count"])
        curr_enc = tiktoken.encoding_for_model(thread_args[0]["model"])
        sys_msg = "You are an expert at summarizing conversations. Your summarizations still sound like someone is recounting a memory. Your conversation summarization will be used to continue conversations"
        user_msg = "Please summarize our past conversation. Disregard system messages and your previous conversation. Just summarize what you said within 40-70 words so that we can continue our conversation. Here is the conversation:" + thread_args[0]["raw_text"]
        old_convo = thread_args[0]["curr_convo"][0].copy()
        curr_token_size = curr_enc.encode(sys_msg + " " + user_msg)
        thread_args[0]["curr_convo"] = [{ "role" : "system", "content" : sys_msg}]
        thread_args[0]["raw_text"] = ""
        gen_user_response(thread_args[0], user_msg)
        response = openai.ChatCompletion.create(
            model=thread_args[0]["model"],
            messages=thread_args[0]["curr_convo"],
            temperature=thread_args[0]["temperature"],
            max_tokens=thread_args[0]["max_tokens"] - len(curr_token_size) - 10 - 5,
        )
        gen_assistant_content(thread_args[0], response.choices[0].message.content) 
        thread_args[0]["curr_convo"] = [old_convo, thread_args[0]["curr_convo"][len(thread_args[0]["curr_convo"]) -1 ]] 
        thread_args[0]["raw_text"] = response.choices[0].message.content
        curr_enc = tiktoken.encoding_for_model(thread_args[0]["model"])
        thread_args[0]["curr_token_count"] = response.usage.total_tokens 
        return response.choices[0].message.content

def gpt35_convo_gen(convo_dict):
        curr_enc = tiktoken.encoding_for_model(convo_dict["model"])
        response = openai.ChatCompletion.create(
            model=convo_dict["model"],
            messages=convo_dict["curr_convo"],
            temperature=convo_dict["temperature"],
            max_tokens=convo_dict["max_tokens"] - convo_dict["curr_token_count"], 
        )
        print(response.choices[0].message.content)
        convo_dict["curr_token_count"] = response.usage.total_tokens
        gen_assistant_content(convo_dict, response.choices[0].message.content)
        return response.choices[0].message.content

def text2speech(pwm_obj, openai_text, voice_name="en-US-GuyNeural"):
    last_time = time.time()
    last_setting = False
    def phenome_rec_audio_event(evt: speechsdk.SpeechSynthesisVisemeEventArgs):
        global viseme_event_now
        global viseme_num
        viseme_event_now = True
        viseme_num = evt.viseme_id
    audio_complete = False
    def complete_audio_event(evt: speechsdk.SpeechRecognitionEventArgs):
        nonlocal audio_complete
        audio_complete = True
        print("Synthesis completed: {}".format(evt))
    speech_config = speechsdk.SpeechConfig(subscription=settings.azure_sub, region=settings.azure_region)

    # Set the voice name, refer to https://aka.ms/speech/voices/neural for full list.
    speech_config.speech_synthesis_voice_name = voice_name
    stream_config = speechsdk.audio.AudioOutputConfig(device_name=settings.speaker_device_name)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=stream_config)
    
    speech_synthesizer.viseme_received.connect(phenome_rec_audio_event)
    speech_synthesizer.synthesis_completed.connect(complete_audio_event)

    result = speech_synthesizer.speak_text_async(openai_text).get()


if __name__ == "__main__":
    openai.api_key = settings.openai_key 
    convo_dict = {
                    "model" : "gpt-3.5-turbo",
                    "temperature" : 1.25,
                    "max_tokens" : 3800, 
                    "curr_token_count" : 0,
                    "summarize_token_time" : 2000, 
                    "curr_convo" : [], 
                    "raw_text" : ""}
    activate_pwm(settings.pwm_pin_name, settings.pwm_chip_num)
    pwm_obj = pwm_runner(settings.pwm_chip_num, settings.pwm_channel_num)
    servo_thread = threading.Thread(target=visemes2servo, args=(settings.servo_angles[0], settings.servo_angles[1], pwm_obj,))
    servo_thread.start()
    gen_system_content(convo_dict, settings.system_conf_prompt)
    gen_assistant_content(convo_dict, settings.system_start_talk)
    text2speech(pwm_obj, settings.system_start_talk, voice_name=settings.speech_voice_name)
    if settings.mode == "reddit":
        reddit_file = open(settings.reddit_story, 'r+')
        gen_user_response(convo_dict, "I need your moral judgement on this Reddit story: " + reddit_file.read())
        reddit_file.close()
        curr_msg = gpt35_convo_gen(convo_dict)
        print("I've got this juicy goss...")
        with gpiod.Chip('gpiochip'+str(settings.button_chip_num)) as chip:
            lines = chip.get_line(settings.button_pin_num)
            lines.request(consumer=sys.argv[0], type=gpiod.LINE_REQ_DIR_IN, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP | gpiod.LINE_REQ_FLAG_ACTIVE_LOW)
            while lines.get_value() == 0:
                pass
            text2speech(pwm_obj, curr_msg, voice_name=settings.speech_voice_name)
        print("Done first tts gen")
    print(settings.system_start_talk)

    
    summ_thread = None
    new_convo_dict = None
    count_since_thread_ran = 1
    tokens_since_thread_ran = 0
    while True:
        curr_thread_count = convo_dict["curr_token_count"]
        if not summ_thread and convo_dict["curr_token_count"] >= convo_dict["summarize_token_time"]:
            count_since_thread_ran = 1
            tokens_since_thread_ran = 0
            new_convo_dict = convo_dict.copy()
            summ_thread = threading.Thread(target=gpt35_summ_gen, args=(new_convo_dict,))
            summ_thread.start()
        store_human_speech = push_button_record(settings.button_pin_num, settings.button_chip_num)
        print(store_human_speech)
        gen_user_response(convo_dict, store_human_speech) 
        curr_msg = gpt35_convo_gen(convo_dict)
        text2speech(pwm_obj, curr_msg, voice_name=settings.speech_voice_name)
        if summ_thread and not summ_thread.is_alive():
           summ_thread = None
           convo_appends = []
           for i in range(len(convo_dict["curr_convo"]) - count_since_thread_ran*2 - 1, len(convo_dict["curr_convo"])-1):
                convo_appends.append(convo_dict["curr_convo"][i])
           new_convo_dict["curr_convo"] + convo_appends
           count_since_thread_ran = 1
           convo_dict = new_convo_dict
        else:
            tokens_since_thread_ran += convo_dict["curr_token_count"] - curr_thread_count
            count_since_thread_ran += 1
        last_token_count = convo_dict["curr_token_count"]
            
    kill_viseme = True
    servo_thread.join()
    pwm_obj.close()
    deactivate_pwm()
