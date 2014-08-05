# Copyright (C) 2014  Justin Harris, Niklas Rosenstein
# All rights reserved.

import myo
import sys
from myo.lowlevel import pose_t
myo.init()
from myo.six import print_
from send_keys.keystrokes import *

class Listener(myo.DeviceListener):

    def on_connect(self, myo, timestamp):
        print 'on_connect'
        myo.request_rssi()

    def on_rssi(self, myo, timestamp, rssi):
        print_("RSSI:", rssi)

    def on_event(self, event):
        r""" Called before any of the event callbacks. """

    def on_event_finished(self, event):
        r""" Called after the respective event callbacks have been
        invoked. This method is *always* triggered, even if one of
        the callbacks requested the stop of the Hub. """

    def on_pair(self, myo, timestamp):
        print 'on_pair'

    def on_disconnect(self, myo, timestamp):
        print 'on_disconnect'

    def on_pose(self, myo, timestamp, pose):
        print 'on_pose', pose
        #tap_key(VK_SPACE)
        if pose == pose_t.fist:
            pass
        elif pose == pose_t.wave_out:
            pass
        elif pose == pose_t.wave_in:
            pass

    def on_orientation_data(self, myo, timestamp, orientation):
        x,y,z,w = orientation
        print zip('xyzw', orientation)
        pass

    def on_accelerometor_data(self, myo, timestamp, acceleration):
        pass

    def on_gyroscope_data(self, myo, timestamp, gyroscope):
        pass

def main():
    try:
        hub = myo.Hub()
        hub.run(1000, Listener())
        print "Running..."
    except:
        sys.stderr.write('Make sure that Myo Connect is running and a Myo is paired.\n')
        raise

    # Listen to keyboard interrupts and stop the
    # hub in that case.
    try:
        while hub.running:
            myo.time.sleep(0.2)
    except KeyboardInterrupt:
        print_("Quitting ...")
        hub.stop(True)

if __name__ == '__main__':
    main()

