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
import dbus


class AdvancedBatteryIndicator:
	def __init__(self):
		self.initDBus();
		
		self.finished = threading.Event();
		self.prefs = {'watts': True, 'updateInterval':0.5};
		self.updateInterval = 1.0;
		
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
		self.menu.append(self.healthMenuItem);
		
		separator = gtk.SeparatorMenuItem();
		self.menu.append(separator);
		
		formatMenuItem = gtk.MenuItem('Units');
		radioWatts = gtk.RadioMenuItem(None, "Watts");
		radioWatts.connect("activate", lambda e: self.prefs.__setitem__('watts',True));
		formatSubMenu = gtk.Menu();
		formatSubMenu.append(radioWatts);
		radioWatts.activate();
		radioMilliamperes = gtk.RadioMenuItem(radioWatts, "Milliampers");
		radioMilliamperes.connect("activate", lambda e: self.prefs.__setitem__('watts',False));
		formatSubMenu.append(radioMilliamperes);
		formatMenuItem.set_submenu(formatSubMenu);
		self.menu.append(formatMenuItem);
		
		updateIntervalMenuItem = gtk.MenuItem("Update interval");
		updateIntervalSubMenu = gtk.Menu();
		updateHalfSecond = gtk.RadioMenuItem(None, "0.5 seconds");
		updateHalfSecond.connect("activate", lambda e: self.prefs.__setitem__('updateInterval',0.5));
		updateIntervalSubMenu.append(updateHalfSecond);
		updateOneSecond = gtk.RadioMenuItem(updateHalfSecond, "1 second");
		updateOneSecond.connect("activate", lambda e: self.prefs.__setitem__('updateInterval',1.0));
		updateOneSecond.activate();
		updateIntervalSubMenu.append(updateOneSecond);
		updateTwoSeconds = gtk.RadioMenuItem(updateHalfSecond, "2 seconds");
		updateTwoSeconds.connect("activate", lambda e: self.prefs.__setitem__('updateInterval',2.0));
		updateIntervalSubMenu.append(updateTwoSeconds);
		updateThreeSeconds = gtk.RadioMenuItem(updateHalfSecond, "3 seconds");
		updateThreeSeconds.connect("activate", lambda e: self.prefs.__setitem__('updateInterval',3.0));
		updateIntervalSubMenu.append(updateThreeSeconds);
		updateFiveSeconds = gtk.RadioMenuItem(updateHalfSecond, "5 seconds");
		updateFiveSeconds.connect("activate", lambda e: self.prefs.__setitem__('updateInterval',5.0));
		updateIntervalSubMenu.append(updateFiveSeconds);
		updateIntervalMenuItem.set_submenu(updateIntervalSubMenu);
		updateOneSecond.activate();
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
		self.finished.set();
		gtk.main_quit();
	
	
	def update(self):
		while not self.finished.is_set():
			try:
				self.refresh();
				
				props =  self.bat.GetAll('org.freedesktop.UPower.Device', dbus_interface='org.freedesktop.DBus.Properties');
				
				self.noBatteryMenuItem.hide();
				self.noBatteryMenuSeparator.hide();
				
				for i in props:
					print i,':',props[i];
			
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
