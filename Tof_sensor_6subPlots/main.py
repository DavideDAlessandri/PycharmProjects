#!/usr/bin/env python

from threading import Thread
import serial
import time
import collections
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import struct
import copy
import logging

limit = 1000    # set sensor max output
log = False     # enable log data
obj = False     # print object detection
plt_err = False  # if true print the corrected error values instead !!!not working!!!
array_dimension = 6
saved_data = [0]*array_dimension  # create an array with old received values

if log:
    logging.basicConfig(filename='value.log', level=logging.INFO, format='%(message)s')
    name_array = str(['Sensor 1', 'Sensor 2', 'Sensor 3', 'Sensor 4', 'Sensor 5',
                      'Sensor 6'])[1:-1]
    logging.info(name_array)  # to log output values

class serialPlot:
    def __init__(self, serialPort='/dev/ttyUSB0', serialBaud=38400, plotLength=100, dataNumBytes=2, numPlots=1):
        self.port = serialPort
        self.baud = serialBaud
        self.plotMaxLength = plotLength
        self.dataNumBytes = dataNumBytes
        self.numPlots = numPlots
        self.rawData = bytearray(numPlots * dataNumBytes)
        self.dataType = None
        if dataNumBytes == 2:
            self.dataType = 'h'     # 2 byte integer
        elif dataNumBytes == 4:
            self.dataType = 'f'     # 4 byte float
        self.data = []
        self.privateData = None     # for storing a copy of the data so all plots are synchronized
        for i in range(numPlots):   # give an array for each type of data and store them in a list
            self.data.append(collections.deque([0] * plotLength, maxlen=plotLength))
        self.isRun = True
        self.isReceiving = False
        self.thread = None
        self.plotTimer = 0
        self.previousTimer = 0

        print('Trying to connect to: ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        try:
            self.serialConnection = serial.Serial(serialPort, serialBaud, timeout=4)
            print('Connected to ' + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')
        except:
            print("Failed to connect with " + str(serialPort) + ' at ' + str(serialBaud) + ' BAUD.')

    def readSerialStart(self):
        if self.thread == None:
            self.thread = Thread(target=self.backgroundThread)
            self.thread.start()
            # Block till we start receiving values
            while self.isReceiving != True:
                time.sleep(0.1)

    def getSerialData(self, frame, lines, lineLabel, pltNumber):
        if pltNumber == 0:  # in order to make all the clocks show the same reading
            currentTimer = time.perf_counter()
            self.plotTimer = int((currentTimer - self.previousTimer) * 1000)     # the first reading will be erroneous
            self.previousTimer = currentTimer
        self.privateData = copy.deepcopy(self.rawData)    # so that the 3 values in our plots will be synchronized to the same sample time
        data = self.privateData[(pltNumber*self.dataNumBytes):(self.dataNumBytes + pltNumber*self.dataNumBytes)]
        value,  = struct.unpack(self.dataType, data)
        value_array = []
        if value > limit:
            value = limit
        value_array.append(value)

        min_value = min(value_array)
        if plt_err:
            saved_data.append(min_value)  # add last value to array
            saved_data.pop(0)  # remove first value of array
            saved_value = 0
            for x in range(array_dimension):
                saved_value = saved_value + saved_data[x]
            if saved_data[0] * array_dimension - saved_value == 0:  # if we measure the same values the sensor is stuck
                min_value = limit

        self.data[pltNumber].append(value)    # we get the latest data point and append it to our array
        lines.set_data(range(self.plotMaxLength), self.data[pltNumber])

        if obj:
            if min_value >= 300:
                print(0)
            elif 150 < min_value < 300:
                print("Object detected")
            elif 50 < min_value < 150:
                print("Slow")
            elif min_value < 50:
                print("Stop")

        if log:
            saved_data[pltNumber] = min_value
            # print(saved_data)
            new_value_array = str(saved_data)[1:-1]  # crate array without bracket
            logging.info(new_value_array)  # to log output values

    def backgroundThread(self):    # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        while (self.isRun):
            self.serialConnection.readinto(self.rawData)
            self.isReceiving = True

    def close(self):
        self.isRun = False
        self.thread.join()
        self.serialConnection.close()
        print('Disconnected...')


def makeFigure(xLimit, yLimit, title):
    xmin, xmax = xLimit
    ymin, ymax = yLimit
    fig = plt.figure()
    ax = plt.axes(xlim=(xmin, xmax), ylim=(int(ymin - (ymax - ymin) / 10), int(ymax + (ymax - ymin) / 10)))
    ax.set_title(title)
    ax.set_xlabel("Time")
    ax.set_ylabel("Distance")
    return fig, ax


def conv_num_x(argument):
    switcher = {
        0: 0,
        1: 1,
        2: 2,
        3: 0,
        4: 1,
        5: 2,
    }
    return switcher.get(argument, 0)


def conv_num_y(argument):
    switcher = {
        0: 0,
        1: 0,
        2: 0,
        3: 1,
        4: 1,
        5: 1,
    }
    return switcher.get(argument, 0)


def main():
    portName = 'COM10'
    baudRate = 115200
    maxPlotLength = 100  # number of points in x-axis of real time plot
    dataNumBytes = 2  # number of bytes of 1 data point
    numPlots = 6  # number of plots in 1 graph
    s = serialPlot(portName, baudRate, maxPlotLength, dataNumBytes, numPlots)   # initializes all required variables
    s.readSerialStart()                                               # starts background thread

    # plotting starts below
    pltInterval = 15    # Period at which the plot animation updates [ms]
    lineLabelText = ['Sensor 1', 'Sensor 2', 'Sensor 3','Sensor 4', 'Sensor 5', 'Sensor 6']
    style = ['r-', 'g-', 'b-', 'c-', 'm-', 'y-']    # linestyles for the different plots
    anim = []
    fig, ax = plt.subplots(3, 2)
    fig.set_figheight(8.5)
    fig.set_figwidth(13)
    ax[2, 0].set_xlabel("Time")
    ax[2, 1].set_xlabel("Time")
    ax[0, 0].set_ylabel("Distance")
    ax[1, 0].set_ylabel("Distance")
    ax[2, 0].set_ylabel("Distance")

    for i in range(numPlots):
        argument = i
        ax[conv_num_x(argument), conv_num_y(argument)].set_xlim([0, maxPlotLength])
        ax[conv_num_x(argument), conv_num_y(argument)].set_ylim([-1, limit + 100])
        ax[conv_num_x(argument), conv_num_y(argument)].set_title(lineLabelText[i])
        lines = ax[conv_num_x(argument), conv_num_y(argument)].plot([], [], style[i])[0]
        anim.append(animation.FuncAnimation(fig, s.getSerialData, fargs=(lines,  lineLabelText[i], i), interval=pltInterval))  # fargs has to be a tuple
    plt.show()

    s.close()


if __name__ == '__main__':
    main()