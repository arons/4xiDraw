#!/usr/bin/env python 
"""
Modified by Jay Johnson 2015, J Tech Photonics, Inc., jtechphotonics.com 
modified by Adam Polak 2014, polakiumengineering.org

based on Copyright (C) 2009 Nick Drobchenko, nick@cnc-club.ru
based on gcode.py (C) 2007 hugomatic... 
based on addnodes.py (C) 2005,2007 Aaron Spike, aaron@ekips.org
based on dots.py (C) 2005 Aaron Spike, aaron@ekips.org
based on interp.py (C) 2005 Aaron Spike, aaron@ekips.org
based on bezmisc.py (C) 2005 Aaron Spike, aaron@ekips.org
based on cubicsuperpath.py (C) 2005 Aaron Spike, aaron@ekips.org

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
import inkex, simplestyle, simplepath
import cubicsuperpath, simpletransform, bezmisc

import os
import math
import bezmisc
import re
import copy
import sys
import time
import cmath
import numpy
import codecs
import random
import gettext
_ = gettext.gettext

options = {}
 
### Check if inkex has errormsg (0.46 version doesnot have one.) Could be removed later.
if "errormsg" not in dir(inkex):
    inkex.errormsg = lambda msg: sys.stderr.write((unicode(msg) + "\n").encode("UTF-8"))


################################################################################
###        print_ prints any arguments into specified log file
################################################################################
def print_(*arg):
    f = open("test.log","a")
    for s in arg :
        s = str(unicode(s).encode('unicode_escape'))+" "
        f.write( s )
    f.write("\n")
    f.close()


################################################################################
###
###        Gcodetools class
###
################################################################################
class laser_gcode(inkex.Effect):
    
    
    def __init__(self):
        inkex.Effect.__init__(self)
        self.OptionParser.add_option("",   "--unit",                            action="store", type="string",          dest="unit",                                default="G21 (All units in mm)",        help="Units either mm or inches")
               
################################################################################
###        Errors handling function, notes are just printed into Logfile, 
###        warnings are printed into log file and warning message is displayed but
###        extension continues working, errors causes log and execution is halted
###        Notes, warnings adn errors could be assigned to space or comma or dot 
###        sepparated strings (case is ignoreg).
################################################################################
    def error(self, s, type_= "Warning"):
        notes = "Note "
        warnings = """
                        Warning tools_warning
                        bad_orientation_points_in_some_layers
                        more_than_one_orientation_point_groups
                        more_than_one_tool
                        orientation_have_not_been_defined
                        tool_have_not_been_defined
                        selection_does_not_contain_paths
                        selection_does_not_contain_paths_will_take_all
                        selection_is_empty_will_comupe_drawing
                        selection_contains_objects_that_are_not_paths
                        """
        errors = """
                        Error     
                        wrong_orientation_points    
                        area_tools_diameter_error
                        no_tool_error
                        active_layer_already_has_tool
                        active_layer_already_has_orientation_points
                    """
        if type_.lower() in re.split("[\s\n,\.]+", errors.lower()) :
            print_(s)
            inkex.errormsg(s+"\n")        
            sys.exit()
        elif type_.lower() in re.split("[\s\n,\.]+", warnings.lower()) :
            print_(s)
        elif type_.lower() in re.split("[\s\n,\.]+", notes.lower()) :
            print_(s)
        else :
            print_(s)
            inkex.errormsg(s)        
            sys.exit()
    
    



################################################################################
###
###        Get Gcodetools info from the svg
###
################################################################################
    def get_info(self):
        self.selected_paths = {}
        self.paths = {}        
        self.orientation_points = {}
        self.layers = [self.document.getroot()]
        self.Zcoordinates = {}
        self.transform_matrix = {}
        self.transform_matrix_reverse = {}
        self.Zauto_scale = {}
        
        def recursive_search(g, layer, selected=False):
            items = g.getchildren()
            items.reverse()
            for i in items:
                if selected:
                    self.selected[i.get("id")] = i
                if i.tag == inkex.addNS("g",'svg') and i.get(inkex.addNS('groupmode','inkscape')) == 'layer':
                    self.layers += [i]
                    recursive_search(i,i)
                elif i.get('gcodetools') == "Gcodetools orientation group" :
                    points = self.get_orientation_points(i)
                    if points != None :
                        self.orientation_points[layer] = self.orientation_points[layer]+[points[:]] if layer in self.orientation_points else [points[:]]
                        print_("Found orientation points in '%s' layer: %s" % (layer.get(inkex.addNS('label','inkscape')), points))
                    else :
                        self.error(_("Warning! Found bad orientation points in '%s' layer. Resulting Gcode could be corrupt!") % layer.get(inkex.addNS('label','inkscape')), "bad_orientation_points_in_some_layers")
                elif i.tag == inkex.addNS('path','svg'):
                    if "gcodetools"  not in i.keys() :
                        self.paths[layer] = self.paths[layer] + [i] if layer in self.paths else [i]  
                        if i.get("id") in self.selected :
                            self.selected_paths[layer] = self.selected_paths[layer] + [i] if layer in self.selected_paths else [i]  
                elif i.tag == inkex.addNS("g",'svg'):
                    recursive_search(i,layer, (i.get("id") in self.selected) )
                elif i.get("id") in self.selected :
                    self.error(_("This extension works with Paths and Dynamic Offsets and groups of them only! All other objects will be ignored!\nSolution 1: press Path->Object to path or Shift+Ctrl+C.\nSolution 2: Path->Dynamic offset or Ctrl+J.\nSolution 3: export all contours to PostScript level 2 (File->Save As->.ps) and File->Import this file."),"selection_contains_objects_that_are_not_paths")
                
                    
        recursive_search(self.document.getroot(),self.document.getroot())

    def get_transforms(self,g):
        root = self.document.getroot()
        trans = []
        while (g!=root):
            if 'transform' in g.keys():
                t = g.get('transform')
                t = simpletransform.parseTransform(t)
                trans = simpletransform.composeTransform(t,trans) if trans != [] else t
                print_(trans)
            g=g.getparent()
        return trans 
    
    def apply_transforms(self,g,csp):
        trans = self.get_transforms(g)
        if trans != []:
            simpletransform.applyTransformToPath(trans, csp)
        return csp
################################################################################
###
###        Orientation
###
################################################################################	                
    def get_orientation_points(self,g):
        self.logDebug("entering get_orientation_points")
        items = g.getchildren()
        items.reverse()
        p2, p3 = [], []
        p = None
        for i in items:
            if i.tag == inkex.addNS("g",'svg') and i.get("gcodetools") == "Gcodetools orientation point (2 points)":
                p2 += [i]
            if i.tag == inkex.addNS("g",'svg') and i.get("gcodetools") == "Gcodetools orientation point (3 points)":
                p3 += [i]
        if len(p2)==2 : p=p2 
        elif len(p3)==3 : p=p3 
        if p==None : return None
        points = []
        for i in p :    
            point = [[],[]]    
            for  node in i :
                if node.get('gcodetools') == "Gcodetools orientation point arrow":
                    point[0] = self.apply_transforms(node,cubicsuperpath.parsePath(node.get("d")))[0][0][1]
                if node.get('gcodetools') == "Gcodetools orientation point text":
                    self.logDebug("node.text:"+node.text)
                    r = re.match(r'(?i)\s*\(\s*(-?\s*\d*(?:,|\.)*\d*)\s*;\s*(-?\s*\d*(?:,|\.)*\d*)\s*;\s*(-?\s*\d*(?:,|\.)*\d*)\s*\)\s*',node.text)
                    point[1] = [float(r.group(1)),float(r.group(2)),float(r.group(3))]
            if point[0]!=[] and point[1]!=[]:    points += [point]
        if len(points)==len(p2)==2 or len(points)==len(p3)==3 : return points
        else : return None





################################################################################
###
###        Orientation
###
################################################################################
    def orientation(self, layer=None) :
        print_("entering orientations")
        if layer == None :
            layer = self.current_layer if self.current_layer is not None else self.document.getroot()
        if layer in self.orientation_points:
            self.error(_("Active layer already has orientation points! Remove them or select another layer!"),"active_layer_already_has_orientation_points")
        
        orientation_group = inkex.etree.SubElement(layer, inkex.addNS('g','svg'), {"gcodetools":"Gcodetools orientation group"})

        # translate == ['0', '-917.7043']
        if layer.get("transform") != None :
            translate = layer.get("transform").replace("translate(", "").replace(")", "").split(",")
        else :
            translate = [0,0]

        # doc height in pixels (38 mm == 134.64566px)
        doc_height = self.unittouu(self.document.getroot().xpath('@height', namespaces=inkex.NSS)[0])

        if self.document.getroot().get('height') == "100%" :
            doc_height = 1052.3622047
            print_("Overruding height from 100 percents to %s" % doc_height)
            
        print_("Document height: " + str(doc_height));
            
        if self.options.unit == "G21 (All units in mm)" : 
            points = [[0.,0.,0.],[100.,0.,0.],[0.,100.,0.]]
            orientation_scale = 3.5433070660
            print_("orientation_scale < 0 ===> switching to mm units=%0.10f"%orientation_scale )
        elif self.options.unit == "G20 (All units in inches)" :
            points = [[0.,0.,0.],[5.,0.,0.],[0.,5.,0.]]
            orientation_scale = 90
            print_("orientation_scale < 0 ===> switching to inches units=%0.10f"%orientation_scale )

        points = points[:2]

        print_(("using orientation scale",orientation_scale,"i=",points))
        for i in points :
            # X == Correct!
            # si == x,y coordinate in px
            # si have correct coordinates
            # if layer have any tranform it will be in translate so lets add that
            si = [i[0]*orientation_scale, (i[1]*orientation_scale)+float(translate[1])]
            g = inkex.etree.SubElement(orientation_group, inkex.addNS('g','svg'), {'gcodetools': "Gcodetools orientation point (2 points)"})
            inkex.etree.SubElement(    g, inkex.addNS('path','svg'), 
                {
                    'style':    "stroke:none;fill:#000000;",     
                    'd':'m %s,%s 2.9375,-6.343750000001 0.8125,1.90625 6.843748640396,-6.84374864039 0,0 0.6875,0.6875 -6.84375,6.84375 1.90625,0.812500000001 z z' % (si[0], -si[1]+doc_height),
                    'gcodetools': "Gcodetools orientation point arrow"
                })
            t = inkex.etree.SubElement(    g, inkex.addNS('text','svg'), 
                {
                    'style':    "font-size:10px;font-style:normal;font-variant:normal;font-weight:normal;font-stretch:normal;fill:#000000;fill-opacity:1;stroke:none;",
                    inkex.addNS("space","xml"):"preserve",
                    'x':    str(si[0]+10),
                    'y':    str(-si[1]-10+doc_height),
                    'gcodetools': "Gcodetools orientation point text"
                })
            t.text = "(%s; %s; %s)" % (i[0],i[1],i[2])
################################################################################
### Log
################################################################################
    def logDebug(self,msg):
                try:
                        with open("4xidraw-orientation-debug.log", "a") as myfile:
                                myfile.write('%s\n' % msg)
                except:
	                 print_("Error logging debug data.")             
################################################################################
###
###        Effect
###
###        Main entry point
###
################################################################################
    def effect(self) :
        global options
        options = self.options
        options.self = self
        options.doc_root = self.document.getroot()

        # define print_ function 
        global print_
        
        self.logDebug("test orientation")
        self.get_info()
        if self.orientation_points == {} :
            self.logDebug("add orientation")
            self.error(_("Orientation points have not been defined! A default set of orientation points has been automatically added."),"warning")
            self.orientation( self.layers[min(0,len(self.layers)-1)] )        
            self.get_info()

    
e = laser_gcode()
e.affect()     