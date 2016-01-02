# GPIO PWM Backlight
Augments the capabilities provided by the XBMC LCDProc addon to provide a PWM controlled backlight for an LCD display via the GPIO pins of the raspberry pi.
This relies on the pigpio library being present and the system daemon running.
See:
https://github.com/JamesGKent/RPi2-kodi-pigpio for the raspberry pi 2 version.

At the time of writing a version has not been compiled for the raspberry pi 1

This addon offers:
1. Setting any GPIO pin as the PWM pin
2. Setting the PWM frequency
3. Setting a PWM percentage for maximum brightness
4. Setting a PWM percentage for minimum brightness
5. Setting time taken to transition from min to max/max to min brightness in 0.1s increments
6. Dim when playing video (can be disabled)
7. Dim when playing audio (can be disabled)
8. Dim on screensaver (can be disabled)
9. Dim on shutdown (can be disabled)
10. Light when on screen display is shown over video/music (can be disabled)
11. Turn backlight off if system enters screensaver mode during certain hours (can be disabled)