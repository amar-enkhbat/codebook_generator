import time
import numpy as np
from psychopy import sound, tools, prefs
from utils import perf_sleep
from button_box import ButtonBoxController


class AudioController:
    def __init__(self, audio_path: str, button_box: ButtonBoxController, marker_outlet):
        self.audio_path = audio_path
        self.button_box = button_box
        self.marker_outlet = marker_outlet

    def cue_audio(self, ref_obj: str, target_obj: str, mode: str):
        """Cue audio before a trial. First cue cannot be cancelled."""
        audio = sound.Sound(f'{self.audio_path}/{mode}_{ref_obj}2{target_obj}.mp3')
        audio.play()
        start_time = time.perf_counter()
        duration = audio.getDuration()
        perf_sleep(duration)
        
        # 3-second pause between playbacks, checking for input
        end_time = time.perf_counter() + 3
        while time.perf_counter() < end_time:
            try:
                x = self.button_box.read()
                if len(x):
                    self.marker_outlet.push_sample(['button_press'])
                    audio.stop()
                    self.marker_outlet.push_sample(['audio_stop'])
                    perf_sleep(np.random.randint(30, 41, 1).item() / 10)  # wait 3 to 4 seconds
                    return x
            except:
                continue

        while True:
            # Play the audio
            audio.play()
            start_time = time.perf_counter()
            duration = audio.getDuration()

            # Monitor button input during audio playback
            while time.perf_counter() - start_time < duration:
                try:
                    x = self.button_box.read()
                    if len(x):
                        self.marker_outlet.push_sample(['button_press'])
                        audio.stop()
                        perf_sleep(np.random.randint(30, 41, 1).item() / 10)  # wait 3 to 4 seconds
                        return x
                except:
                    continue
            # Monitor button input during audio playback
            while time.perf_counter() - start_time < duration:
                pass

            # 3-second pause between playbacks, still checking for input
            end_time = time.perf_counter() + 3
            while time.perf_counter() < end_time:
                try:
                    x = self.button_box.read()
                    if len(x):
                        self.marker_outlet.push_sample(['button_press'])
                        audio.stop()
                        self.marker_outlet.push_sample(['audio_stop'])
                        perf_sleep(np.random.randint(30, 41, 1).item() / 10)  # wait 3 to 4 seconds
                        return x
                except:
                    continue

    def cue_audio_single(self, ref_obj: str, target_obj: str, mode: str):
        """Cue audio before a trial"""
        audio = sound.Sound(f'{self.audio_path}/{mode}_{ref_obj}2{target_obj}.mp3')

        audio.play()
        start_time = time.perf_counter()
        duration = audio.getDuration() + 2

        # Monitor button input during audio playback
        while time.perf_counter() - start_time < duration:
            pass
        
    def get_available_audio_devices(self):
        return list(tools.systemtools.getAudioDevices().keys())
    
    def select_speakers(self):
        # Set speakers
        prefs.hardware['audioLib'] = ['PTB'] if ['PTB'] in prefs.hardware['audioLib'] else prefs.hardware['audioLib'] # Most time accurate library according to psychopy docs
        
        # default_audio_devices = [
        #     'OUT 3-4 (BEHRINGER X-AIR)', # For lab PC
        #     'Speakers (Realtek(R) Audio)', # For Windows
        #     'Speakers (High Definition Audio Device)' # For my mac
        # ]

        while True:
            print("Available audio devices:\nFOR EXPERIMENT SELECT 'OUT 3-4 (BEHRINGER X-AIR)'\n")
            audio_devices = self.get_available_audio_devices()
            for i, device_name in enumerate(audio_devices):
                print(i, device_name)
            audio_device_id = int(input(f'Select audio device: {list(range(len(audio_devices)))}\n'))
            audio_device = audio_devices[audio_device_id]
            print(audio_device)
            prefs.hardware['audioDevice'] = audio_device
            self.cue_audio_single(self.objects[0], self.objects[1])
            if input('Do the speakers work? y/n\n') == 'y':
                break