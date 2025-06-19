import serial
from psychopy import visual, event


# make a buttonbox
ser = serial.Serial("COM6", 115200, timeout = 0.10)
ser.write('A1'.encode())
ser.reset_input_buffer()
ser.flush()
text = ""
for _ in range(100):
    text = text + ser.read().decode()
    if "BITSI mode, Ready!\r\n" in text:
        print("Button ready!")
        break

win = visual.Window(size=(1920, 1080), winType='pyglet', fullscr=True, screen=1, units="pix", color='black', waitBlanking=True, allowGUI=True)

while True:
	x = ser.readline().decode()
	visual.TextStim(win, text=x, height=500).draw()
	# black screen for 1000 ms
	win.flip()
	key = event.getKeys()
	try:
		if key[0]=='escape':
			break
	except:
		continue