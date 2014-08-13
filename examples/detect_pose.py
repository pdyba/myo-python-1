# Copyright (C) 2014  Justin Harris, Niklas Rosenstein
# All rights reserved.

import myo
import sys
from myo.lowlevel import pose_t
from time import sleep
from numpy import dtype
myo.init()
from myo.six import print_
from sklearn import svm
from threading import Thread
import logging
import numpy as np
from sklearn import hmm
from random import Random
from collections import Counter, defaultdict

logging.basicConfig(level=logging.INFO)

new_pose_data = []

is_collecting_new_pose = False
is_collecting_regular = False

new_data = []

states = [pose for pose in pose_t]
# [<pose_t: [0] rest>, <pose_t: [1] fist>, <pose_t: [2] wave_in>, <pose_t: [3] wave_out>, <pose_t: [4] fingers_spread>, <pose_t: [5] reserved1>, <pose_t: [6] thumb_to_pinky>]
states.append('new')
n_states = len(states)

NUM_FEATURES = 1 + 4 + 3 + 3

class Datum():
    def __init__(self, action, dtype=None):
        self._array = [0 for _ in xrange(NUM_FEATURES)]
        if type(action) == pose_t or dtype == pose_t:
            self._array[0] = action.value
        elif dtype == 'ori':
            self._array[1:5] = action
        elif dtype == 'acc':
            self._array[5:8] = action
        elif dtype == 'gyr':
            self._array[8:11] = action

    def __repr__(self):
        return str(self._array)
            

def collect_data(datum):
    logging.debug("datum %s", datum)
    if is_collecting_new_pose:
        new_pose_data.append(datum._array)

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
        print 'on_pair', myo

    def on_disconnect(self, myo, timestamp):
        print 'on_disconnect'

    def on_pose(self, myo, timestamp, pose):
        collect_data(Datum(pose))
        if pose == pose_t.fist:
            pass
        elif pose == pose_t.wave_out:
            pass
        elif pose == pose_t.wave_in:
            pass

    def on_orientation_data(self, myo, timestamp, orientation):
        # x, y, z, w = orientation
        collect_data(Datum(orientation, 'ori'))

    def on_accelerometor_data(self, myo, timestamp, acceleration):
        logging.debug('acc %s', acceleration)
        collect_data(Datum(acceleration, 'acc'))

    def on_gyroscope_data(self, myo, timestamp, gyroscope):
        logging.debug('gyr %s', gyroscope)
        collect_data(Datum(gyroscope, 'gyr'))

def countdown(prompt):
    print 'On "GO!",', prompt
    for i in xrange(3, 0, -1):
        print i
        sleep(1)
    print 'GO!'

def chunks(data, chunk_size):
    for i in xrange(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

def get_distribution(states, ranges_in_states):
    counter = Counter()
    for new_pose_index_start, new_pose_index_end in ranges_in_states:
        counter.update(states[new_pose_index_start:new_pose_index_end])
    size = sum(counter.values())
    return dict((state, count * 1.0 / size) for state, count in counter.items())

def train_pose():
    global is_collecting_new_pose
    is_collecting_new_pose = True
    new_poses_ranges = []
    countdown('do regular stuff and not your pose.')
    for _ in xrange(1):
        sleep(2)
        countdown('do your pose.')
        new_pose_index_start = len(new_pose_data) - 1
        sleep(1)
        new_pose_index_end = len(new_pose_data)
        new_poses_ranges.append((new_pose_index_start, new_pose_index_end))
        print "Do regular stuff again."
    print "Done training."
    is_collecting_new_pose = False
    logging.debug('new_pose_data:\n%s', new_pose_data)
    X = np.array(new_pose_data)
    logging.debug('X:\n%s', X)
    print 'number of Observations:', len(X)
    global model
    startprob = np.zeros(n_states)
    startprob[0] = 1
    transmat = hmm.normalize(np.random.rand(n_states, n_states), axis=1)
    model = hmm.GaussianHMM(n_components=n_states,
                            covariance_type="full",
                            startprob=startprob,
                            transmat=transmat)
    model.means_ = np.zeros((n_states,NUM_FEATURES))
    model.covars_ = np.tile(np.identity(NUM_FEATURES), (n_states, 1, 1))
    print model.fit([X])
    predictions = model.predict(X) 
    logging.info("Predictions:\n%s", list(predictions))
    predictions_set = set(predictions)
    logging.info("Set of predictions:\n%s", predictions_set)
    logging.info("Num distinct predictions:\n%s", len(predictions_set))

    # TODO keep track of regular states distribution

    global new_pose_states_dist
    new_pose_states_dist = get_distribution(predictions, new_poses_ranges)
    logging.info('new_pose_states_dist: %s', new_pose_states_dist)

def similarity(dict1, dict2):
    if len(dict1) > len(dict2):
        dict1, dict2 = dict2, dict1
    result = 0
    for k, v in dict1.iteritems():
        result += dict2.get(k, 0) * v
    return result

def detect_pose():
    while True:
        global is_collecting_new_pose
        global model
        is_collecting_new_pose = True
        sleep(1)
        is_collecting_new_pose = False
        X = np.array(new_pose_data)
        predictions = model.predict(X)
        logging.info("Predictions:\n%s", list(predictions))
        predictions_set = set(predictions)
        logging.info("Set of predictions:\n%s", predictions_set)
        logging.info("Num distinct predictions:\n%s", len(predictions_set))
        # print "score", model.score(X)
        # print "eval", model.eval(X)
        dist = get_distribution(predictions, [(0, len(predictions))])
        new_pose_score = similarity(dist, new_pose_states_dist)
        print 'new pose score:', new_pose_score

def main():
    try:
        hub = myo.Hub()
        hub.run(1000, Listener())
        print "Running..."
        training_thread = Thread(target=train_pose, name='Training_Thread')
        training_thread.start()
        training_thread.join()
        print "Done Training Thread."
        training_thread = Thread(target=detect_pose, name='Detecting_Thread')
        training_thread.start()
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
