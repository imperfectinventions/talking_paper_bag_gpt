import random
import openai
import datetime
import time
import json
import gpiod
import sys
import azure.cognitiveservices.speech as speechsdk
import settings

button_pin = 91
chip_num = 1

from periphery import PWM
import subprocess
import numpy
import threading


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
        subprocess.getoutput(f'echo 1 > /sys/class/pwm/pwmchip{pwm_chip_num}/export')

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
    def __init__(self, chip_num, pwm_num, period_ns=2400000, duty_cycle_ns=400000, step_ns=100000):
        self.chip_num = chip_num
        self.pwm_num = pwm_num
        self.period_ns = period_ns
        self.duty_cycle_ns = duty_cycle_ns
        self.step_ns = step_ns
        self.__pwm_obj = PWM(0, 1)
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

def push_button_record():
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
        #rint('RECOGNIZING: {}'.format(evt))
       #print(finalized_text[curr_text_index])

    def recognized_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        nonlocal finalized_text
        nonlocal curr_text_index
        if len(finalized_text) < curr_text_index + 1:
            finalized_text.append('')
        finalized_text[curr_text_index] = str(evt.result.text)
        print(finalized_text[curr_text_index])
        curr_text_index += 1
       #print(curr_text_index)
        #rint(f"TEXT IS RIGHT {finalized_text}")

    def stop_cb(evt: speechsdk.SessionEventArgs):
        """callback that signals to stop continuous recognition"""
        #rint('CLOSING on {}'.format(evt))
        nonlocal done
        done = True

    # Connect callbacks to the events fired by the speech recognizer
    speech_recognizer.recognizing.connect(recognizing_cb)
    speech_recognizer.recognized.connect(recognized_cb)
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    with gpiod.Chip('gpiochip'+str(chip_num)) as chip:
      lines = chip.get_line(button_pin)
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

def gen_system_content(curr_convo, system_start_file):
    speech_guide_file = open(system_start_file, "r")
    curr_convo.append({ "role" : "system", "content" : speech_guide_file.read() })

def gen_assistant_content(curr_convo, assistant_response):
    curr_convo.append({ "role" : "assistant", "content" : assistant_response })


def gen_user_response(curr_convo, user_response):
    curr_convo.append({ "role" : "user", "content" : user_response })

def visemes2servo(*pwm_run):
    low = 10
    high = 70
    secs_per_deg = (0.1/60)
    last_setting = False
    global kill_viseme
    global viseme_event_now
    global viseme_num
    print("THESE ARE START VALUES:", kill_viseme, viseme_event_now)
    open_mouths = [1, 2, 9, 11, 20]
    closed_mouths = [0, 18, 21 ]
    oooo_mouths = [3, 7, 10, 13]
    mid_mouths = [4, 5, 8, 12, 14, 17, 19 ]
    mid_low_mouths = [6, 15, 16 ]
    last_angle = 0
    curr_angle = 0
    while not kill_viseme:
        if viseme_event_now: 
            print("We're in a viseme event...")
            if viseme_num in open_mouths:
                pwm_run[0].set_pos(high)
                curr_angle = high
            elif viseme_num in oooo_mouths or viseme_num in mid_mouths:
                pwm_run[0].set_pos(low + (high-low)//2)
                curr_angle = low + (high-low)//2
            elif viseme_num in mid_low_mouths: 
                pwm_run[0].set_pos(low + (high-low)//4)
                curr_angle = low + (high-low)//4
            else: 
                pwm_run[0].set_pos(low)
                curr_angle = low 
            time.sleep(int(abs(curr_angle-last_angle)*secs_per_deg))
            last_angle = curr_angle
            viseme_event_now = False
    return last_setting



def text2speech(pwm_obj, openai_text):
    #out_stream = speechsdk.audio.PullAudioOutputStream()
    last_time = time.time()
    last_setting = False
    def phenome_rec_audio_event(evt: speechsdk.SpeechSynthesisVisemeEventArgs):
        global viseme_event_now
        global viseme_num
        #nonlocal last_time
        print("Phenome rec")
        print(evt)
        viseme_event_now = True
        viseme_num = evt.viseme_id
       #print("visemes2servo starting...")
        #visemes2servo(evt.viseme_id, last_setting)
       #if ((time.time() - last_time) > 0):
       #    if last_setting:
       #        pwm_obj.set_pos(10)
       #       #time.sleep(0.2)
       #    else:
       #        pwm_obj.set_pos(70)
       #       #time.sleep(0.2)
       #last_setting = not last_setting
       #print(last_setting)
    def chunk_rec_audio_event(evt: speechsdk.SpeechRecognitionEventArgs):
        print("Chunk rec")
        print(evt)
    audio_complete = False
    def complete_audio_event(evt: speechsdk.SpeechRecognitionEventArgs):
        nonlocal audio_complete
        audio_complete = True
        print("Synthesis completed: {}".format(evt))
    speech_config = speechsdk.SpeechConfig(subscription=settings.azure_sub, region=settings.azure_region)

    # Set the voice name, refer to https://aka.ms/speech/voices/neural for full list.
    speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
    # https://learn.microsoft.com/en-us/javascript/api/microsoft-cognitiveservices-speech-sdk/?view=azure-node-latest
    # Creates a speech synthesizer using the default speaker as audio output    
    #stream_callback = PushAudioOutputStreamSampleCallback()
    # Creates audio output stream from the callback
    #push_stream = speechsdk.audio.PushAudioOutputStream(stream_callback)
    # Creates a speech synthesizer using push stream as audio output.
    stream_config = speechsdk.audio.AudioOutputConfig(device_name=settings.speaker_device_name)#stream=push_stream)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=stream_config)
    
    speech_synthesizer.synthesis_started.connect(lambda evt: print("Synthesis started: {}".format(evt)))
    speech_synthesizer.synthesizing.connect(chunk_rec_audio_event)
    speech_synthesizer.viseme_received.connect(phenome_rec_audio_event)
    speech_synthesizer.synthesis_completed.connect(complete_audio_event)

    result = speech_synthesizer.speak_text_async(openai_text).get()
   #while (not result._ResultFuture__resolved):
   #    print("Still waiting...")
   #    time.sleep(0.1)

activate_pwm('pwm-ao-b-6', 1)
pwm_obj = pwm_runner(0, 1)
servo_thread = threading.Thread(target=visemes2servo, args=(pwm_obj,))
servo_thread.start()
curr_convo = []
gen_system_content(curr_convo, "insult_text.txt")
gen_assistant_content(curr_convo, "Hello stupid, why are you taking up my oxygen?")
text2speech(pwm_obj, "Hello stupid, why are you taking up my oxygen?")
print("Hello stupid, why are you taking up my oxygen?")

openai.api_key = settings.openai_key 
for i in range(0, 5):
    store_human_speech = push_button_record()
    print(store_human_speech)
    gen_user_response(curr_convo, store_human_speech) 
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=curr_convo,
        temperature=1.25,
        max_tokens=1024,
    )
    gen_assistant_content(curr_convo, response.choices[0].message.content)
    print(response.choices[0].message.content)
    text2speech(pwm_obj, response.choices[0].message.content)
kill_viseme = True
servo_thread.join()
pwm_obj.close()
#rint(current_convo)
