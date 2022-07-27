#!/usr/bin/env python
import logging
from threading import Thread
import serial
import time
import collections
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import struct
import copy
import pandas as pd

limit = 400     # set sensor max output
log = False     # enable log data
obj = True      # print object detection
plt_min = True  # if true print the min value instead
array_dimension = 15    # create an array with old received values

saved_data_1 = [0]*array_dimension
saved_data_2 = [0]*array_dimension
saved_data_3 = [0]*array_dimension

if log:
    logging.basicConfig(filename='value.log', level=logging.INFO, format='%(message)s')
    name_array = str(['Sensor 1', 'Sensor 2', 'Sensor 3', 'Sensor 1 corrected', 'Sensor 2 corrected',
                      'Sensor 3 corrected', 'Min. value original', 'Min value correct'])[1:-1]
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
        for i in range(numPlots):   # give an array for each type of data and store them in a list
            self.data.append(collections.deque([0] * plotLength, maxlen=plotLength))
        self.isRun = True
        self.isReceiving = False
        self.thread = None
        self.plotTimer = 0
        self.previousTimer = 0
        # self.csvData = []

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

    def getSerialData(self, frame, lines, lineValueText, lineLabel, timeText):
        currentTimer = time.perf_counter()
        self.plotTimer = int((currentTimer - self.previousTimer) * 1000)     # the first reading will be erroneous
        self.previousTimer = currentTimer
        timeText.set_text('Plot Interval = ' + str(self.plotTimer) + 'ms')
        privateData = copy.deepcopy(self.rawData[:])    # so that the 3 values in our plots will be synchronized to the same sample time
        value_array = []
        for i in range(self.numPlots):
            data = privateData[(i*self.dataNumBytes):(self.dataNumBytes + i*self.dataNumBytes)]
            value,  = struct.unpack('h', data)  # self.dataType

            if value > limit:
                value = limit
            value_array.append(value)

            if not plt_min:
                self.data[i].append(value)  # we get the latest data point and append it to our array
                lines[i].set_data(range(self.plotMaxLength), self.data[i])
                lineValueText[i].set_text('[' + lineLabel[i] + '] = ' + str(value))

        min_value_original = min(value_array)
        saved_data_1.append(value_array[0])       # add last value to array
        saved_data_1.pop(0)                  # remove first value of array
        saved_data_2.append(value_array[1])  # add last value to array
        saved_data_2.pop(0)  # remove first value of array
        saved_data_3.append(value_array[2])  # add last value to array
        saved_data_3.pop(0)  # remove first value of array
        log_array = []
        for x in range(3):
            log_array.append(value_array[x])

        saved_value_1 = 0
        for x in range(array_dimension):
            saved_value_1 = saved_value_1 + saved_data_1[x]
        if saved_data_1[0]*array_dimension-saved_value_1 == 0:      # if we measure the same values the sensor is stuck
            value_array[0] = limit
        saved_value_2 = 0
        for x in range(array_dimension):
            saved_value_2 = saved_value_2 + saved_data_2[x]
        if saved_data_2[0] * array_dimension - saved_value_2 == 0:  # if we measure the same values the sensor is stuck
            value_array[1] = limit
        saved_value_3 = 0
        for x in range(array_dimension):
            saved_value_3 = saved_value_3 + saved_data_3[x]
        if saved_data_3[0] * array_dimension - saved_value_3 == 0:  # if we measure the same values the sensor is stuck
            value_array[2] = limit
        min_value = min(value_array)

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
            for x in range(3):
                log_array.append(value_array[x])
            log_array.append(min_value_original)
            log_array.append(min_value)
            new_value_array = str(log_array)[1:-1]  # crate array without bracket
            logging.info(new_value_array)  # to log output values

        if plt_min:
            plt_min_array = []
            plt_min_array.append(min_value_original)
            plt_min_array.append(min_value)
            plt_min_array.append(-1)
            for i in range(self.numPlots):
                self.data[i].append(plt_min_array[i])  # we get the latest data point and append it to our array
                lines[i].set_data(range(self.plotMaxLength), self.data[i])
                lineValueText[i].set_text('[' + lineLabel[i] + '] = ' + str(plt_min_array[i]))

    def backgroundThread(self):    # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        while (self.isRun):
            self.serialConnection.readinto(self.rawData)
            self.isReceiving = True
            #print(self.rawData)

    def close(self):
        self.isRun = False
        self.thread.join()
        self.serialConnection.close()
        print('Disconnected...')
        # df = pd.DataFrame(self.csvData)
        # df.to_csv('/home/rikisenia/Desktop/data.csv')


def main():
    portName = 'COM7'
    baudRate = 115200
    maxPlotLength = 100     # number of points in x-axis of real time plot
    dataNumBytes = 2        # number of bytes of 1 data point
    numPlots = 3            # number of plots in 1 graph
    s = serialPlot(portName, baudRate, maxPlotLength, dataNumBytes, numPlots)   # initializes all required variables
    s.readSerialStart()                                               # starts background thread

    # plotting starts below
    pltInterval = 50    # Period at which the plot animation updates [ms]
    xmin = 0
    xmax = maxPlotLength
    ymin = -(1)
    ymax = limit + 200
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(xlim=(xmin, xmax), ylim=(float(ymin - (ymax - ymin) / 10), float(ymax + (ymax - ymin) / 10)))
    ax.set_title('Tof Sensors')
    ax.set_xlabel("Time")
    ax.set_ylabel("Distance")

    if plt_min:
        lineLabel = ['Min. value', 'Min value corrected', '-']
    else:
        lineLabel = ['Sensor 1', 'Sensor 2', 'Sensor 3']
    if plt_min:
        style = ['#FFF157', 'r-', 'w-']  # linestyles for the different plots
    else:
        style = ['r-', 'c-', 'b-']  # linestyles for the different plots

    timeText = ax.text(0.70, 0.95, '', transform=ax.transAxes)
    lines = []
    lineValueText = []

    for i in range(numPlots):
        lines.append(ax.plot([], [], style[i], label=lineLabel[i])[0])
        lineValueText.append(ax.text(0.70, 0.90-i*0.05, '', transform=ax.transAxes))
    anim = animation.FuncAnimation(fig, s.getSerialData, fargs=(lines, lineValueText, lineLabel, timeText), interval=pltInterval)    # fargs has to be a tuple

    plt.legend(loc="upper left")
    plt.show()

    s.close()


if __name__ == '__main__':
    main()