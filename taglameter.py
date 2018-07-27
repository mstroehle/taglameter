import pyaudio
import numpy as np
import time
import os
#import matplotlib.pyplot as plt


def main(subID = ''):

    port = pyaudio.PyAudio()  # Opens a pyAudio streaming port
    

    print "\n    ---------------------------------------------------"
    print   "    | Welcome to the incredible TaboGladdoAudioMeter! |"
    print   "    ---------------------------------------------------\n\n"

    # Subject ID can be intered as an argument of this function. If not, 
    # the ID is requested via keyboard input
    if subID == '':
        subID = raw_input('Enter participants ID: ')
        if subID.lower() in ["falken", "stephen falken"]:
            print "Greetings, Professor Falken."

    # Calibration is triggered through the subject ID, we need to change this
    if subID.lower() == 'calibrateplease':
        calibrate(port)
        return()   

    print "Loading...."
    time.sleep(1)
    print "\n"

    chan = ['left', 'right']

    # Thresholding is done sequentially for each frequency in par['freq']
    for ichan in chan:
        par  = loadParameters(ichan)   # Loads the audiometer parameters
        threshold = np.zeros(len(par['freq']))
        for fIx, freq in enumerate(par['freq']):
            print 'Testing {} f = {:.0f}Hz'.format(ichan, freq)
            threshold[fIx] = measureThreshold(fIx, port, par, chan)
            print '---- done! Threshold {} at {:.1f} dB \n'.format(ichan, threshold[fIx])

    saveThresholds(threshold, subID, par, chan)
    port.terminate()

    # * Add plots of the thresholds here? It would be better to print the 
    # plots using plain text so that the audiometer can run completely 
    # without a window manager. Also: it would be fun to implement. <-- ToDo.

    raw_input('Press ENTER to exit...')



def saveThresholds(threshold, subID, par, chan):

    """ 
    Saves the hearing thresholds in a plain textfile.

    Inputs
        threshold : array with the measured thresholds (dB). Each value 
                    corresponds to a frequency value in par['freq']
        subID     : subject ID
        par       : dictionary with the parameters, check loadParameters()
    
    """


    header = "Audiometry for subject {}".format(subID)
    footer = "\n// Powered by the TaboGladdoAudioMeter!"
    headLine = "  |".join(["{:>7.0f}".format(f) for f in par['freq']])
    resLine  = "  |".join(["{:>7.1f}".format(t) for t in threshold])

    if chan == 'left':
        headLine = "Freq L (Hz)  |" + headLine
    else:
        headLine = "Freq R (Hz)  |" + headLine
    resLine  = "Thresh  (dB)  |" + resLine
    header   = header + "\n" + "-" * len(headLine) + "\n"
    footer   = "\n" + "-" * len(headLine) + "\n" + footer

    if not os.path.isdir('./out/'):
        os.makedirs('./out/')

    resFile = "./out/audioThresh-{}".format(subID)
    f = open(resFile, "w")
    f.write(header + headLine + "\n" + resLine + footer)
    f.close()

    print "Audiometry completed! Results saved to {}\n".format(resFile)
    print header + headLine + "\n" + resLine + footer
    print "\n\n"

    # * It would be cool to implement a function that automatically reads the 
    # textfile and stores the thresholds in an array or list. <-- ToDo.



