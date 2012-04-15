#!/usr/bin/env python

# Indicator of power consumption for Unity
# 
# Copyright 2012 Oleg Zaytsev.
#
# Authors:
#     Oleg Zaytsev <lambroso@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as 
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

import gtk, gobject
import appindicator
import os, time, threading
import dbus;
import pickle;
from optparse import OptionParser

class AdvancedBatteryIndicator:
	def __init__(self):
		# Parse running options
		self.parseOptions();
		
		# Initiate gtk multithreading
		gtk.gdk.threads_init();
		# Connect DBus to UPower
		self.initDBus();
		
		# Just an event to stop the updater thread
		self.finished = threading.Event();
		
		# Load configuration from ~/.config/advancedbatteryindicator/config.pickle
		self.loadConfig();
		
		# Create the indicator
		self.createIndicator();
		# Create the indicator menu
		self.createMenu();
		
		# Start the updater thread
		self.startUpdater();
		
		# Run main gtk loop
		self.main();
	
	# Will parse the script options and save them to self.options
	def parseOptions(self):	
		parser = OptionParser();
		parser.add_option("--noconfig", action="store_true",dest="noConfig",help="Do not save or load config.");
		parser.add_option("--noquit", action="store_true",dest="noQuitOption",help="Do not show 'Quit' menu option.");
		parser.add_option("--debug", action="store_true", dest="debug",help="Show misc debug info.");
		parser.add_option("--debugall", action="store_true", dest="debugAll",help="Show all debug info");
		(self.options, args) = parser.parse_args();
		if self.options.debugAll:
			self.options.debug = True;
		
	def createIndicator(self):
		self.ind = appindicator.Indicator("example-simple-client", "indicator-battery", appindicator.CATEGORY_APPLICATION_STATUS);
		self.ind.set_status(appindicator.STATUS_ACTIVE);
		
	def createMenu(self):
		self.menu = gtk.Menu();
		
		self.noBatteryMenuItem = gtk.ImageMenuItem(gtk.STOCK_DISCONNECT);
		self.noBatteryMenuItem.set_label("No battery found.")
		self.noBatteryMenuItem.set_no_show_all(True);
		self.menu.append(self.noBatteryMenuItem);
		self.noBatteryMenuSeparator = gtk.SeparatorMenuItem();
		self.noBatteryMenuSeparator.set_no_show_all(True);
		self.menu.append(self.noBatteryMenuSeparator);
		
		self.voltageMenuItem = gtk.MenuItem("Voltage: no data");
		self.menu.append(self.voltageMenuItem);
		
		self.healthMenuItem = gtk.MenuItem("Battery health: no data");
		self.healthMenuItem.set_tooltip_text('Hoho');
		self.menu.append(self.healthMenuItem);
		
		
		separator = gtk.SeparatorMenuItem();
		self.menu.append(separator);
		
		formatMenuItem = gtk.MenuItem('Units');
		radioWatts = gtk.RadioMenuItem(None, "Watts");
		radioWatts.connect("toggled", lambda e: self.prefs.__setitem__('watts',True));
		formatSubMenu = gtk.Menu();
		formatSubMenu.append(radioWatts);
		if (self.prefs['watts']):
			radioWatts.set_active(True);
		radioMilliamperes = gtk.RadioMenuItem(radioWatts, "Milliamperes");
		radioMilliamperes.connect("toggled", lambda e: self.prefs.__setitem__('watts',False));
		formatSubMenu.append(radioMilliamperes);
		if (not self.prefs['watts']):
			radioMilliamperes.set_active(True);
		formatMenuItem.set_submenu(formatSubMenu);
		self.menu.append(formatMenuItem);
		
		updateIntervalMenuItem = gtk.MenuItem("Update interval");
		updateIntervalSubMenu = gtk.Menu();
		
		updateRadios = [];
		updateLabels = ["0.5 seconds", "1 second", "2 seconds", "3 seconds", "5 seconds"];
		updateIntervals = [0.5,1.0,2.0,3.0,5.0];
		updateLambdas = [lambda x,i=i: self.prefs.__setitem__('updateInterval',i) for i in updateIntervals]
		for i in range(len(updateLabels)):
			group = None;
			if (i>0):
				group = updateRadios[0];
			updateRadio = gtk.RadioMenuItem(group, updateLabels[i])
			updateRadio.connect("toggled", updateLambdas[i]);
			updateIntervalSubMenu.append(updateRadio);
			if updateIntervals[i] == self.prefs['updateInterval']:
				updateRadio.set_active(True);
			updateRadios += [updateRadio];
				
		updateIntervalMenuItem.set_submenu(updateIntervalSubMenu);
		self.menu.append(updateIntervalMenuItem);
		
		if not self.options.noQuitOption:
			separatorQuit = gtk.SeparatorMenuItem();
			self.menu.append(separatorQuit);
		
			quitMenuItem = gtk.MenuItem('Quit');
			quitMenuItem.connect("activate", self.quit);
			self.menu.append(quitMenuItem);
        
		self.menu.show_all();
		self.ind.set_menu(self.menu);		
	
	# Start updater thread	
	def startUpdater(self):
		self.updaterThread = threading.Thread(target=self.update);
		self.updaterThread.start();
	
	def initDBus(self):
		# DBus bus
		self.bus = dbus.SystemBus();
		# Battery proxy
		self.bat = self.bus.get_object('org.freedesktop.UPower', '/org/freedesktop/UPower/devices/battery_BAT0');
	
	def quit(self, widget, data=None):
		self.saveConfig();
		self.finished.set();
		gtk.main_quit();
	
	# Load the configuration	
	def loadConfig(self):	
		try:
			if self.options.noConfig:
				raise;
			f = open(os.path.expanduser('~/.config/advancedbatteryindicator/config.pickle'), 'r');
			self.prefs = pickle.load(f);
			f.close();
		except:
			print "Loading default config";
			self.prefs = {'watts': True, 'updateInterval':0.5};
	
	# Save the configuration
	def saveConfig(self):
		if not self.options.noConfig:
			try:
				configDir = os.path.expanduser('~/.config/advancedbatteryindicator');
				if not os.path.isdir(configDir):
					os.makedirs(configDir);
				f = open(configDir+'/config.pickle', 'w');
				pickle.dump(self.prefs, f);
				print "Configuration saved at "+configDir+'/config.pickle';
				f.close();
			except:
				# TODO: What's going wrong?
				print "Something went wrong while saving config...";
	
	# Updater thread main loop
	def update(self):
		# We stop if the finished event is set
		while not self.finished.is_set():
			# Try to acces the interface, it will fail if there is no battery
			try:
				self.bat.Refresh(dbus_interface='org.freedesktop.UPower.Device');
				props =  self.bat.GetAll('org.freedesktop.UPower.Device', dbus_interface='org.freedesktop.DBus.Properties');
				
				self.noBatteryMenuItem.hide();
				self.noBatteryMenuSeparator.hide();
				
				# Debug print
				if self.options.debugAll:
					print "------ START UPOWER DUMP:"+str(time.ctime(time.time()))+"------"
					for i in props:
						print "   ",i,':',props[i];
					
					print "------ END ----";
			
				capacity = str(int(round(props['Capacity'])));
			
				rate = str(int(round(props['EnergyRate'] if self.prefs['watts'] else props['EnergyRate'] * 1000 / props['Voltage']))) + (' W' if self.prefs['watts'] else ' mA');
				energy = str(int(round(props['Energy'] if self.prefs['watts'] else props['Energy'] * 1000 / props['Voltage']))) + (' Wh' if self.prefs['watts'] else ' mAh');
				energyFull = str(int(round(props['EnergyFull'] if self.prefs['watts'] else props['EnergyFull'] * 1000 / props['Voltage']))) + (' Wh' if self.prefs['watts'] else ' mAh');
		
				self.healthMenuItem.set_label('Battery health: '+capacity+'%');
				self.voltageMenuItem.set_label('Voltage: '+str(props['Voltage'])+' V');
		
				if (props['State'] == 2):
					self.ind.set_label(rate + " / " + energy);
				elif (props['State'] == 1):
					self.ind.set_label(energy + " / " + energyFull);
				elif (props['State'] == 4):
					self.ind.set_label(energy);
				else:
					self.ind.set_label(energy);
			except:
				# Probably no battery present.
				print "Refresh failed. Maybe no battery present?";
				self.ind.set_label('N/A');
				self.healthMenuItem.set_label('Battery health: N/A');
				self.voltageMenuItem.set_label('Voltage: N/A');
				
				self.noBatteryMenuItem.show();
				self.noBatteryMenuSeparator.show();
			# Sleep
			time.sleep(self.prefs['updateInterval']);
	
	# Main gtk loopn	
	def main(self):
		gtk.gdk.threads_enter();
		gtk.main();
		gtk.gdk.threads_leave();

if __name__ == "__main__":
	indicator = AdvancedBatteryIndicator();	
