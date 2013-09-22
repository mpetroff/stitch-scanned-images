#!/usr/bin/env python3

#  ______     ______   __     ______   ______     __  __                       
# /\  ___\   /\__  _\ /\ \   /\__  _\ /\  ___\   /\ \_\ \                      
# \ \___  \  \/_/\ \/ \ \ \  \/_/\ \/ \ \ \____  \ \  __ \                     
#  \/\_____\    \ \_\  \ \_\    \ \_\  \ \_____\  \ \_\ \_\                    
#   \/_____/     \/_/   \/_/     \/_/   \/_____/   \/_/\/_/                    
#                                                                              
#  ______     ______     ______     __   __     __   __     ______     _____   
# /\  ___\   /\  ___\   /\  __ \   /\ "-.\ \   /\ "-.\ \   /\  ___\   /\  __-. 
# \ \___  \  \ \ \____  \ \  __ \  \ \ \-.  \  \ \ \-.  \  \ \  __\   \ \ \/\ \
#  \/\_____\  \ \_____\  \ \_\ \_\  \ \_\\"\_\  \ \_\\"\_\  \ \_____\  \ \____-
#   \/_____/   \/_____/   \/_/\/_/   \/_/ \/_/   \/_/ \/_/   \/_____/   \/____/
#                                                                              
#  __     __    __     ______     ______     ______     ______                 
# /\ \   /\ "-./  \   /\  __ \   /\  ___\   /\  ___\   /\  ___\                
# \ \ \  \ \ \-./\ \  \ \  __ \  \ \ \__ \  \ \  __\   \ \___  \               
#  \ \_\  \ \_\ \ \_\  \ \_\ \_\  \ \_____\  \ \_____\  \/\_____\              
#   \/_/   \/_/  \/_/   \/_/\/_/   \/_____/   \/_____/   \/_____/              
#                                                                              
# Stitch Scanned Images
# Copyright (c) 2013 Matthew Petroff
# 
# Dependencies: autooptimiser, convert, cpclean, cpfind, enblend, nona,
#               pto_gen, pano_modify, pano_trafo, pto_var
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import argparse
import subprocess
import glob
import tempfile
import os

# Parse input
parser = argparse.ArgumentParser(description='Stitch scanned segments.')
parser.add_argument('inputFiles', metavar='N', nargs='+',
                    help='files to be stitched')
parser.add_argument('-o', '--output', dest='output', default='output.jpg',
                    help='output name (default: output.jpg)')
args = parser.parse_args()

# Allow glob syntax cross-platform
inputFiles = []
for i in args.inputFiles:
    inputFiles += glob.glob(i)

# Make temporary directory
tmpDir = tempfile.TemporaryDirectory()
tmp = tmpDir.name

# Make pto file
ptoFile = args.output.split('.')[0] + '.pto'
subprocess.call(['pto_gen', '-o', ptoFile] + inputFiles)

# Find control points
subprocess.call(['cpfind', '--fullscale', '--multirow', '--sieve1size', '500',
                 '--sieve2width', '20', '--sieve2height', '20', '-o', ptoFile,
                 ptoFile])

# Set image parameters to optimize
subprocess.call(['pto_var', '--opt', 'r,TrX,TrY', '-o', ptoFile, ptoFile])

# Remove incorrect control points
subprocess.call(['cpclean', '-n', '1', '-o', ptoFile, ptoFile])
subprocess.call(['cpclean', '-o', ptoFile, ptoFile])

# Optimize rotation and x,y translation
subprocess.call(['autooptimiser', '-n', '-o', ptoFile, ptoFile])

# Morph images to fit control points
imgCtrlPts = ''
with open(ptoFile) as input:
    for line in input:
        if line[0] == 'c':
            img1 = line.split('n')[1].split()[0]
            img2 = line.split('N')[1].split()[0]
            x1 = line.split('x')[1].split()[0]
            x2 = line.split('X')[1].split()[0]
            y1 = line.split('y')[1].split()[0]
            y2 = line.split('Y')[1].split()[0]
            imgCtrlPts += img1 + ' ' + x1 + ' ' + y1 + '\n' \
                        + img2 + ' ' + x2 + ' ' + y2 + '\n'
pipe = subprocess.Popen(['pano_trafo', ptoFile], stdout=subprocess.PIPE,
                        stdin=subprocess.PIPE)
trafoOut = (pipe.communicate(input
                             = imgCtrlPts.encode('utf-8'))[0]).decode('utf-8')
splitImgCtrlPts = imgCtrlPts.splitlines()
splitTrafoOut = trafoOut.splitlines()
morphedSplitTrafoOut = [''] * len(splitTrafoOut)
for i in range(0, int(len(splitTrafoOut) / 2)):
    i1 = splitImgCtrlPts[i*2].split()[0]
    i2 = splitImgCtrlPts[i*2+1].split()[0]
    x = (float(splitTrafoOut[i*2].split()[0]) \
        + float(splitTrafoOut[i*2+1].split()[0])) / 2
    y = (float(splitTrafoOut[i*2].split()[1]) \
        + float(splitTrafoOut[i*2+1].split()[1])) / 2
    morphedSplitTrafoOut[i*2] = i1 + ' ' + str(x) + ' ' + str(y)
    morphedSplitTrafoOut[i*2+1] = i2 + ' ' + str(x) + ' ' + str(y)
trafoRin = "\n".join(morphedSplitTrafoOut)
pipe = subprocess.Popen(['pano_trafo', '-r', ptoFile], stdout=subprocess.PIPE,
                        stdin=subprocess.PIPE)
trafoRout = (pipe.communicate(input
                              = trafoRin.encode('utf-8'))[0]).decode('utf-8')
splitTrafoRout = trafoRout.splitlines()
ctrlPts = [''] * len(inputFiles)
for i in range(0, len(splitTrafoRout)):
    ctrlPts[int(splitImgCtrlPts[i].split()[0])] \
        += splitImgCtrlPts[i].split()[1] + ',' \
        + splitImgCtrlPts[i].split()[2] \
        + ' ' + splitTrafoRout[i].split()[0] + ',' \
        + splitTrafoRout[i].split()[1] + ' '
ptoOpt = open(ptoFile, 'r', encoding='utf-8').read()
for i in range(0, len(inputFiles)):
    print('morphing image: ' + str(i))
    subprocess.call(['convert', inputFiles[i], '-compress', 'LZW', '-distort',
                     'Shepards', ctrlPts[i],
                     tmp + os.sep + 'm' + str(i) + '.tif'])
    ptoOpt = ptoOpt.replace(inputFiles[i], tmp + '/m' + str(i) + '.tif')
open(ptoFile, 'w', encoding='utf-8').write(ptoOpt)

# Stitch images
subprocess.call(['pano_modify', '-p', '0', '--fov=AUTO', '--canvas=AUTO',
                 '--crop=AUTO', '-o', ptoFile, ptoFile])
subprocess.call(['nona', '-o', tmp + os.sep + 'remapped', ptoFile])
subprocess.call(['enblend', '--primary-seam-generator=graph-cut', '-o',
                 args.output.split('.')[0] + '.tif']
                 + glob.glob(tmp + os.sep + 'remapped*'))
