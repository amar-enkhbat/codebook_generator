import time
import numpy as np
from psychopy import sound, tools, prefs
from utils import perf_sleep
from button_box import ButtonBoxController
from pylsl import StreamInfo, StreamOutlet, cf_string

class AudioController:
    def __init__(self, audio_path: str, button_box: ButtonBoxController):
        self.audio_path = audio_path
        self.button_box = button_box
        self.playback_interval = 3 # Play audio every 3 seconds
        self.key_press_pause_duration = (3, 5) # Pause between 3 to 4 seconds after key press
        self.key_press_pause_duration = (0, 0.5) # Pause between 3 to 4 seconds after key press

        # Init marker stream
        info = StreamInfo(name='AudioCueMarkerStream', type='Marker', channel_count=1, channel_format=cf_string, nominal_srate=0, source_id='audio_marker_stream_id')
        self.marker_outlet = StreamOutlet(info)

    def random_wait(self):
        """wait 3 to 4 seconds or values defined in self.key_press_pause_duration"""
        val = round(np.random.uniform(self.key_press_pause_duration[0], self.key_press_pause_duration[1]), 2)
        perf_sleep(val)

    def cue_audio(self, ref_obj: str, target_obj: str, mode: str):
        """Cue audio before a trial. First cue cannot be cancelled."""
        audio = sound.Sound(f'{self.audio_path}/{mode}_{ref_obj}2{target_obj}.mp3')
        duration = audio.getDuration()

        # Play first cue. It cannot be cancelled.
        self.marker_outlet.push_sample(['play'])
        audio.play()
        start_time = time.perf_counter()
        perf_sleep(duration)
        self.marker_outlet.push_sample(['stop'])
        _ = self.button_box.read() # Flush previous key presses
        
        # 3-second pause between playbacks, checking for key press
        end_time = time.perf_counter() + self.playback_interval
        while time.perf_counter() < end_time:
            x = self.button_box.read()
            if len(x):
                button_box.marker_outlet.push_sample([1])
                self.marker_outlet.push_sample(['button_press'])
                self.random_wait()
                return x
            else:
                continue

        # Contiue repeating audio cue
        while True:
            # Play the audio until key press
            audio.play()
            start_time = time.perf_counter()
            self.marker_outlet.push_sample(['play'])
            
            while time.perf_counter() - start_time < duration:
                x = self.button_box.read()
                if len(x):
                    button_box.marker_outlet.push_sample([1])
                    audio.stop()
                    self.marker_outlet.push_sample(['button_press'])
                    self.random_wait()
                    return x
                else:
                    continue
            self.marker_outlet.push_sample(['stop'])

            # 3-second pause between playbacks, still checking for input
            end_time = time.perf_counter() + 3
            while time.perf_counter() < end_time:
                x = self.button_box.read()
                if len(x):
                    button_box.marker_outlet.push_sample([1])
                    self.marker_outlet.push_sample(['button_press'])
                    self.random_wait()
                    return x
                else:
                    continue

    def cue_audio_single(self, ref_obj: str, target_obj: str, mode: str):
        """Cue audio before a trial"""
        audio = sound.Sound(f'{self.audio_path}/{mode}_{ref_obj}2{target_obj}.mp3')

        audio.play()
        start_time = time.perf_counter()
        duration = audio.getDuration() + 2
        perf_sleep(duration)
        
    def get_available_audio_devices(self):
        return list(tools.systemtools.getAudioDevices().keys())
    
    def select_speakers(self):
        # Set speakers
        prefs.hardware['audioLib'] = ['PTB'] if ['PTB'] in prefs.hardware['audioLib'] else prefs.hardware['audioLib'] # Most time accurate library according to psychopy docs
        


        while True:
            print("Available audio devices:\nFOR EXPERIMENT SELECT 'OUT 3-4 (BEHRINGER X-AIR)'\n")
            audio_devices = self.get_available_audio_devices()
            for i, device_name in enumerate(audio_devices):
                print(i, device_name)
            audio_device_id = int(input(f'Select audio device: {list(range(len(audio_devices)))}\n'))
            audio_device = audio_devices[audio_device_id]
            print(audio_device)
            prefs.hardware['audioDevice'] = audio_device
            self.cue_audio_single('can', 'candle', 'scene')
            if input('Do the speakers work? y/n\n') == 'y':
                break



if __name__ == '__main__':
    button_box = ButtonBoxController(timeout=0.1)
    audio = AudioController('./tts/queries/psychopy_slowed', button_box=button_box)
    # audio.select_speakers()
    # default_audio_devices = [
    #     'OUT 3-4 (BEHRINGER X-AIR)', # For lab PC
    #     'Speakers (Realtek(R) Audio)', # For Windows
    #     'Speakers (High Definition Audio Device)' # For my mac
    # ]
    prefs.hardware['audioDevice'] = 'OUT 3-4 (BEHRINGER X-AIR)'
    # while True:
    x = audio.cue_audio('can', 'candle', 'scene')
    print(x)