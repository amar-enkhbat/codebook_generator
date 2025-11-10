from lasers import LaserController
from window import ScreenStimWindow
from audio import AudioController
from button_box import ButtonBoxController

objects = {
    0: 'can', 
    1: 'bandage', 
    2: 'remote', 
    3: 'bottle', 
    4: 'candle', 
    5: 'box', 
    6: 'book', 
    7: 'cup'
}

lasers = LaserController()
screen = ScreenStimWindow(objects=objects)
button = ButtonBoxController()
audio = AudioController(audio_path='./tts/queries/tts/psychopy_slowed', button_box=button)

# Test lasers
## Turn on pointers
lasers.on()
val = input('Press any key after pointing lasers to objects.\n')

## Verify lasers are pointing correct objects
lasers.test_laser_order()
val = input('Press any key if correct.\n')

# Test screen
screen.test_erp(2)
screen.test_cvep(2)
val = input('Verify screen refresh rate is 60hz,\n# of dropped frame rates is 0.\n')

# Test button box
val = input('Press a button in the button box')
while True:
    val = button.read()
    if len(val) > 0:
        break
print('Pressed button:', val)

## Test audio
audio.cue_audio('can', 'candle', 'scene')
_ = input('Did audio play?\n')

print('Test complete!')
