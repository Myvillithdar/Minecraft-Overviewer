#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import time
import logging
import progressbar
import sys
import os

class Observer(object):
    """Base class that defines the observer interface.
    """

    def __init__(self):
        self._current_value = None
        self._max_value = None
        self.start_time = None
        self.end_time = None

    def start(self, max_value):
        """Signals the start of whatever process. Must be called before update
        """
        self._set_max_value(max_value)
        self.start_time = time.time()
        self.update(0)
        return self

    def is_started(self):
        return self.start_time is not None

    def finish(self):
        """Signals the end of the processes, should be called after the
        process is done.
        """
        self.end_time = time.time()

    def is_finished(self):
        return self.end_time is not None

    def is_running(self):
        return self.is_started() and not self.is_finished()

    def add(self, amount):
        """Shortcut to update by increments instead of absolute values. Zero
        amounts are ignored.
        """
        if amount:
            self.update(self.get_current_value() + amount)

    def update(self, current_value):
        """Set the progress value. Should be between 0 and max_value. Returns
        whether this update is actually displayed.
        """
        self._current_value = current_value
        return False

    def get_percentage(self):
        """Get the current progress percentage. Assumes 100% if max_value is 0
        """
        if self.get_max_value() is 0:
            return 100.0
        else:
            return self.get_current_value() * 100.0 / self.get_max_value()

    def get_current_value(self):
        return self._current_value

    def get_max_value(self):
        return self._max_value

    def _set_max_value(self, max_value):
        self._max_value = max_value

class LoggingObserver(Observer):
    """Simple observer that just outputs status through logging.
    """
    def __init__(self):
        super(Observer, self).__init__()
        #this is an easy way to make the first update() call print a line
        self.last_update = -101

    def finish(self):
        logging.info("Rendered %d of %d.  %d%% complete", self.get_max_value(),
            self.get_max_value(), 100.0)
        super(LoggingObserver, self).finish()

    def update(self, current_value):
        super(LoggingObserver, self).update(current_value)
        if self._need_update():
            logging.info("Rendered %d of %d.  %d%% complete",
                self.get_current_value(), self.get_max_value(),
                self.get_percentage())
            self.last_update = current_value
            return True
        return False

    def _need_update(self):
        cur_val = self.get_current_value()
        if cur_val < 100:
            return cur_val - self.last_update > 10
        elif cur_val < 500:
            return cur_val - self.last_update > 50
        else:
            return cur_val - self.last_update > 100

default_widgets = [
    progressbar.Percentage(), ' ',
    progressbar.Bar(marker='=', left='[', right=']'), ' ',
    progressbar.CounterWidget(), ' ',
    progressbar.GenericSpeed(format='%.2ft/s'), ' ',
    progressbar.ETA(prefix='eta ')
]
class ProgressBarObserver(progressbar.ProgressBar, Observer):
    """Display progress through a progressbar.
    """

    #the progress bar is only updated in increments of this for performance
    UPDATE_INTERVAL = 25

    def __init__(self, widgets=default_widgets, term_width=None, fd=sys.stderr):
        super(ProgressBarObserver, self).__init__(widgets=widgets,
            term_width=term_width, fd=fd)
        self.last_update = 0 - (self.UPDATE_INTERVAL + 1)

    def start(self, max_value):
        self._set_max_value(max_value)
        logging.info("Rendering %d total tiles." % max_value)
        super(ProgressBarObserver, self).start()

    def is_started(self):
        return self.start_time is not None

    def finish(self):
        self._end_time = time.time()
        super(ProgressBarObserver, self).finish()
        self.fd.write('\n')
        logging.info("Rendering complete!")

    def update(self, current_value):
        if super(ProgressBarObserver, self).update(current_value):
            self.last_update = self.get_current_value()

    percentage = Observer.get_percentage

    def get_current_value(self):
        return self.currval

    def get_max_value(self):
        return self.maxval

    def _set_max_value(self, max_value):
        self.maxval = max_value

    def _need_update(self):
        return self.get_current_value() - self.last_update > self.UPDATE_INTERVAL

class JSObserver(Observer):
    """Display progress on index.html using JavaScript
    """

    def __init__(self, outputdir, minrefresh=5):
        """Initialise observer
	outputdir must be set to the map output directory path
	minrefresh specifies the minimum gap between requests, in seconds
	"""
	self.last_update = -11
	self.last_update_time = -1 
	self._current_value = -1
	self.minrefresh = 1000*minrefresh
        self.logfile = os.path.join(outputdir, "progress.js") 

	f = open(self.logfile, "w", 0) 
	f.write('{"message": "Render in progress", "update": %d}' % self.minrefresh)
        f.close()

    def start(self, max_value):
        f = open(self.logfile, "w", 0)
	f.write('{"message": "Rendering %d tiles", "update": %s}' % (max_value, self.minrefresh))
        self.start_time=time.time()
	self._set_max_value(max_value)

    def is_started(self):
        return self.start_time is not None

    def finish(self):
        """Signals the end of the processes, should be called after the
        process is done.
        """
        self.end_time = time.time()
	duration = self.end_time - self.start_time
        f = open(self.logfile, "w", 0)
	f.write('{"message": "Render completed in %dm %ds", "update": "false"}' % (duration//60, duration - duration//60))
        f.close()

    def is_finished(self):
        return self.end_time is not None

    def is_running(self):
        return self.is_started() and not self.is_finished()

    def add(self, amount):
        """Shortcut to update by increments instead of absolute values. Zero
        amounts are ignored.
        """
        if amount:
            self.update(self.get_current_value() + amount)

    def update(self, current_value):
        """Set the progress value. Should be between 0 and max_value. Returns
        whether this update is actually displayed.
        """
        self._current_value = current_value
        if self._need_update():
            refresh = max(1500*(time.time() - self.last_update_time), self.minrefresh)
            f = open(self.logfile, "w", 0)
	    f.write('{"message": "Rendered %d of %d tiles (%d%%)", "update": %d }' % (self.get_current_value(), self.get_max_value(), self.get_percentage(), refresh))
            f.close()
            self.last_update_time = time.time()
	    self.last_update = current_value
	    return True
        return False

    def get_percentage(self):
        """Get the current progress percentage. Assumes 100% if max_value is 0
        """
        if self.get_max_value() is 0:
            return 100.0
        else:
            return self.get_current_value() * 100.0 / self.get_max_value()

    def get_current_value(self):
        return self._current_value

    def get_max_value(self):
        return self._max_value

    def _set_max_value(self, max_value):
        self._max_value = max_value 

    def _need_update(self):
        cur_val = self.get_current_value()
        if (time.time() - self.last_update_time) <= self.minrefresh//1000:
            return False
        if cur_val < 100:
            return cur_val - self.last_update > 10
        elif cur_val < 500:
            return cur_val - self.last_update > 50
        else:
            return cur_val - self.last_update > 100

