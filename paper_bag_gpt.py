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


import sys
from periphery import PWM
import subprocess
import time

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

def pwm_pos(chip_num, pwm_num, angle, period_ns=2400000, duty_cycle_ns=400000, step_ns=100000):
    pwm_here = PWM(0, 1)
    pwm_here.period_ns = period_ns
    pwm_here.duty_cycle_ns = duty_cycle_ns
    pwm_here.enable()
    pwm_here.duty_cycle_ns = int(duty_cycle_ns + (period_ns - duty_cycle_ns)* (int(angle)/180))
    time.sleep(0.1)
    pwm_here.close()

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

def text2speech(openai_text):
    #out_stream = speechsdk.audio.PullAudioOutputStream()

    audio_config = speechsdk.audio.AudioOutputConfig(device_name=settings.speaker_device_name)
    speech_config = speechsdk.SpeechConfig(subscription=settings.azure_sub, region=settings.azure_region)

    # Set the voice name, refer to https://aka.ms/speech/voices/neural for full list.
    speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"
    #print(speech_config.getProperty("style"))
    # https://learn.microsoft.com/en-us/javascript/api/microsoft-cognitiveservices-speech-sdk/?view=azure-node-latest
    # Creates a speech synthesizer using the default speaker as audio output.
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    
    speech_synthesizer.synthesis_started.connect(lambda evt: print("Synthesis started: {}".format(evt)))
    curr_pos = 0
    def synthesizing_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        print("At word boundary")
        #print(len(evt.result.audio_data), evt.result.audio_data[len(evt.result.audio_data)-30:len(evt.result.audio_data)-1])
        #print(int(evt.result.audio_data[len(evt.result.audio_data)]/255*90))
        nonlocal curr_pos
        pwm_pos(0, 1, curr_pos*70 + 10)
        if (not curr_pos):
            curr_pos = 1
        else:
            curr_pos = 0
        #print(evt.result.audio_data[len(evt.result.audio_data)-1])
    speech_synthesizer.synthesis_word_boundary.connect(synthesizing_cb)
   #speech_synthesizer.synthesizing.connect(synthesizing_cb)
    speech_synthesizer.synthesis_completed.connect(lambda evt: print("Synthesis completed: {}".format(evt)))


    result = speech_synthesizer.speak_text_async(openai_text).get()
activate_pwm('pwm-ao-b-6', 1)
curr_convo = []
gen_system_content(curr_convo, "insult_text.txt")
gen_assistant_content(curr_convo, "Hello stupid, why are you taking up my oxygen?")
text2speech("Hello stupid, why are you taking up my oxygen?")
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
    text2speech(response.choices[0].message.content)
#rint(current_convo)