def measureThreshold(fIx, port, par, chan):

    """ 
    Runs the algorithm to measure the hearing threshold of a given frequency.
    It uses the "up-5 down-10" technique. The process is repeated until
    participant responds to two out of three repetitions.

    Inputs
        fIx  : integer such that par['freq'][fIx] = tested frequency (Hz)
        port : pyAudio port to stream the sound
        par  : dictionary with the parameters, check loadParameters()
    
    Outputs 
        key  : key pressed, None if no key is pressed.
    """
    from collections import Counter

    freq     = par['freq'][fIx] # fIx : current frequency = par['freq'][lIx]
    lIx      = par['l0Ix']      # lIx : current loudness  = par['loud'][lIx]

    prev = True  # Flags if the sound was heared in the previous iteration
    last_spl = []  # Remember last SPL played.
    max_played = 0  

    # Need to test left and right channels separately.
    for chan in ['left', 'right']:
        while True:
            # Wait for a normally distributed amount of time
            time.sleep(par['avgT'] + par['sgmT'] * abs(np.random.randn()))
            print "     -> loudness = {:>5.1f}dB".format(par['loud'][lIx])
            # Return key press.
            key = playTone(freq, par['A0'][fIx][lIx], port, par, chan)
            print ""
            # Count number of SPL occurences.
            num_played = Counter(last_spl)
            if num_played:  # Check if not empty.
                max_played = num_played[max(num_played, key=num_played.get)]
            if key is not None:
                if prev:
                    if lIx != 0 and max_played < 3: # if loudness index is not at min level
                        lIx = max(0, lIx - 2) # two down, with saturation at 0
                        prev = True
                    else: # if loudness is at minimum, return minimum
                        return par['loud'][lIx]
                else:
                    return par['loud'][lIx]
            elif key is None:
                if max_played < 4:
                    lIx += 1 # one up
                else:
                   return par['loud'][lIx]
                   prev = False
            last_spl.append(lIx)



def playTone(f, a0, port, par, chan):

    """ 
    Plays a pure tone and waits for a key press through a limited amount of
    time. Sampling rate, duration, and waiting time are parameters stored in
    par.

    Inputs
        f    : pure tone frequency (Hz)
        a0   : waveform amplitude (0 < a0 < 1)
        port : pyAudio port to stream the sound
        par  : dictionary with the parameters, check loadParameters()
    
    Outputs 
        key  : key pressed, None if no key is pressed.
    """

    streamer = PyAudioStreamer(f, a0, par, chan)
    stream   = port.open(format          = pyaudio.paFloat32,
                         channels        = 2,
                         rate            = par['fs'],
                         output          = True, 
                         stream_callback = streamer.callback)

    stream.start_stream()
    key = listenKeyPress(par['dur'] + 2 * par['tau'] + par['wait'])   

    stream.stop_stream()
    stream.close()

    return(key)



def listenKeyPress(waitTime, terminateOnPress = False, verbose = True):

    """ 
    Listens keyboard keypress actions for a specified amount of time. 
    
    * Mouse inputs should be integrated here (nightmare alert!) <-- ToDo

    Inputs
        waitTime          : maximum waiting time (seconds)
        aterminateOnPress : function exits on key press if set to True
        verbosity         : verbose flag (True/False)
    
    Outputs 
        key               : first pressed key, None if no key is pressed
    """

    import termios, fcntl, sys, os
    fd = sys.stdin.fileno()

    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

    noKeyPresed = True
    key         = None
    startTime   = time.time()
    try:
        while (time.time() - startTime) < waitTime and noKeyPresed:
            try:
                key = sys.stdin.read()
                noKeyPresed = True
                if verbose:
                    print ' - response! (key pressed = {})'.format(key),
                break
            except IOError: pass
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)

    if not(terminateOnPress) and (time.time() - startTime) < waitTime:
        time.sleep(waitTime - time.time() + startTime)

    return(key)



