import xbmc
import xbmcgui
import xbmcaddon
import os
import time
import pigpio
import datetime

__settings__   = xbmcaddon.Addon(id='script.service.gpio-pwm-backlight')
__cwd__        = __settings__.getAddonInfo('path')
__icon__       = os.path.join(__cwd__,"icon.png")
__scriptname__ = "GPIO PWM LCD Backlight"

WINDOW_FULLSCREEN_VIDEO = 12005 # when video is playing fullscreen
WINDOW_VISUALISATION 	= 12006 # when audio is playing fullscreen

def log(loglevel, msg):
	xbmc.log("### [%s] - %s" % (__scriptname__,msg,), level=loglevel)

class addon():
	def __init__(self):
		# settings variables
		self.pi_conn = None
		
		#GPIO settings
		self.gpio_pin = 27
		self.pwm_freq = 1000
		self.bright_duty = 100
		self.dim_duty = 10
		self.dim_time = 0.5

		# when to dim settings
		self.dimonscreensaver = True
		self.dimonshutdown = True
		self.dimonvideoplayback = True
		self.dimonmusicplayback = True
		self.lightonosd = True
		
		self.offovernight = False
		self.offtime = datetime.time(22,0)
		self.ontime = datetime.time(7,0)

		# working variables
		self.setting_check_time = None

		# used for navigation tracking
		self.oldMenu = ""
		self.oldSubMenu = ""
		self.navTimer = time.time()
		self.oldFilenameandpath = ""
		self.CachedFilenameIsStream = False

	def checkSettings(self):
		if not self.setting_check_time: # if no previous check
			self.setting_check_time = time.time() # record time of this check
		else:
			if (time.time() - self.setting_check_time) > 2: # if 2 seconds since last check
				self.setting_check_time = time.time() # record time of this check
			else:
				return False # exit without checking

		settingsChanged = False

		if not self.pi_conn: # if no pi connection has been set up
			settingsChanged = True # force a setup

		gpio_pin = int(__settings__.getSetting("gpiopin"))
		pwm_freq = int(__settings__.getSetting("pwmfreq"))
		self.bright_duty =int( __settings__.getSetting("brightduty"))
		self.dim_duty = int(__settings__.getSetting("dimduty"))
		self.dim_time = float(__settings__.getSetting("dimtime"))
		self.dimonscreensaver = __settings__.getSetting("dimonscreensaver") == "true"
		self.dimonshutdown = __settings__.getSetting("dimonshutdown") == "true"
		self.dimonvideoplayback = __settings__.getSetting("dimonvideoplayback") == "true"
		self.dimonmusicplayback = __settings__.getSetting("dimonmusicplayback") == "true"
		self.lightonosd = __settings__.getSetting("lightonosd") == "true"
		self.offovernight = __settings__.getSetting("offovernight") == "true"
		self.offtime = datetime.time(*[int(x) for x in __settings__.getSetting("offtime").split(":")])
		self.ontime = datetime.time(*[int(x) for x in __settings__.getSetting("ontime").split(":")])

		if self.gpio_pin != gpio_pin:
			self.gpio_pin = gpio_pin
			settingsChanged = True

		if self.pwm_freq != pwm_freq:
			self.pwm_freq = pwm_freq
			settingsChanged = True

		return settingsChanged

	def setup_Pi_Connection(self):
		if self.pi_conn:
			self.pi_conn.stop()
			self.pi_conn = None

		self.pi_conn = pigpio.pi()
		self.pi_conn.set_PWM_range(self.gpio_pin, 100)
		self.pi_conn.set_PWM_frequency(self.gpio_pin, self.pwm_freq)
		try: # see if pin is already being used for PWM and do nothing if so
			pwm = self.pi_conn.get_PWM_dutycycle(self.gpio_pin)
		except pigpio.error: # pin was not being used for PWM so assume first start
			self.pi_conn.set_PWM_dutycycle(self.gpio_pin, 0)
			
	def do_backlight(self, pwm, target_pwm):
		if self.dim_time != 0:
			delay = self.dim_time / (abs(pwm - target_pwm))
			if pwm > target_pwm: # if currently brighter than setting
				for num in range(pwm, target_pwm, -1): # decrease from current to setting
					self.pi_conn.set_PWM_dutycycle(self.gpio_pin, num)
					time.sleep(delay)
			else: # if currently dimmer than setting
				for num in range(pwm, target_pwm, 1): # increase from current to setting
					self.pi_conn.set_PWM_dutycycle(self.gpio_pin, num)
					time.sleep(delay)
		self.pi_conn.set_PWM_dutycycle(self.gpio_pin, target_pwm)

	def handle_backlight(self):
		action = None
		
		# if settings set for never dimming then always brighten
		if not (self.dimonvideoplayback or self.dimonmusicplayback or self.dimonscreensaver):
			action = "brighten"

		# check player and settings to determine if should dim/brighten
		if self.isPlayingVideo():
			if self.dimonvideoplayback:
				if self.isShowingOSD() and self.lightonosd:
					action = "brighten"
				else:
					action = "dim"
			else:
				action = "brighten"
			if self.isPlayerPaused():
				action = "brighten"
		elif self.isPlayingAudio():
			if self.dimonmusicplayback:
				if self.isShowingOSD() and self.lightonosd:
					action = "brighten"
				else:
					action = "dim"
			else:
				action = "brighten"
			if self.isPlayerPaused():
				action = "brighten"
		else:
			action = "brighten"

		if self.getBool("System.ScreenSaverActive"):
			if self.dimonscreensaver:
				action = "dim"
			if self.offovernight:
				cur_time = datetime.datetime.now().time()
				if cur_time < self.ontime:
					action = "off"
				elif cur_time > self.offtime:
					action = "off"

		# if navigating always brighten
		if self.isNavigationActive():
			action = "brighten"

		# get the current brightness
		pwm = self.pi_conn.get_PWM_dutycycle(self.gpio_pin)
		
		# if an operation needs to happen then call it here
		if (action=="dim"):
			if pwm != self.dim_duty: # only act if pwm doesn't match settings
				self.do_backlight(pwm, self.dim_duty)
		elif (action=="brighten"):
			if pwm != self.bright_duty: # only act if pwm doesn't match settings
				self.do_backlight(pwm, self.bright_duty)
		elif (action=="off"):
			if pwm !=  0: # only act if pwm doesn't match settings
				self.do_backlight(pwm, 0)

	def getInfoLabel(self, strLabel):
		return xbmc.getInfoLabel(strLabel)

	def getBool(self, strBool):
		return xbmc.getCondVisibility(strBool)

	def isPlayingVideo(self):
		return self.getBool("Player.HasVideo")

	def isPlayingAudio(self):
		return self.getBool("Player.HasAudio")
	
	def isPlayerPlaying(self):
		return self.getBool("Player.Playing")

	def isPlayerPaused(self):
		return self.getBool("Player.Paused")
	
	def isShowingOSD(self):
		if self.getInfoLabel("System.CurrentWindow") in ["Fullscreen OSD"]:
			return True
		else:
			return False

	def isNavigationActive(self):
		ret = False

		navtimeout = 5
		menu = self.getInfoLabel("$INFO[System.CurrentWindow]")
		subMenu = self.getInfoLabel("$INFO[System.CurrentControl]")

		if menu != self.oldMenu or subMenu != self.oldSubMenu or (self.navTimer + navtimeout) > time.time():
			ret = True
			if menu != self.oldMenu or subMenu != self.oldSubMenu:
				self.navTimer = time.time()      
				self.oldMenu = menu
				self.oldSubMenu = subMenu

#		xbmc.executebuiltin("XBMC.Notification(%s,%s,%s,%s)" % ("Window:",str(int(xbmcgui.getCurrentWindowId())),10,None))

		if int(xbmcgui.getCurrentWindowId()) in [WINDOW_FULLSCREEN_VIDEO, WINDOW_VISUALISATION]:
			ret = False
			
		if self.getInfoLabel("System.CurrentWindow") in ["Fullscreen OSD"]:
			ret = False
			
		return ret

	def mainloop(self):
#		log(xbmc.LOGNOTICE, "mainloop")
		while not xbmc.abortRequested: # enter loop that will exit on XBMC/kodi exit
			if self.checkSettings(): # see if settings have changed
				self.setup_Pi_Connection() # if settings have changed that require a reconnect then reconnect
			self.handle_backlight() # see if should light/dim and handle it
			time.sleep(0.2) # sleep to prevent high CPU usage

		if self.dimonshutdown:
			pwm = self.pi_conn.get_PWM_dutycycle(self.gpio_pin)
			self.do_backlight(pwm, 0) # do a dim to nothing on shutdown
			
		self.pi_conn.stop() # cleanup by closing connection
		self.pi_conn = None

add = addon()
add.mainloop()
