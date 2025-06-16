# Checklist for running this experiment on DCC lab computer
Visual stimulation requires high time-accuracy to correctly mark labels.
Below are computer settings checklist for optimal prsentation time accuracy.

## Windows Display Settings
1. Scale and Layout
    - 100% (Recommended)
2. Display Resolution:
    - Recommended native resolution
3. Multiple displays
    - __Extended__
    - DO NOT USE CLONE OR A SINGLE DISPLAY
4. Screen refresh rate
    - Fit your experiment

## GPU settings
Highly recommended to use a GPU. Intel integrated GPUs use triple buffering which OpenGL does not support. This results in presentation being 1 or 2 frames being late. GPUs provide double-buffering and optimal presentation speed.

### NVIDIA Control Panel
1. Manage 3D settings
    - Image Scaling: OFF
    - Ambient Occlusion: OFF
    - Anisotropic filtering: OFF
    - Antialiasing - FXAA: OFF
    - Antialiasing - Gamma Correction: ON
    - Antialiasing mode: OFF
    - Antialiasing - Setting: None
    - Antialiasing - Transparency: Off
    - Background Application Max Frame Rate: Off
    - CUDA -GPUs: All
    - CUDA -Sysmem Fallback Policy: Driver Default
    - DSR - Factors: OFF
    - DSR - Smoothness: OFF
    - __Low Latency Mode: Ultra__
    - Max Frame Rate: OFF
    - Multi-Frame Sampled AA (MFAA): OFF
    - __OpenGL GDI Compatiblity: Auto__
    - __OpenGL rendering GPU: NVIDIA GeForce GTX 1050 Ti (or your GPU and not Intel integrated GPU)__
    - __Power Management Mode: Prefer maximum Performance__
    - Preferred refresh rate (BenQ XL 2430T): Application controlled
    - Shader cache size: Driver default
    - Texture filtering - Anisotropic Sample Optimization: On
    - Texture filtering - Negative LOD bias: Allow
    - Texture filtering - Quality: High performance
    - Texture filtering - Trillinear optimization: On
    - Threaded optimization: Auto
    - __Triple buffering: OFF__
    - __Vertical sync: On__
    - Virtual reaility pre-rendered frames: 1
    - Vulkan/Opengl present method: Auto

## Vsync sensor settings
Highly recommended to connect tthe vsync sensor to the motherboard directly. Or high speed USB-TYpe C hub.
### Comport settings
Go to device manager -> Ports (COM & LPT) -> USB Serial Device (COM3), correctly select the COM port for your sensor.
Right click -> properties -> Port settings
 - Bits per second: 9600
 - Data bits: 8
 - Parity: None
 - Stop bits: 1
 - Flow control: None
Go to "Advanced". Untick the "Use FIFO Buffers (requires 16550 compatible UART)" and click OK.


### Necessity of a GPU
from psychopy documentation:
‘Blocking’ on the VBI
As of version 1.62 PsychoPy® ‘blocks’ on the vertical blank interval meaning that, once Window.flip() has been called, no code will be executed until that flip actually takes place. The timestamp for the above frame interval measurements is taken immediately after the flip occurs. Run the timeByFrames demo in Coder to see the precision of these measurements on your system. They should be within 1ms of your mean frame interval.

Note that Intel integrated graphics chips (e.g. GMA 945) under win32 do not sync to the screen at all and so blocking on those machines is not possible.