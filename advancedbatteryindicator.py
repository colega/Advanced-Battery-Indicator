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


class AdvancedBatteryIndicator:
	def __init__(self):
		self.initDBus();
		
		self.finished = threading.Event();
		self.loadConfig();
		
		self.createIndicator();
		self.createMenu();
		
		self.startUpdater();
		
	def createIndicator(self):
		self.ind = appindicator.Indicator("example-simple-client", "indicator-battery", appindicator.CATEGORY_APPLICATION_STATUS);
		self.ind.set_status(appindicator.STATUS_ACTIVE);
		
		
	def createMenu(self):
		self.menu = gtk.Menu();
		
		self.noBatteryMenuItem = gtk.MenuItem('No battery found');
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
		if (self.prefs['watts'])
			radioWatts.set_active();
		radioMilliamperes = gtk.RadioMenuItem(radioWatts, "Milliamperes");
		radioMilliamperes.connect("toggled", lambda e: self.prefs.__setitem__('watts',False));
		formatSubMenu.append(radioMilliamperes);
		if (not self.prefs['watts'])
			radioMilliamperes.set_active();
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
			print i;
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
		
		separator2 = gtk.SeparatorMenuItem();
		self.menu.append(separator2);
		
		quitMenuItem = gtk.MenuItem('Quit');
		quitMenuItem.connect("activate", self.quit);
		self.menu.append(quitMenuItem);
        
		self.menu.show_all();
		self.ind.set_menu(self.menu);		
		
	def startUpdater(self):
		self.updaterThread = threading.Thread(target=self.update);
		self.updaterThread.start();
	
	def initDBus(self):
		self.bus = dbus.SystemBus();
		self.bat = self.bus.get_object('org.freedesktop.UPower', '/org/freedesktop/UPower/devices/battery_BAT0')
		self.refresh = self.bat.get_dbus_method('Refresh', dbus_interface='org.freedesktop.UPower.Device');

	def showWatts(self, widget, data=None):
		self.format = 1;
	
	def showMilliampers(self, widget, data=None):
		self.format = 0;
	
	def quit(self, widget, data=None):
		self.saveConfig();
		self.finished.set();
		gtk.main_quit();
		
	def loadConfig(self):	
		try:
			f = open(os.path.expanduser('~/.config/advancedbatteryindicator/config.pickle'), 'r');
			self.prefs = pickle.load(f);
			f.close();
		except:
			print "Loading default config";
			self.prefs = {'watts': True, 'updateInterval':0.5};
		
	def saveConfig(self):
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
	
	def update(self):
		while not self.finished.is_set():
			try:
				self.refresh();
				
				props =  self.bat.GetAll('org.freedesktop.UPower.Device', dbus_interface='org.freedesktop.DBus.Properties');
				
				self.noBatteryMenuItem.hide();
				self.noBatteryMenuSeparator.hide();
				
				for i in props:
					pass;
					#print i,':',props[i];
			
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
				print "Refresh failed. Maybe no battery present?";
				self.ind.set_label('N/A');
				self.healthMenuItem.set_label('Battery health: N/A');
				self.voltageMenuItem.set_label('Voltage: N/A');
				
				self.noBatteryMenuItem.show();
				self.noBatteryMenuSeparator.show();
			time.sleep(self.prefs['updateInterval']);
		
	def main(self):
		gtk.main();
		
		

if __name__ == "__main__":
	gtk.gdk.threads_init();
	indicator = AdvancedBatteryIndicator();	
	gtk.gdk.threads_enter()
	indicator.main();
	gtk.gdk.threads_leave()