def loadParameters(chan):

    """ 
    Returns the audiometer parameters. All frequencies and the initial 
    loudness must belong to the values stored in the calibration file.
    """

    # Audiometer parameters -- Feel free to mess around! :)
    par = {'dur'    : 1.1,   # tone duration including ramps (seconds)
           'fs'     : 44100, # sample rate Hz
           'tau'    : 0.05,  # ramps time windows
           'avgT'   : 1,     # average pause time between tones (seconds)
           'sgmT'   : 1,     # std of pause time between tones (seconds)
           'wait'   : 1,     # response waiting time after offset (seconds)
           'l0'     : 30,    # initial loudness for thresholding (dB SPL)
           'freq'   : [.25, .5, 1, 2, 4, 8, 12.5, 14], # kHz
           'calf' : '' # placeholder path to calibration file
           }

    # Choose calibration based on left and right channel.
    if chan == 'left':
        par['calf'] = './calibration_left.npz'
    else:
        par['calf'] = './calibration_right.npz'
            

    # Transforms --- touching this can be punished with death (by spoon!)
    par['freq'] = np.array(par['freq']) * 1000  

    calFile     = np.load(par['calf'])
    par['loud'] = calFile['LOUD']
    par['l0Ix'] = [ix for ix, loud in enumerate(par['loud']) 
                                                    if loud == par['l0']][0]
    par['A0']   = [calFile['A0'][ix] for ix in [ix 
                                      for ix, F in enumerate(calFile['FREQ']) 
                                      for f in par['freq'] if F==f]]

    if par['fs'] != calFile['FS']:
        print "WARNING! Sample rate set to {}Hz ".format(par['fs']),
        print "but calibration was performed at {}Hz".format(calFile['FS'])

    return par



class PyAudioStreamer:

    """ 
    Support class wrapping the callback function for pyAudio stream. 

    Inputs
        sound : sound waveform
    """

    def __init__(self, f, a0, par, chan):
        self.createTone(f, a0, par, chan)
        self.lastFrame = 0


    def callback(self, in_data, frame_count, time_info, status):

        """ 
        Callback method for pyAudio stream. Returns a chunk of the provided 
        sound. The sound must be provided when invoking the class Streamer.
        
        Inputs
            in_data     : arg required by pyAudio but not in use
            frame_count : chunk size (integer)
            time_info   : arg required by pyAudio but not in use
            status      : arg required by pyAudio but not in use
        
        Outputs 
            chunk       : excerpt of the sound waveform
            finished    : flag that marks if the sound waveform is deplected
        """

        prevFrame = self.lastFrame
        self.lastFrame = prevFrame + frame_count
        
        if self.lastFrame >= len(self.sound):
            finished = True
            self.lastFrame = len(self.sound)
        else:
            finished = False

        chunk = self.sound[prevFrame:self.lastFrame]

        return (chunk, finished)


    def createTone(self, f, a0, par, chan):

        """ 
        Creates a pure tone. 
        
        * It would be better to generate the tone online. <-- ToDo.

        Inputs
            f     : pure tone frequency (Hz)
            a0    : waveform amplitude (0 < a0 < 1)
            par   : dictionary specifyint the duration, sampling rate, and 
                    hamming window ramp/damp size; check loadParameters()
            chan  : 'left' or 'right' channel
        
        Outputs 
            sound : sound waveform
        """

        from struct import pack

        x     = np.linspace(0, par['dur'], int(par['dur'] * par['fs']));
        omega = 2 * np.pi * f
        sound = []
        sound = ''
        if chan == 'left':
            print('left')
            for ix in x:
                sound += pack('h', (a0 * np.sin(omega * ix)).astype(np.float32))
                sound += pack('h', (0 * np.sin(omega * ix)).astype(np.float32))
        elif chan == 'right':
            print('right')
            for ix in x:
                sound.append((0 * np.sin(omega * ix)).astype(np.float32))
                sound.append((a0 * np.sin(omega * ix)).astype(np.float32))

        if par['tau'] > 0:
            hL = int(par['tau'] * par['fs'])
            hw = np.hamming(2 * hL)
            sound[:hL ] = sound[:hL ] * hw[:hL]
            sound[-hL:] = sound[-hL:] * hw[hL:]

            sound = (np.concatenate((np.zeros((hL,)), 
                                     sound, 
                                     np.zeros((hL,))))).astype(np.float32)

        self.sound = sound

        
if __name__ == "__main__":
    
    main()

