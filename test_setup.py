from lasers import LaserController
from window import ScreenStimWindow
from audio import AudioController
from button_box import ButtonBoxController
from psychopy import event

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
button_box = ButtonBoxController()
audio = AudioController(audio_path='./tts/queries/psychopy_slowed', button_box=button_box)

# Test lasers
if input('Test lasers? y/n\n') == 'y':
    lasers.on()
    val = input('Press any key after pointing lasers to objects.\n')

    ## Verify lasers are pointing correct objects
    lasers.test_laser_order()
    
# Test screen
if input('Test screen? y/n\n') == 'y':
    print('Follow instructions on screen.')
    screen.draw_text('Press any key to continue.')
    screen.win.flip()
    event.waitKeys()
    screen.screen_warmup(3)
    screen.test_erp(2)
    screen.draw_text('Press any key to continue.')
    screen.win.flip()
    event.waitKeys()
    screen.screen_warmup(3)
    screen.test_cvep(2)

# Test button box
print('Press a button in the button box.\n')
while True:
    val = button_box.read()
    if len(val) > 0:
        break
print('Pressed button:', val)

## Test audio
audio.cue_audio('can', 'candle', 'scene', play_once=True)
_ = input('Can you hear an audio cue? y/n\n')

print('Test complete!')
