pwm_pin_name        = "pwm-ao-b-6"
pwm_chip_num        = 0
pwm_channel_num     = 1
button_pin_num      = 91
button_chip_num     = 1
speaker_device_name = "plughw:CARD=Device,DEV=0" #find this with "aplay -L". Doesn't really matter which one. These were just the ones that worked for me with my hardware.
mic_device_name     = "sysdefault:CARD=NSCBM19" #find this with "arecord -L" Doesn't matter much. These were what worked for me with my hardware
azure_sub           = "" #the azure subscription 
azure_region        = "eastus" #the location of your speech
openai_key          = "" #openai key 
mode                = "convo" #either "reddit" or "convo". reddit will start with waiting for a button press and convo will just go into talking, no reddit story pass in
reddit_story        = "reddit_story.txt" #pass in the file name of the reddit story (takes text files). Only needed if "mode" is "reddit"
system_conf_prompt  = "system_message_templates/insulting-paper-bag.txt" #the prompt to use for the system message
system_start_talk   = "Hello, why are you wasting my time?"
speech_voice_name   = "en-US-GuyNeural"
servo_angles        = [10, 70] #the low and high angles for the servo as it talks
