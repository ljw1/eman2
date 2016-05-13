#!/usr/bin/env python
#
# Author: Toshio Moriya, 11/11/2015 (toshio.moriya@mpi-dortmund.mpg.de)
#
# This software is issued under a joint BSD/GNU license. You may use the
# source code in this file under either license. However, note that the
# complete EMAN2 and SPHIRE software packages have some GPL dependencies,
# so you are responsible for compliance with the licenses of these packages
# if you opt to use BSD licensing. The warranty disclaimer below holds
# in either instance.
#
# This complete copyright notice must be included in any revised version of the
# source code. Additional authorship citations may be added, but existing
# author citations must be preserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#

import sys
import os
from subprocess import *
from functools import partial  # Use to connect event-source widget and event handler
from PyQt4.Qt import *
from PyQt4 import QtGui
from PyQt4 import QtCore
from EMAN2 import *
from EMAN2_cppwrap import *
from global_def import *
from sparx import *

# ========================================================================================
# Inherited by SXcmd_category and SXconst_set
# SXMainWindow use this class to handle events from menu item buttons
class SXmenu_item(object):
	def __init__(self, name = "", label = "", short_info = ""):
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		self.name = name              # Name of this menu item, used as a key of dictionary
		self.label = label            # User friendly name of this menu item
		self.short_info = short_info  # Short description of this menu item
		self.btn = None               # <Used only in sxgui.py> QPushButton button instance associating with this menu item
		self.widget = None            # <Used only in sxgui.py> SXCmdWidget instance associating with this menu item
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><

# ========================================================================================
class SXcmd_token(object):
	def __init__(self):
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		self.key_base = ""           # key base name of command token (argument or option) in command line
		self.key_prefix = ""         # key prefix of of command token. None for argument, "--" or "-" for option
		self.label = ""              # User friendly name of argument or option
		self.help = ""               # Help info
		self.group = ""              # Tab group: main or advanced
		self.is_required = False     # Required argument or options. No default value are available 
		self.default = ""            # Default value
		self.type = ""               # Type of value
		self.restore = ""            # Restore value
		self.is_in_io = False        # <Used only in wikiparser.py> To check consistency between "usage in command line" and list in "== Input ==" and "== Output ==" sections
		self.restore_widget = None   # <Used only in sxgui.py> Restore widget instance associating with this command token
		self.widget = None           # <Used only in sxgui.py> Widget instance associating with this command token
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		
	def initialize_edit(self, key_base):
		self.key_base = key_base
		self.key_prefix = None
		self.label = None
		self.help = None
		self.group = None
		self.is_required = None
		self.default = None
		self.type = None

# ========================================================================================
class SXcmd(object):
	def __init__(self, category = "", role = "", is_submittable = True):
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		self.name = ""                        # Name of this command (i.e. name of sx*.py script but without .py extension), used for generating command line
		self.mode = ""                        # key base name of a command token, defining mode/subset of this command. For fullset command, use empty string
		self.label = ""                       # User friendly name of this command
		self.short_info = ""                  # Short description of this command
		self.mpi_support = False              # Flag to indicate if this command suppors MPI version
		self.mpi_add_flag = False             # DESIGN_NOTE: 2015/11/12 Toshio Moriya. This can be removed when --MPI flag is removed from all sx*.py scripts 
		self.category = category              # Category of this command: sxc_movie_micrograph, sxc_ctf, sxc_particle_stack, sxc_2d_clustering, sxc_initial_3d_modeling, sxc_3d_refinement, sxc_3d_clustering, sxc_utilities
		self.role = role                      # Role of this command; sxr_pipe (pipeline), sxr_alt (alternative) sxr_util (utility)
		self.is_submittable = is_submittable  # External GUI Application (e.g. sxgui_cter.py) should not be submitted to job queue
		self.token_list = []                  # list of command tokens. Need this to keep the order of command tokens
		self.token_dict = {}                  # dictionary of command tokens, organised by key base name of command token. Easy to access a command token but looses their order
		self.btn = None                       # <Used only in sxgui.py> QPushButton button instance associating with this command
		self.widget = None                    # <Used only in sxgui.py> SXCmdWidget instance associating with this command
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		
	def get_mode_name_for(self, target_name):
		mode_name = self.name
		if self.mode != "":
			if target_name in ["file_path"]:
				mode_name = "%s_%s" % (self.name, self.mode)
			elif target_name in ["human"]:
				mode_name = "%s %s%s" % (self.name, self.token_dict[self.mode].key_prefix, self.mode)
				
		return mode_name
	
	def get_category_dir_path(self, parent_dir_path = ""):
		category_dir_path = self.category.replace("sxc_", "")
		if parent_dir_path != "":
			category_dir_path = os.path.join(parent_dir_path, category_dir_path)
		
		return category_dir_path
		
# ========================================================================================
class SXcmd_category(SXmenu_item):
	def __init__(self, name = "", label = "", short_info = ""):
		super(SXcmd_category, self).__init__(name, label, short_info)
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		# self.name = name              # <Inherit from SXmenu_item> Name of this command category (i.e. sxc_movie_micrograph, sxc_ctf, sxc_particle_stack, sxc_2d_clustering, sxc_initial_3d_modeling, sxc_3d_refinement, sxc_3d_clustering, sxc_utilities), used as a key of dictionary
		# self.label = label            # <Inherit from SXmenu_item> User friendly name of this command category
		# self.short_info = short_info  # <Inherit from SXmenu_item> Short description of this command category
		self.cmd_list = []              # <Used only in sxgui.py> list of commands in this category. Need this to keep the order of commands 
#		self.cmd_dict = {}              # <Used only in sxgui.py> dictionary of commands in this category, organised by names of commands. Easy to access a command but looses their order
		# self.btn = None               # <Inherit from SXmenu_item> QPushButton button instance associating with this category
		# self.widget = None            # <Inherit from SXmenu_item> SXCmdWidget instance associating with this category
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
	
# ========================================================================================
class SXconst(object):
	def __init__(self):
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		self.key = ""                # <Used only in sxgui.py> key of constant parameter
		self.label = ""              # <Used only in sxgui.py> User friendly name of constant parameter
		self.help = ""               # <Used only in sxgui.py> Help info
		self.register = ""           # <Used only in sxgui.py> Default value
		self.type = ""               # <Used only in sxgui.py> Type of value
		self.register_widget = None  # <Used only in sxgui.py> Restore widget instance associating with this command token
		self.widget = None           # <Used only in sxgui.py> Widget instance associating with this constant parameter
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><

# ========================================================================================
class SXconst_set(SXmenu_item):
	def __init__(self):
		super(SXconst_set, self).__init__()
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		# self.name = ""        # <Inherit from SXmenu_item> Name of this constant parameter set
		# self.label = ""       # <Inherit from SXmenu_item> User friendly name of this set
		# self.short_info = ""  # <Inherit from SXmenu_item> Short description of this set
		self.list = []          # <Used only in sxgui.py> list of constant parameters. Need this to keep the order of constant parameters
		self.dict = {}          # <Used only in sxgui.py> dictionary of constant parameters, organised by keys of constant parameters. Easy to access each constant parameter but looses their order
		# self.btn = None       # <Inherit from SXmenu_item> QPushButton button instance associating with this set
		# self.widget = None    # <Inherit from SXmenu_item> Widget instance associating with this set
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><

# ========================================================================================
class SXLookFeelConst(object):
	# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
	# static class variables
	# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
	default_bg_color = QColor(229, 229, 229, 192) # default_bg_color = QColor(229, 229, 229, 242) # Greyish-White Transparent
	sxinfo_widget_bg_color = QColor(0, 0, 0, 10) # Almost-Completely Transparent
	sxcmd_widget_bg_color = QColor(0, 0, 0, 0) # Completely Transparent
	sxcmd_tab_bg_color = QColor(255, 255, 255, 64) # White Transparent
	
	# Constants
	project_dir = "sxgui_settings"
	sxmain_window_left = 0
	sxmain_window_top = 0
	sxmain_window_min_width = 1280 # Requirement of specification
	sxmain_window_min_height = 720 # Requirement of specification
	expected_cmd_counts = 32
	grid_margin = 6 # grid_margin = 12
	grid_spacing = 6
	
	# Constants initialised with invalid values.  
	# Valid values should be set by initialise() function
	screen_height = -1
	sxmain_window_width = -1
	sxmain_window_height = -1
	sxmenu_item_btn_width = -1
	grid_distance = -1
	sxmenu_btn_area_min_width = -1
	sxcmd_btn_area_min_width = -1
	sxcmd_widget_area_min_width = -1
	
	@staticmethod
	def initialise(sxapp):
		# Search for maximun screen height and set it to SXLookFeelConst singleton class
		max_screen_height = sxapp.desktop().screenGeometry().height()
		for index in range(sxapp.desktop().screenCount()):
			screen_height = sxapp.desktop().screenGeometry(index).height()
			if max_screen_height < screen_height:
				max_screen_height = screen_height
		SXLookFeelConst.screen_height = max_screen_height
		
		# Set size of the main window depending on the screen size
		if SXLookFeelConst.screen_height > SXLookFeelConst.sxmain_window_min_width:
			SXLookFeelConst.sxmain_window_height = SXLookFeelConst.screen_height / 2
		else:
			SXLookFeelConst.sxmain_window_height = SXLookFeelConst.sxmain_window_min_width
		
		SXLookFeelConst.sxmain_window_width = SXLookFeelConst.sxmain_window_height / (float(SXLookFeelConst.sxmain_window_min_height) / float(SXLookFeelConst.sxmain_window_min_width))
	
		SXLookFeelConst.sxmenu_item_btn_width = SXLookFeelConst.sxmain_window_width / 13
		SXLookFeelConst.grid_distance = SXLookFeelConst.sxmenu_item_btn_width / 10
		
		SXLookFeelConst.sxmenu_btn_area_min_width = 2 * SXLookFeelConst.sxmenu_item_btn_width + SXLookFeelConst.grid_distance + 18
		SXLookFeelConst.sxcmd_btn_area_min_width = 240
		SXLookFeelConst.sxcmd_widget_area_min_width = SXLookFeelConst.sxmain_window_width - SXLookFeelConst.sxmenu_btn_area_min_width - SXLookFeelConst.sxcmd_btn_area_min_width

# ========================================================================================
class SXLogoButton(QPushButton):
	def __init__(self, logo_file_path, parent = None):
		super(SXLogoButton, self).__init__(parent)
		
		# print "MRK_DEBUG: logo_file_path = %s" % logo_file_path
		# print "MRK_DEBUG: os.path.exists(logo_file_path) %s" % os.path.exists(logo_file_path)
		
		# Width of logo image
		logo_width = SXLookFeelConst.sxmenu_item_btn_width * 2 + SXLookFeelConst.grid_distance
		
		# Style of widget
		self.setFixedSize(logo_width, 0.434 * logo_width)
		self.customButtonStyle = """
			SXLogoButton {{background-color: rgba(0, 0, 0, 0); border: 0px solid black; border-radius: 0px; image: url("{0}");}}
			SXLogoButton:focus {{background-color: rgba(0, 0, 0, 0); border: 0px solid grey; border-radius: 0px; image: url("{0}");}}
			SXLogoButton:pressed {{background-color: rgba(0, 0, 0, 0); border: 0px solid red; border-radius: 0px; image: url("{0}");}}
			""".format(logo_file_path)
		self.customButtonStyleClicked = """
			SXLogoButton {{background-color: rgba(0, 0, 0, 0); border: 0px solid black; border-radius: 0px; image: url("{0}");}}
			SXLogoButton:focus {{background-color: rgba(0, 0, 0, 0); border: 0px solid grey; border-radius: 0px; image: url("{0}");}}
			SXLogoButton:pressed {{background-color: rgba(0, 0, 0, 0); border: 0px solid red; border-radius: 0px; image: url("{0}");}}
			""".format(logo_file_path)
		
		# Set style and add click event
		self.setStyleSheet(self.customButtonStyle)

# ========================================================================================
class SXPictogramButton(QPushButton):
	def __init__(self, pictogram_file_path, parent = None):
		super(SXPictogramButton, self).__init__(parent)
		
		# print "MRK_DEBUG: pictogram_file_path = %s" % pictogram_file_path
		# print "MRK_DEBUG: os.path.exists(logo_file_path) %s" % os.path.exists(pictogram_file_path)
		
		# Width of pictogram image
		pictogram_width = SXLookFeelConst.sxmenu_item_btn_width
		
		# Style of widget
		self.setFixedSize(pictogram_width, pictogram_width)
		self.customButtonStyle = """
			SXPictogramButton {{background-color: rgba(0, 0, 0, 0); border: 2px solid rgba(0, 0, 0, 0); border-radius: {1}px; image: url("{0}");}}
			SXPictogramButton:focus {{background-color: rgba(0, 0, 0, 0); border: 2px solid grey; border-radius: {1}px; image: url("{0}");}}
			SXPictogramButton:pressed {{background-color: rgba(0, 0, 0, 0); border: 2px solid rgb(153, 153, 153); border-radius: {1}px; image: url("{0}");}}
			""".format(pictogram_file_path, pictogram_width / 4)
		self.customButtonStyleClicked = """
			SXPictogramButton:pressed {{background-color: rgba(0, 0, 0, 0); border: 2px solid rgb(153, 153, 153); border-radius: {1}px; image: url("{0}");}}
			SXPictogramButton {{background-color: rgba(0, 0, 0, 0); border: 2px solid rgb(220, 220, 220); border-radius: {1}px; image: url("{0}");}}
			""".format(pictogram_file_path, pictogram_width / 4)
		
		# Set style and add click event
		self.setStyleSheet(self.customButtonStyle)

class SXMenuItemBtnAreaWidget(QWidget):
	def __init__(self, sxconst_set, sxcmd_category_list, sxinfo, parent = None):
		super(SXMenuItemBtnAreaWidget, self).__init__(parent)
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
		
		# Create widgets for pipeline command category button area and miscellaneous function button area
		sxcmd_category_btn_subarea_widget = self.create_sxmenu_item_btn_subarea_widget()
		misc_func_btn_subarea_widget = self.create_sxmenu_item_btn_subarea_widget()
		for sxcmd_category in sxcmd_category_list:
			if sxcmd_category.name != "sxc_utilities":
				self.add_sxmenu_item_btn_widget(sxcmd_category, sxcmd_category_btn_subarea_widget)
			else: # assert(sxcmd_category.name == "sxc_utilities")
				self.add_sxmenu_item_btn_widget(sxcmd_category, misc_func_btn_subarea_widget)
		self.add_sxmenu_item_btn_widget(sxconst_set, misc_func_btn_subarea_widget)
		
		global_layout = QVBoxLayout()
		global_layout.setContentsMargins(0, 0, 0, 0)
		
		sxmenu_item_btn_area_widget = QWidget(self)
		sxmenu_item_btn_area_widget.setObjectName('SXMenuItemBtnAreaWidget')
		sxmenu_item_btn_area_widget.setStyleSheet('QWidget#SXMenuItemBtnAreaWidget {background-color: rgba(0, 0, 0, 153);}')
		sxmenu_item_btn_area_widget.setFixedWidth(SXLookFeelConst.sxmenu_btn_area_min_width)
		
		sxmenu_item_btn_area_layout = QVBoxLayout()
		
		# Add widget of pipeline command category button area to layout
		sxmenu_item_btn_area_layout.addWidget(sxcmd_category_btn_subarea_widget)
		
		# Create and Add separator label
		layout_label = QHBoxLayout()
		line_label = QLabel(sxmenu_item_btn_area_widget)
		line_label.setFixedHeight(1)
		line_label.setFixedWidth(SXLookFeelConst.sxmenu_item_btn_width * 2)
		line_label.setStyleSheet('background-color: rgba(220, 220, 220, 100)')
		layout_label.addWidget(line_label)
		layout_label.setContentsMargins(0, 7, 0, 7)
		
		sxmenu_item_btn_area_layout.addLayout(layout_label)
		
		# Add widget of miscellaneous function button area to layout
		sxmenu_item_btn_area_layout.addWidget(misc_func_btn_subarea_widget)
		
		# Add stretch to make a space and keep sizes of the other widgets to be constant
		sxmenu_item_btn_area_layout.addStretch(1)
		
		# Add menu item button for application information
		sxmenu_item_btn_pictograph_file_path = '{0}sxgui_logo_sphire.png'.format(get_image_directory())
		sxmenu_item_btn = SXLogoButton(sxmenu_item_btn_pictograph_file_path)
		sxinfo.btn = sxmenu_item_btn
		
		sxmenu_item_btn_area_layout.addWidget(sxmenu_item_btn)
		
		# Set menu item button area layout to the widget
		sxmenu_item_btn_area_widget.setLayout(sxmenu_item_btn_area_layout)
		
		# self related settings
		global_layout.addWidget(sxmenu_item_btn_area_widget)
		self.setLayout(global_layout)
		
	def create_sxmenu_item_btn_subarea_widget(self):
		sxmenu_item_btn_subarea_widget = QWidget()
		
		grid_layout = QGridLayout()
		grid_layout.setSpacing(SXLookFeelConst.grid_distance)
		grid_layout.setContentsMargins(0, 0, 0, 0)
		
		sxmenu_item_btn_subarea_widget.setLayout(grid_layout)
		
		return sxmenu_item_btn_subarea_widget
		
	def add_sxmenu_item_btn_widget(self, sxmenu_item, sxmenu_item_btn_subarea_widget):
		assert(isinstance(sxmenu_item, SXmenu_item) == True) # Assuming the sxmenu_item is an instance of class SXmenu_item
		
		sxmenu_item_btn_pictograph_file_path = "{0}sxgui_pictograph_{1}.png".format(get_image_directory(), sxmenu_item.name.replace("sxc_", ""))
		sxmenu_item.btn = SXPictogramButton(sxmenu_item_btn_pictograph_file_path, self)
		cur_widget_counts = sxmenu_item_btn_subarea_widget.layout().count()
		sxmenu_item_btn_subarea_widget.layout().addWidget(sxmenu_item.btn, cur_widget_counts // 2, cur_widget_counts % 2)

# ========================================================================================
# Provides all necessary functionarity
# tabs only provides widgets and knows how to layout them
class SXCmdWidget(QWidget):
	def __init__(self, sxconst_set, sxcmd, parent = None):
		super(SXCmdWidget, self).__init__(parent)
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		self.sxconst_set = sxconst_set
		self.sxcmd = sxcmd
		
		self.sxcmd_tab_main = None
		self.sxcmd_tab_advance = None
		
		self.child_application_list = []
		
		self.gui_settings_file_path = "%s/gui_settings_%s.txt" % (self.sxcmd.get_category_dir_path(SXLookFeelConst.project_dir), self.sxcmd.get_mode_name_for("file_path"))
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		
		# Set grid layout
		grid_layout = QGridLayout(self)
		# grid_layout.setMargin(SXLookFeelConst.grid_margin)
		# grid_layout.setSpacing(SXLookFeelConst.grid_spacing)
		
		self.setAutoFillBackground(True)
		palette = QPalette()
		palette.setBrush(QPalette.Background, QBrush(SXLookFeelConst.sxcmd_widget_bg_color))
		self.setPalette(palette)
		
		self.sxcmd_tab_main = SXCmdTab("Main", self)
		self.sxcmd_tab_advance = SXCmdTab("Advanced", self)
		tab_widget = QTabWidget()
		tab_widget.insertTab(0, self.sxcmd_tab_main, self.sxcmd_tab_main.name)
		tab_widget.insertTab(1, self.sxcmd_tab_advance, self.sxcmd_tab_advance.name)
		tab_widget.setAutoFillBackground(True)
		palette = tab_widget.palette()
		palette.setBrush(QPalette.Background, QBrush(SXLookFeelConst.sxcmd_widget_bg_color))
		tab_widget.setPalette(palette)
		grid_layout.addWidget(tab_widget, 0, 0)
		
	def map_widgets_to_sxcmd_line(self):
		# Add program name to command line
		sxcmd_line = "%s.py" % self.sxcmd.name
		
		# Loop through all command tokens
		for sxcmd_token in self.sxcmd.token_list:
			# First, handle very special cases
			if sxcmd_token.type == "function":
				user_func_name_index = 0
				external_file_path_index = 1
				user_func_name = str(sxcmd_token.widget[user_func_name_index].text())
				external_file_path = str(sxcmd_token.widget[external_file_path_index].text())
				
				# This is not default value
				if external_file_path not in ["", sxcmd_token.default[external_file_path_index]]:
					# Case 1: User specified an exteranl function different from default or empty string
					if os.path.splitext(external_file_path)[1] != ".py": 
						QMessageBox.warning(self, "Invalid parameter value", "Exteranl File Path (%s) should include the python script extension (.py)." % (external_file_path))
						return ""
					dir_path, file_basename = os.path.split(external_file_path)
					file_basename = file_basename.replace(".py", "")
					sxcmd_line += " %s%s=[%s,%s,%s]" % (sxcmd_token.key_prefix, sxcmd_token.key_base, dir_path, file_basename, user_func_name)
				elif user_func_name != sxcmd_token.default[user_func_name_index]:
					# Case 2: User specified an internal function different from default
					sxcmd_line += " %s%s=%s" % (sxcmd_token.key_prefix, sxcmd_token.key_base, user_func_name)
				# else: User left default value. Do nothing
			# Then, handle the other cases//
			else:
				if sxcmd_token.type == "bool":
					if not ((sxcmd_token.widget.checkState() == Qt.Checked) == sxcmd_token.default and sxcmd_token.is_required == False): 
						### if (sxcmd_token.widget.checkState() == Qt.Checked) == sxcmd_token.default and sxcmd_token.is_required == True:  # Add this token to command line
						### if (sxcmd_token.widget.checkState() == Qt.Checked) != sxcmd_token.default and sxcmd_token.is_required == True:  # Add this token to command line
						### if (sxcmd_token.widget.checkState() == Qt.Checked) != sxcmd_token.default and sxcmd_token.is_required == False: # Add this token to command line
						sxcmd_line += " %s%s" % (sxcmd_token.key_prefix, sxcmd_token.key_base)
					#else: 
						### if (sxcmd_token.widget.checkState() == Qt.Checked) == sxcmd_token.default and sxcmd_token.is_required == False: # Do not add this token to command line
				else:
					if sxcmd_token.widget.text() == sxcmd_token.default:
						### if sxcmd_token.widget.text() == sxcmd_token.default and sxcmd_token.is_required == True:  # Error case
						if sxcmd_token.is_required == True: 
							QMessageBox.warning(self, "Invalid parameter value", "Token (%s) of command (%s) is required. Please set the value for this." % (sxcmd_token.label, self.sxcmd.get_mode_name_for("message_output")))
							return ""
						### if sxcmd_token.widget.text() == sxcmd_token.default and sxcmd_token.is_required == False: # Do not add this token to command line
						# else: # assert(sxcmd_token.is_required == False) # Do not add to this command line
					else: # sxcmd_token.widget.text() != sxcmd_token.default
						### if sxcmd_token.widget.text() != sxcmd_token.default and sxcmd_token.is_required == True:  # Add this token to command line
						### if sxcmd_token.widget.text() != sxcmd_token.default and sxcmd_token.is_required == False: # Add this token to command line
						
						# For now, using line edit box for the other type
						widget_text = str(sxcmd_token.widget.text())
						if sxcmd_token.type not in ["int", "float", "apix", "wn", "box", "radius", "any_file_list", "any_image_list"]:
							# Always enclose the string value with single quotes (')
							widget_text = widget_text.strip("\'")  # make sure the string is not enclosed by (')
							widget_text = widget_text.strip("\"")  # make sure the string is not enclosed by (")
							widget_text = "\'%s\'" % (widget_text) # then, enclose the string value with single quotes (')
						
						if sxcmd_token.key_prefix == "":
							sxcmd_line += " %s" % (widget_text)
						elif sxcmd_token.key_prefix == "--":
							sxcmd_line += " %s%s=%s" % (sxcmd_token.key_prefix, sxcmd_token.key_base, widget_text)
						else:
							ERROR("Logical Error: Encountered unexpected prefix for token (%s) of command (%s). Consult with the developer." % (sxcmd_token.key_base, self.sxcmd.get_mode_name_for("human")), "%s in %s" % (__name__, os.path.basename(__file__)))
						# else: # assert(sxcmd_token.widget.text() == sxcmd_token.default) # Do not add to this command line
		
		return sxcmd_line
	
	def generate_cmd_line(self):
		# Generate SX command line 
		sxcmd_line = self.map_widgets_to_sxcmd_line()
		
		if sxcmd_line:
			# SX command line is not empty
			# If mpi is not supported set number of MPI processer (np) to 1
			np = 1
			if self.sxcmd.mpi_support:
				# mpi is supported
				np = int(str(self.sxcmd_tab_main.mpi_nproc_edit.text()))
				# 
				# DESIGN_NOTE: 2016/03/17 Toshio Moriya
				# The MPI policy below has changed!!! An example of this exception is sxcter.py.
				# Don't add --MPI flag if np == 1
				# 
				# DESIGN_NOTE: 2015/10/27 Toshio Moriya
				# Since we now assume sx*.py exists in only MPI version, always add --MPI flag if necessary
				# This is not elegant but can be removed when --MPI flag is removed from all sx*.py scripts 
				# 
				if self.sxcmd.mpi_add_flag and np > 1:
					sxcmd_line += " --MPI"
					
				# DESIGN_NOTE: 2016/02/11 Toshio Moriya
				# Ideally, the following exceptional cases should not handled in here 
				# because it will remove the generality from the software design
				required_key_base = None
				if self.sxcmd.name == "sxisac":
					required_key_base = "indep_run"
				elif self.sxcmd.name == "sxviper":
					required_key_base = "nruns"
				elif self.sxcmd.name == "sxrviper":
					required_key_base = "n_shc_runs"
				# else: # Do nothing
				
				if required_key_base != None:
					required_divisor = int(str(self.sxcmd.token_dict[required_key_base].widget.text()))
					required_label =  self.sxcmd.token_dict[required_key_base].label
					if required_divisor == 0:
						QMessageBox.warning(self, "Invalid parameter value", "\"%s\" must be larger than 0. Please check the setting" % (required_label))
						return "" 
					
					valid_np = np
					if valid_np % required_divisor != 0:
						if valid_np < required_divisor:
							valid_np = required_divisor
						else:
							valid_np = valid_np - (valid_np % required_divisor)
						QMessageBox.warning(self, "Invalid parameter value", "The number of \"MPI processes\" (%d) is invalid. It MUST BE multiplicity of \"%s\" (%d). Please check the setting. A close valid number is %d." % (np, required_label, required_divisor,valid_np))
						return "" 
							
			# else: assert(np == 1) # because the "MPI Processes" is disabled for sx*.py process which does not support mpi
				
			# Generate command line according to the case
			cmd_line = ""
			if self.sxcmd_tab_main.qsub_enable_checkbox.checkState() == Qt.Checked:
				# Case 1: queue submission is enabled (MPI can be supported or unsupported)
				# Create script for queue submission from a give template
				if os.path.exists(self.sxcmd_tab_main.qsub_script_edit.text()) != True: 
					QMessageBox.warning(self, "Invalid parameter value", "Invalid file path for qsub script template (%s)." % (self.sxcmd_tab_main.qsub_script_edit.text()))
					return "" 
					
				file_template = open(self.sxcmd_tab_main.qsub_script_edit.text(),"r")
				# Extract command line from qsub script template 
				for line in file_template:
					if line.find("XXX_SXCMD_LINE_XXX") != -1:
						cmd_line = line.replace("XXX_SXCMD_LINE_XXX", sxcmd_line)
						if cmd_line.find("XXX_SXMPI_NPROC_XXX") != -1:
							cmd_line = cmd_line.replace("XXX_SXMPI_NPROC_XXX", str(np))
						if cmd_line.find("XXX_SXMPI_JOB_NAME_XXX") != -1:
							cmd_line = cmd_line.replace("XXX_SXMPI_JOB_NAME_XXX", str(self.sxcmd_tab_main.qsub_job_name_edit.text()))
				file_template.close()
			elif self.sxcmd.mpi_support:
				# Case 2: queue submission is disabled, but MPI is supported
				if self.sxcmd_tab_main.qsub_enable_checkbox.checkState() == Qt.Checked: ERROR("Logical Error: Encountered unexpected condition for sxcmd_tab_main.qsub_enable_checkbox.checkState. Consult with the developer.", "%s in %s" % (__name__, os.path.basename(__file__)))
				# Add MPI execution to command line
				cmd_line = str(self.sxcmd_tab_main.mpi_cmd_line_edit.text())
				# If empty string is entered, use a default template
				if cmd_line == "":
					cmd_line = "mpirun -np XXX_SXMPI_NPROC_XXX XXX_SXCMD_LINE_XXX"
				if cmd_line.find("XXX_SXMPI_NPROC_XXX") != -1:
					cmd_line = cmd_line.replace("XXX_SXMPI_NPROC_XXX", str(np))
				if cmd_line.find("XXX_SXCMD_LINE_XXX") != -1:
					cmd_line = cmd_line.replace("XXX_SXCMD_LINE_XXX", sxcmd_line)
			else: 
				# Case 3: queue submission is disabled, and MPI is not supported
				if self.sxcmd_tab_main.qsub_enable_checkbox.checkState() == Qt.Checked: ERROR("Logical Error: Encountered unexpected condition for sxcmd_tab_main.qsub_enable_checkbox.checkState. Consult with the developer.", "%s in %s" % (__name__, os.path.basename(__file__)))
				# Use sx command as it is
				cmd_line = sxcmd_line
		else:
			# SX command line is be empty because an error happens in map_widgets_to_sxcmd_line
			cmd_line = ""
		
		return cmd_line
	
	def execute_cmd_line(self):
		# Generate command line 
		cmd_line = self.generate_cmd_line()
		
		if cmd_line:
			# Command line is not empty
			# First, check existence of outputs
			for sxcmd_token in self.sxcmd.token_list:
				if sxcmd_token.type == "output":
					if os.path.exists(sxcmd_token.widget.text()):
						# DESIGN_NOTE: 2015/11/24 Toshio Moriya
						# This special case needs to be handled with more general method...
						if self.sxcmd.name in ["sxisac", "sxviper", "sxrviper", "sxmeridien", "sxsort3d"]:
							reply = QMessageBox.question(self, "Output Directory/File", "Output Directory/File (%s) already exists. Do you really want to run the program with continue mode?" % (sxcmd_token.widget.text()), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
							if reply == QMessageBox.No:
								return
							# else: # Do nothing
						else:
							QMessageBox.warning(self, "Output Directory/File", "Output Directory/File (%s) already exists. Please change the name and try it again. Aborting execution ..." % (sxcmd_token.widget.text()))
							return
			
			# If mpi is not supported set number of MPI processer (np) to 1
			np = 1
			if self.sxcmd.mpi_support:
				np = int(str(self.sxcmd_tab_main.mpi_nproc_edit.text()))
			
			if self.sxcmd_tab_main.qsub_enable_checkbox.checkState() == Qt.Checked:
				# Case 1: queue submission is enabled (MPI can be supported or unsupported)
				# Create script for queue submission from a give template
				template_file_path = self.sxcmd_tab_main.qsub_script_edit.text()
				if os.path.exists(template_file_path) == False: 
					QMessageBox.warning(self, "Invalid parameter value", "Invalid file path for qsub script template (%s). Aborting execution ..." % (template_file_path))
					return
				file_template = open(self.sxcmd_tab_main.qsub_script_edit.text(),"r")
				file_name_qsub_script = "qsub_" + str(self.sxcmd_tab_main.qsub_job_name_edit.text()) + ".sh"
				file_qsub_script = open(file_name_qsub_script,"w")
				for line_io in file_template:
					if line_io.find("XXX_SXCMD_LINE_XXX") != -1:
						line_io = cmd_line
					else:
						if line_io.find("XXX_SXMPI_NPROC_XXX") != -1:
							line_io = line_io.replace("XXX_SXMPI_NPROC_XXX", str(np))
						if line_io.find("XXX_SXMPI_JOB_NAME_XXX") != -1:
							line_io = line_io.replace("XXX_SXMPI_JOB_NAME_XXX", str(self.sxcmd_tab_main.qsub_job_name_edit.text()))
					file_qsub_script.write(line_io)
				file_template.close()
				file_qsub_script.close()
				# Generate command line for queue submission
				cmd_line_in_script = cmd_line
				cmd_line = str(self.sxcmd_tab_main.qsub_cmd_edit.text()) + " " + file_name_qsub_script
				print "Wrote the following command line in the queue submission script: "
				print cmd_line_in_script
				print "Submitted a job by the following command: "
				print cmd_line
			else:
				# Case 2: queue submission is disabled (MPI can be supported or unsupported)
				if self.sxcmd_tab_main.qsub_enable_checkbox.checkState() == Qt.Checked: ERROR("Logical Error: Encountered unexpected condition for sxcmd_tab_main.qsub_enable_checkbox.checkState. Consult with the developer.", "%s in %s" % (__name__, os.path.basename(__file__)))
				print "Executed the following command: "
				print cmd_line
		
			# Execute the generated command line
			process = subprocess.Popen(cmd_line, shell=True)
			self.emit(SIGNAL("process_started"), process.pid)
			if self.sxcmd.is_submittable == False:
				assert(self.sxcmd.mpi_support == False)
				# Register to This is a GUI application
				self.child_application_list.append(process)
			
			# Save the current state of GUI settings
			if os.path.exists(self.sxcmd.get_category_dir_path(SXLookFeelConst.project_dir)) == False:
				os.mkdir(self.sxcmd.get_category_dir_path(SXLookFeelConst.project_dir))
			self.write_params(self.gui_settings_file_path)
		# else: SX command line is be empty because an error happens in generate_cmd_line. Let's do nothing
	
	def print_cmd_line(self):
		# Generate command line 
		cmd_line = self.generate_cmd_line()
		if cmd_line:
			message_line = "Generated the following command line:"
			print message_line
			print cmd_line
			QtGui.QMessageBox.information(self, "Information","%s \n\n%s" % (message_line, cmd_line))
			
			# Save the current state of GUI settings
			if os.path.exists(self.sxcmd.get_category_dir_path(SXLookFeelConst.project_dir)) == False:
				os.mkdir(self.sxcmd.get_category_dir_path(SXLookFeelConst.project_dir))
			self.write_params(self.gui_settings_file_path)
		# else: Do nothing
	
	def write_params(self, file_path_out):
		file_out = open(file_path_out,"w")
		
		# Write script name for consistency check upon loading
		file_out.write("@@@@@ %s gui settings - " % (self.sxcmd.get_mode_name_for("human")))
		# file_out.write(EMANVERSION + " (CVS" + CVSDATESTAMP[6:-2] +")")
		file_out.write(EMANVERSION + " (GITHUB: " + DATESTAMP +")" )
		file_out.write(" @@@@@ \n")
		
		# Define list of (tab) groups
		group_main = "main"
		group_advanced = "advanced"
		
		# Loop through all groups. First write out values of widgets in main tab, then ones in advanced
		for group in [group_main, group_advanced]:
			# Loop through all command tokens
			for cmd_token in self.sxcmd.token_list:
				if cmd_token.group == group:
					# First, handle very special cases
					if cmd_token.type == "function":
						# This type has two line edit boxes as a list of widget
						n_widgets = 2
						for widget_index in xrange(n_widgets):
							val_str = str(cmd_token.widget[widget_index].text()) 
							file_out.write("<%s> %s (default %s) == %s \n" % (cmd_token.key_base, cmd_token.label[widget_index], cmd_token.default[widget_index], val_str))
					# Then, handle the other cases
					else:
						val_str = ""
						if cmd_token.type == "bool":
							if cmd_token.widget.checkState() == Qt.Checked:
								val_str = "YES"
							else:
								val_str = "NO"
						else:
							# The other type has only one line edit box
							val_str = str(cmd_token.widget.text())
						
						if cmd_token.is_required == False:
							file_out.write("<%s> %s (default %s) == %s \n" % (cmd_token.key_base, cmd_token.label, cmd_token.default, val_str))
						else:
							file_out.write("<%s> %s (default required %s) == %s \n" % (cmd_token.key_base, cmd_token.label, cmd_token.type, val_str))
				# else: do nothig
			
		# At the end of parameter file...
		# Write MPI parameters 
		file_out.write("%s == %s \n" % ("MPI processors", str(self.sxcmd_tab_main.mpi_nproc_edit.text())))
		file_out.write("%s == %s \n" % ("MPI Command Line Template", str(self.sxcmd_tab_main.mpi_cmd_line_edit.text())))
		# Write Qsub parameters 
		if self.sxcmd_tab_main.qsub_enable_checkbox.checkState() == Qt.Checked:
			val_str = "YES"
		else:
			val_str = "NO"
		file_out.write("%s == %s \n" % ("Submit Job to Queue", val_str))	
		file_out.write("%s == %s \n" % ("Job Name", str(self.sxcmd_tab_main.qsub_job_name_edit.text())))
		file_out.write("%s == %s \n" % ("Submission Command", str(self.sxcmd_tab_main.qsub_cmd_edit.text())))
		file_out.write("%s == %s \n" % ("Submission Script Template", str(self.sxcmd_tab_main.qsub_script_edit.text())))
		
		file_out.close()
	
	def read_params(self, file_path_in):
		file_in = open(file_path_in,"r")
		
		# Check if this parameter file is for this sx script
		line_in = file_in.readline()
		if line_in.find("@@@@@ %s gui settings" % (self.sxcmd.get_mode_name_for("human"))) != -1:
			n_function_type_lines = 2
			function_type_line_counter = 0
			# loop through the rest of lines
			for line_in in file_in:
				# Extract label (which should be left of "=="). Also strip the ending spaces
				label_in = line_in.split("==")[0].strip()
				# Extract value (which should be right of "=="). Also strip all spaces
				val_str_in = line_in.split("==")[1].strip() 
				
				if label_in == "MPI processors":
					self.sxcmd_tab_main.mpi_nproc_edit.setText(val_str_in)
				elif label_in == "MPI Command Line Template":
					self.sxcmd_tab_main.mpi_cmd_line_edit.setText(val_str_in)
				elif label_in == "Submit Job to Queue":
					if val_str_in == "YES":
						self.sxcmd_tab_main.qsub_enable_checkbox.setChecked(True)
					else: # assert(val_str_in == "NO")
						self.sxcmd_tab_main.qsub_enable_checkbox.setChecked(False)
				elif label_in == "Job Name":
					self.sxcmd_tab_main.qsub_job_name_edit.setText(val_str_in)
				elif label_in == "Submission Command":
					self.sxcmd_tab_main.qsub_cmd_edit.setText(val_str_in)
				elif label_in == "Submission Script Template":
					self.sxcmd_tab_main.qsub_script_edit.setText(val_str_in)
				else:
					# Extract key_base of this command token
					target_operator = "<"
					item_tail = label_in.find(target_operator)
					if item_tail != 0: 
						QMessageBox.warning(self, "Invalid Parameter File Format", "Command token entry should start from \"%s\" for key base name in line (%s). The format of this file might be corrupted. Please save the paramater file again." % (target_operator, line_in))
					label_in = label_in[item_tail + len(target_operator):].strip() # Get the rest of line
					target_operator = ">"
					item_tail = label_in.find(target_operator)
					if item_tail == -1: 
						QMessageBox.warning(self, "Invalid Parameter File Format", "Command token entry should have \"%s\" closing key base name in line (%s) The format of this file might be corrupted. Please save the paramater file again." % (target_operator, line_in))
					key_base = label_in[0:item_tail]
					# Get corresponding cmd_token
					if key_base not in self.sxcmd.token_dict.keys(): 
						QMessageBox.warning(self, "Invalid Parameter File Format", "Invalid base name of command token \"%s\" is found in line (%s). This parameter file might be imcompatible with the current version. Please save the paramater file again." % (key_base, line_in))
					cmd_token = self.sxcmd.token_dict[key_base]
					# First, handle very special cases
					if cmd_token.type == "function":
						cmd_token.widget[function_type_line_counter].setText(val_str_in)
						function_type_line_counter += 1
						function_type_line_counter %= n_function_type_lines # function have two line edit boxes
					# Then, handle the other cases
					else:
						if cmd_token.type == "bool":
							# construct new widget(s) for this command token
							if val_str_in == "YES":
								cmd_token.widget.setChecked(Qt.Checked)
							else: # val_str_in == "NO"
								cmd_token.widget.setChecked(Qt.Unchecked)
						else:
							# For now, use line edit box for the other type
							cmd_token.widget.setText(val_str_in)
						
		else:
			QMessageBox.warning(self, "Fail to load parameters", "The specified file is not parameter file for %s." % self.sxcmd.get_mode_name_for("human"))
		
		file_in.close()
	
	def save_params(self):
		file_path_out = str(QFileDialog.getSaveFileName(self, "Save Parameters", options = QFileDialog.DontUseNativeDialog))
		if file_path_out != "":
			self.write_params(file_path_out)
	
	def load_params(self):
		file_path_in = str(QFileDialog.getOpenFileName(self, "Load parameters", options = QFileDialog.DontUseNativeDialog))
		if file_path_in != "":
			self.read_params(file_path_in)
	
	def select_file(self, target_widget, file_format = ""):
		file_path = ""
		if file_format == "bdb":
			file_path = str(QFileDialog.getOpenFileName(self, "Select BDB File", "", "BDB files (*.bdb)", options = QFileDialog.DontUseNativeDialog))
			# Use relative path. 
			if file_path:
				file_path = "bdb:./" + os.path.relpath(file_path).replace("EMAN2DB/", "#").replace(".bdb", "")
				file_path = file_path.replace("/#", "#")
				# If the input directory is the current directory, use the simplified DBD file path format
				if file_path.find(".#") != -1:
					file_path = file_path.replace(".#", "")
		elif file_format == "py":
			file_path = str(QFileDialog.getOpenFileName(self, "Select Python File", "", "PY files (*.py)", options = QFileDialog.DontUseNativeDialog))
			# Use full path
		elif file_format == "pdb":
			file_path = str(QFileDialog.getOpenFileName(self, "Select PDB File", "", "PDB files (*.pdb *.pdb1)", options = QFileDialog.DontUseNativeDialog))
			# Use relative path. 
			if file_path:
				file_path = os.path.relpath(file_path)
		elif file_format == "mrc":
			file_path = str(QFileDialog.getOpenFileName(self, "Select MRC File", "", "MRC files (*.mrc)", options = QFileDialog.DontUseNativeDialog))
			# Use relative path. 
			if file_path:
				file_path = os.path.relpath(file_path)
		elif file_format == "any_file_list" or file_format == "any_image_list":
			file_path_list = QFileDialog.getOpenFileNames(self, "Select Files", "", "All files (*.*)", options = QFileDialog.DontUseNativeDialog)
			# Use relative path. 
			for a_file_path in file_path_list:
				file_path += os.path.relpath(str(a_file_path)) + " "
		else:
			if file_format:
				file_path = str(QFileDialog.getOpenFileName(self, "Select %s File" % (file_format.upper()), "", "%s files (*.%s)"  % (file_format.upper(), file_format), options = QFileDialog.DontUseNativeDialog))
			else:
				file_path = str(QFileDialog.getOpenFileName(self, "Select File", "", "All files (*.*)", options = QFileDialog.DontUseNativeDialog))
			# Use relative path. 
			if file_path:
				file_path = os.path.relpath(file_path)
			
		if file_path != "":
			target_widget.setText(file_path)
	
	def select_dir(self, target_widget):
		dir_path = str(QFileDialog.getExistingDirectory(self, "Select Directory", "", options = QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks | QFileDialog.DontUseNativeDialog))
		if dir_path != "":
			# Use relative path. 
			target_widget.setText(os.path.relpath(dir_path))
	
	def quit_all_child_applications(self):
		# Quit all child applications
		for child_application in self.child_application_list:
			child_application.kill()
			# child_application.terminate() # This call ends up outputing "Program interrupted" Message and it is not pretty...
	
	"""
#	def show_output_info(self):
#		QMessageBox.information(self, "sx* output","outdir is the name of the output folder specified by the user. If it does not exist, the directory will be created. If it does exist, the program will crash and an error message will come up. Please change the name of directory and restart the program.")
	"""

# ========================================================================================
class SXCmdTab(QWidget):
	def __init__(self, name, parent=None):
		super(SXCmdTab, self).__init__(parent)
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		self.name = name
		self.sxcmdwidget = parent
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# local constants
		required_cmd_token_restore_tooltip = "please enter the value manually"
		const_cmd_token_restore_tooltip = "retrieve the registed constant value for this parameter"
		default_cmd_token_restore_tooltip = "retrieve this default value"
		
		# Setting for layout
		grid_row_origin = 0; grid_col_origin = 0
		title_row_span = 1; title_col_span = 2
		short_info_row_span = 1; short_info_col_span = 5
		func_btn_row_span = 1; func_btn_col_span = 2
		token_label_row_span = 1; token_label_col_span = 4
		token_widget_row_span = 1; token_widget_col_span = 1
		cmd_frame_row_span = 32; cmd_frame_col_span = 7
		
		title_label_min_width = 150
		title_label_min_height = 80
		short_info_min_width = 260 # short_info_min_width = 360
		short_info_min_height = 80
		func_btn_min_width = 150
		token_label_min_width = 360 # token_label_min_width = 560
		token_widget_min_width = 120
		
		# Setup global layout
		global_layout = QVBoxLayout(self)
		global_layout.setContentsMargins(0,0,0,0)
		global_layout.setSpacing(0)
		# Setup scroll area and its widget 
		scroll_area = QScrollArea()
		# scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		# scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn) # MRK_DEBUG: Useful during designing layout
		scroll_area.setWidgetResizable(True)
		scroll_area_widget = QWidget(scroll_area)
		# Setup scroll widget and its background color
		scroll_area.setStyleSheet("QScrollArea {background-color:transparent;}");
		### scroll_area_widget.setStyleSheet("background-color:transparent;");
		scroll_area_widget.setAutoFillBackground(True)
		palette = QPalette()
		palette.setBrush(QPalette.Background, QBrush(SXLookFeelConst.sxcmd_tab_bg_color))
		scroll_area_widget.setPalette(palette)
		# Register the widget to scroll area
		scroll_area.setWidget(scroll_area_widget)
		# Register the scroll area to the global layout
		global_layout.addWidget(scroll_area)
		
		# Setup grid layout in the scroll area
		grid_layout = QGridLayout(scroll_area_widget)
		grid_layout.setMargin(SXLookFeelConst.grid_margin)
		grid_layout.setSpacing(SXLookFeelConst.grid_spacing)
		grid_layout.setColumnMinimumWidth(grid_col_origin + token_label_col_span, token_widget_min_width)
		grid_layout.setColumnMinimumWidth(grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_min_width)
		grid_layout.setColumnMinimumWidth(grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_min_width)
		grid_layout.setColumnMinimumWidth(grid_col_origin + token_label_col_span + token_widget_col_span * 3, token_widget_min_width)
		# # Give the columns of token label a higher priority to stretch relative to the others
		# for col_span in xrange(token_label_col_span):
		# 	grid_layout.setColumnStretch(grid_row_origin + col_span, grid_layout.columnStretch(grid_row_origin+col_span) + 1)
		
		# Define the tab frame within the tab layout
		tab_frame = QFrame()
		grid_layout.addWidget(tab_frame, grid_row_origin, grid_col_origin, cmd_frame_row_span, cmd_frame_col_span)
		
		# Start add command token widgets to the grid layout
		grid_row = grid_row_origin
		
		tab_group = self.name.lower()
		if tab_group == "main":
			# Set a label and its position in this tab
			temp_label = QLabel("<b>%s</b>" % (self.sxcmdwidget.sxcmd.get_mode_name_for("human")))
			temp_label.setMinimumWidth(title_label_min_width)
			temp_label.setMinimumHeight(title_label_min_height)
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin, title_row_span, title_col_span)
			
			#
			# NOTE: 2015/11/17 Toshio Moriya
			# Necessary to separate "<b>%s</b>" from the information for avoiding to invoke the tag interpretations of string
			# e.g. < becomes the escape character
			# 
			temp_label = QLabel("%s" % (self.sxcmdwidget.sxcmd.short_info))
			temp_label.setWordWrap(True)
			temp_label.setMinimumWidth(short_info_min_width)
			temp_label.setMinimumHeight(short_info_min_height)
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin + title_col_span, short_info_row_span, short_info_col_span)
			
			grid_row += short_info_row_span
			
			# Add load paramaters button 
			self.load_params_btn = QPushButton("Load parameters")
			self.load_params_btn.setMinimumWidth(func_btn_min_width)
			self.load_params_btn.setToolTip("load gui parameter settings to retrieve a previously-saved one")
			self.connect(self.load_params_btn, SIGNAL("clicked()"), self.sxcmdwidget.load_params)
			grid_layout.addWidget(self.load_params_btn, grid_row, grid_col_origin, func_btn_row_span, func_btn_col_span)
			
		elif tab_group == "advanced":
			# Set a label and its position in this tab
			temp_label = QLabel("<b>%s</b>" % (self.sxcmdwidget.sxcmd.get_mode_name_for("human")))
			temp_label.setMinimumWidth(title_label_min_width)
			temp_label.setMinimumHeight(title_label_min_height)
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin, title_row_span, title_col_span)
			
			temp_label = QLabel("Set advanced parameters", self)
			temp_label.setWordWrap(True)
			temp_label.setMinimumWidth(short_info_min_width)
			temp_label.setMinimumHeight(short_info_min_height)
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin + title_col_span, short_info_row_span, short_info_col_span)
		
		# Add space
		grid_row += 2
		
		# Add widget for editing command args and options
		for cmd_token in self.sxcmdwidget.sxcmd.token_list:
			if cmd_token.group == tab_group:
				
				# First, handle very special cases
				if cmd_token.type == "function":
					n_widgets = 2 # function type has two line edit boxes
					cmd_token_widget = [None] * n_widgets
					cmd_token_restore_widget = [None] * n_widgets
					
					# Create widgets for user function name
					widget_index = 0
					temp_label = QLabel(cmd_token.label[widget_index])
					temp_label.setMinimumWidth(token_label_min_width)
					grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
					
					assert(cmd_token.is_required == False)
					cmd_token_restore_widget[widget_index] = QPushButton("%s" % cmd_token.restore[widget_index])
					cmd_token_restore_widget[widget_index].setToolTip(default_cmd_token_restore_tooltip)
					grid_layout.addWidget(cmd_token_restore_widget[widget_index], grid_row, grid_col_origin + token_label_col_span, token_widget_row_span, token_widget_col_span)
					
					# cmd_token_widget[widget_index] = QLineEdit(self)
					cmd_token_widget[widget_index] = QLineEdit()
					cmd_token_widget[widget_index].setText(cmd_token.restore[widget_index])
					cmd_token_widget[widget_index].setToolTip(cmd_token.help[widget_index])
					grid_layout.addWidget(cmd_token_widget[widget_index], grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
					
					self.connect(cmd_token_restore_widget[widget_index], SIGNAL("clicked()"), partial(self.handle_restore_widget_event, cmd_token, widget_index))
					
					grid_row +=  1
					
					# Create widgets for external file path containing above user function
					widget_index = 1
					temp_label = QLabel(cmd_token.label[widget_index])
					grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
					
					assert(cmd_token.is_required == False)
					cmd_token_restore_widget[widget_index] = QPushButton("%s" % cmd_token.restore[widget_index])
					cmd_token_restore_widget[widget_index].setToolTip(default_cmd_token_restore_tooltip)
					grid_layout.addWidget(cmd_token_restore_widget[widget_index], grid_row, grid_col_origin + token_label_col_span, token_widget_row_span, token_widget_col_span)
					
					cmd_token_widget[widget_index] = QLineEdit()
					cmd_token_widget[widget_index].setText(cmd_token.restore[widget_index]) # Because default user functions is internal
					cmd_token_widget[widget_index].setToolTip(cmd_token.help[widget_index])
					grid_layout.addWidget(cmd_token_widget[widget_index], grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
					
					self.connect(cmd_token_restore_widget[widget_index], SIGNAL("clicked()"), partial(self.handle_restore_widget_event, cmd_token, widget_index))
					
					file_format = "py"
					temp_btn = QPushButton("Select Script")
					temp_btn.setToolTip("display open file dailog to select .%s python script file" % file_format)
					grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
					self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget[widget_index], file_format))
					
					grid_row +=  1
					
#					temp_label = QLabel(cmd_token.help[widget_index])
#					grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
#					
#					grid_row +=  1
					
				# Then, handle the other cases
				else:
					# Create label widget 
					temp_label = QLabel(cmd_token.label)
					temp_label.setMinimumWidth(token_label_min_width)
					grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
					
					# Create widget and associate it to this cmd_token
					cmd_token_widget = None
					cmd_token_restore_widget = None
					cmd_token_restore_tooltip = default_cmd_token_restore_tooltip
					if cmd_token.type == "bool":
						btn_name = "NO"
						is_btn_enable = True
						custom_style = "QPushButton {color:gray; }"
						if cmd_token.restore:
							btn_name = "YES"
						if cmd_token.type in parent.sxconst_set.dict.keys():
							custom_style = "QPushButton {color:green; }"
							cmd_token_restore_tooltip = const_cmd_token_restore_tooltip
						elif cmd_token.is_required:
							btn_name = "required"
							custom_style = "QPushButton {color:red; }"
							is_btn_enable = False
							cmd_token_restore_tooltip = required_cmd_token_restore_tooltip
						cmd_token_restore_widget = QPushButton("%s" % btn_name)
						cmd_token_restore_widget.setStyleSheet(custom_style)
						cmd_token_restore_widget.setEnabled(is_btn_enable)
						grid_layout.addWidget(cmd_token_restore_widget, grid_row, grid_col_origin + token_label_col_span, token_widget_row_span, token_widget_col_span)
						
						# construct new widget(s) for this command token
						cmd_token_widget = QCheckBox("")
						if cmd_token.restore == True:
							cmd_token_widget.setCheckState(Qt.Checked)
						else:
							cmd_token_widget.setCheckState(Qt.Unchecked)
						cmd_token_widget.setEnabled(is_btn_enable)
						grid_layout.addWidget(cmd_token_widget, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
						
						self.connect(cmd_token_restore_widget, SIGNAL("clicked()"), partial(self.handle_restore_widget_event, cmd_token))
						
					else:
						btn_name = "%s" % cmd_token.restore
						custom_style = "QPushButton {color:gray; }"
						is_btn_enable = True
						if cmd_token.type in parent.sxconst_set.dict.keys():
							custom_style = "QPushButton {color:green; }"
							cmd_token_restore_tooltip = const_cmd_token_restore_tooltip
						elif cmd_token.is_required:
							btn_name = "required"
							custom_style = "QPushButton {color:red; }"
							is_btn_enable = False
							cmd_token_restore_tooltip = required_cmd_token_restore_tooltip
						cmd_token_restore_widget = QPushButton("%s" % btn_name)
						cmd_token_restore_widget.setStyleSheet(custom_style)
						cmd_token_restore_widget.setEnabled(is_btn_enable)
						grid_layout.addWidget(cmd_token_restore_widget, grid_row, grid_col_origin + token_label_col_span, token_widget_row_span, token_widget_col_span)
						
						cmd_token_widget = QLineEdit()
						cmd_token_widget.setText(cmd_token.restore)
						grid_layout.addWidget(cmd_token_widget, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
						
						self.connect(cmd_token_restore_widget, SIGNAL("clicked()"), partial(self.handle_restore_widget_event, cmd_token))
						
						if cmd_token.type == "image":
							file_format = "hdf"
							temp_btn = QPushButton("Select .%s" % file_format)
							temp_btn.setToolTip("display open file dailog to select .%s format image file" % file_format)
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget, file_format))
							file_format = "bdb"
							temp_btn = QPushButton("Select .%s" % file_format)
							temp_btn.setToolTip("display open file dailog to select .%s format image file" % file_format)
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 3, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget, file_format))
						elif cmd_token.type == "any_image":
							temp_btn = QPushButton("Select Image")
							temp_btn.setToolTip("display open file dailog to select standard format image file (e.g. .hdf, .mrc)")
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget))
						elif cmd_token.type == "any_file_list":
							temp_btn = QPushButton("Select Files")
							temp_btn.setToolTip("display open file dailog to select files (e.g. *.*)")
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget, cmd_token.type))
						elif cmd_token.type == "any_image_list":
							temp_btn = QPushButton("Select Images")
							temp_btn.setToolTip("display open file dailog to select standard format image files (e.g. .hdf, .mrc)")
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget, cmd_token.type))
						elif cmd_token.type == "bdb":
							file_format = "bdb"
							temp_btn = QPushButton("Select .%s" % file_format)
							temp_btn.setToolTip("display open file dailog to select .%s format image file" % file_format)
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget, file_format))
						elif cmd_token.type == "pdb":
							file_format = "pdb"
							temp_btn = QPushButton("Select .%s" % file_format)
							temp_btn.setToolTip("display open file dailog to select .%s format image file" % file_format)
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span* 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget, file_format))
						elif cmd_token.type == "mrc":
							file_format = "mrc"
							temp_btn = QPushButton("Select .%s" % file_format)
							temp_btn.setToolTip("display open file dailog to select .%s format image file" % file_format)
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span* 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget, file_format))
						elif cmd_token.type == "parameters":
							temp_btn = QPushButton("Select Parameter")
							temp_btn.setToolTip("display open file dailog to select parameter file (e.g. .txt)")
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget))
						elif cmd_token.type == "any_file":
							temp_btn = QPushButton("Select File")
							temp_btn.setToolTip("display open file dailog to select file (e.g. *.*)")
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, cmd_token_widget))
						elif cmd_token.type == "directory":
							temp_btn = QPushButton("Select directory")
							temp_btn.setToolTip("display select directory dailog")
							grid_layout.addWidget(temp_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
							self.connect(temp_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_dir, cmd_token_widget))
						# elif cmd_token.type == "output":
						# else:
						# 	if cmd_token.type not in ["int", "float", "string", "apix", "wn", "box", "radius", "sym"]: ERROR("Logical Error: Encountered unsupported type (%s). Consult with the developer."  % cmd_token.type, "%s in %s" % (__name__, os.path.basename(__file__)))
							
					cmd_token_widget.setToolTip(cmd_token.help)
					cmd_token_restore_widget.setToolTip(cmd_token_restore_tooltip)
					
					grid_row += 1
				
				# Register this widget
				cmd_token.widget = cmd_token_widget
				cmd_token.restore_widget = cmd_token_restore_widget
		
		if tab_group == "main":
			# Add space
			grid_row += 1
			
			# Add gui components for MPI related paramaters
			temp_label = QLabel("MPI processors")
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
			
			# self.mpi_nproc_edit = QLineEdit(self)
			self.mpi_nproc_edit = QLineEdit()
			self.mpi_nproc_edit.setText("1")
			self.mpi_nproc_edit.setToolTip("number of processors to use. default is single processor mode")
			grid_layout.addWidget(self.mpi_nproc_edit, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
			
			grid_row += 1
			
			temp_label = QLabel("MPI command line template")
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
			
			self.mpi_cmd_line_edit = QLineEdit()
			self.mpi_cmd_line_edit.setText("")
			self.mpi_cmd_line_edit.setToolTip("template of MPI command line (e.g. \"mpirun -np XXX_SXMPI_NPROC_XXX --host n0,n1,n2 XXX_SXCMD_LINE_XXX\"). if empty, use \"mpirun -np XXX_SXMPI_NPROC_XXX XXX_SXCMD_LINE_XXX\"")
			grid_layout.addWidget(self.mpi_cmd_line_edit, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
			
			grid_row += 1
			
			# If MPI is not supported, disable this widget
			self.set_text_entry_widget_enable_state(self.mpi_nproc_edit, self.sxcmdwidget.sxcmd.mpi_support)
			self.set_text_entry_widget_enable_state(self.mpi_cmd_line_edit, self.sxcmdwidget.sxcmd.mpi_support)
			
			# Add gui components for queue submission (qsub)
			is_qsub_enabled = False
			temp_label = QLabel("submit job to queue")
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
			
			self.qsub_enable_checkbox = QCheckBox("")
			if is_qsub_enabled == True:
				self.qsub_enable_checkbox.setCheckState(Qt.Checked)
			else: # assert(is_qsub_enabled == False)
				self.qsub_enable_checkbox.setCheckState(Qt.Unchecked)
			self.qsub_enable_checkbox.setToolTip("submit job to queue")
			self.qsub_enable_checkbox.stateChanged.connect(self.set_qsub_enable_state) # To control enable state of the following qsub related widgets
			self.qsub_enable_checkbox.setEnabled(self.sxcmdwidget.sxcmd.is_submittable)
			grid_layout.addWidget(self.qsub_enable_checkbox, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
			
			grid_row += 1
			
			temp_label = QLabel("job name")
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
			
			self.qsub_job_name_edit = QLineEdit()
			if self.sxcmdwidget.sxcmd.is_submittable == True:
				self.qsub_job_name_edit.setText(self.sxcmdwidget.sxcmd.get_mode_name_for("file_path"))
			else: # assert(self.sxcmdwidget.sxcmd.is_submittable == False)
				assert(self.sxcmdwidget.sxcmd.mpi_support == False)
				self.qsub_job_name_edit.setText("N/A")
			self.qsub_job_name_edit.setToolTip("name of this job")
			grid_layout.addWidget(self.qsub_job_name_edit, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
			
			grid_row += 1
			
			temp_label = QLabel("submission command")
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
			
			self.qsub_cmd_edit = QLineEdit()
			if self.sxcmdwidget.sxcmd.is_submittable == True:
				self.qsub_cmd_edit.setText("qsub")
			else: # assert(self.sxcmdwidget.sxcmd.is_submittable == False)
				assert(self.sxcmdwidget.sxcmd.mpi_support == False)
				self.qsub_cmd_edit.setText("N/A")
			self.qsub_cmd_edit.setToolTip("name of submission command to queue job")
			grid_layout.addWidget(self.qsub_cmd_edit, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
			
			grid_row += 1
			
			temp_label = QLabel("submission script template")
			grid_layout.addWidget(temp_label, grid_row, grid_col_origin, token_label_row_span, token_label_col_span)
			
			self.qsub_script_edit = QLineEdit()
			if self.sxcmdwidget.sxcmd.is_submittable == True:
				self.qsub_script_edit.setText("msgui_qsub.sh")
			else: # assert(self.sxcmdwidget.sxcmd.is_submittable == False)
				assert(self.sxcmdwidget.sxcmd.mpi_support == False)
				self.qsub_script_edit.setText("N/A")
			self.qsub_script_edit.setToolTip("file name of submission script template (e.g. $EMAN2DIR/bin/msgui_qsub.sh)")
			grid_layout.addWidget(self.qsub_script_edit, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span, token_widget_row_span, token_widget_col_span)
			
			self.qsub_script_open_btn = QPushButton("Select Template")
			self.qsub_script_open_btn.setToolTip("display open file dailog to select job submission script template file")
			self.connect(self.qsub_script_open_btn, SIGNAL("clicked()"), partial(self.sxcmdwidget.select_file, self.qsub_script_edit))
			grid_layout.addWidget(self.qsub_script_open_btn, grid_row, grid_col_origin + token_label_col_span + token_widget_col_span * 2, token_widget_row_span, token_widget_col_span)
			
			grid_row += 1
			
			# Initialize enable state of qsub related widgets
			self.set_qsub_enable_state()
			
			# Add space
			grid_row += 1
			
			# Add save paramaters button 
			self.save_params_btn = QPushButton("Save parameters")
			self.save_params_btn.setMinimumWidth(func_btn_min_width)
			self.save_params_btn.setToolTip("save gui parameter settings")
			self.connect(self.save_params_btn, SIGNAL("clicked()"), self.sxcmdwidget.save_params)
			grid_layout.addWidget(self.save_params_btn, grid_row, grid_col_origin, func_btn_row_span, func_btn_col_span)
			
			grid_row += 1
			
			self.cmd_line_btn = QPushButton("Generate command line")
			self.cmd_line_btn.setMinimumWidth(func_btn_min_width)
			self.cmd_line_btn.setToolTip("generate command line from gui parameter settings and automatically save settings")
			self.connect(self.cmd_line_btn, SIGNAL("clicked()"), self.sxcmdwidget.print_cmd_line)
			grid_layout.addWidget(self.cmd_line_btn, grid_row, grid_col_origin, func_btn_row_span, func_btn_col_span)
			
			grid_row += 1
			
			# Add a run button
			self.execute_btn = QPushButton("Run %s" % self.sxcmdwidget.sxcmd.get_mode_name_for("human"))
			# make 3D textured push button look
			custom_style = "QPushButton {font: bold; color: #000;border: 1px solid #333;border-radius: 11px;padding: 2px;background: qradialgradient(cx: 0, cy: 0,fx: 0.5, fy:0.5,radius: 1, stop: 0 #fff, stop: 1 #8D0);min-width:90px;margin:5px} QPushButton:pressed {font: bold; color: #000;border: 1px solid #333;border-radius: 11px;padding: 2px;background: qradialgradient(cx: 0, cy: 0,fx: 0.5, fy:0.5,radius: 1, stop: 0 #fff, stop: 1 #084);min-width:90px;margin:5px} QPushButton:focus {font: bold; color: #000;border: 2px solid #8D0;border-radius: 11px;padding: 2px;background: qradialgradient(cx: 0, cy: 0,fx: 0.5, fy:0.5,radius: 1, stop: 0 #fff, stop: 1 #8D0);min-width:90px;margin:5px}"
			self.execute_btn.setStyleSheet(custom_style)
			self.execute_btn.setMinimumWidth(func_btn_min_width)
			self.execute_btn.setToolTip("run %s and automatically save gui parameter settings" % self.sxcmdwidget.sxcmd.get_mode_name_for("human"))
			self.connect(self.execute_btn, SIGNAL("clicked()"), self.sxcmdwidget.execute_cmd_line)
			grid_layout.addWidget(self.execute_btn, grid_row, grid_col_origin + func_btn_col_span, func_btn_row_span, func_btn_col_span)
	
	def set_text_entry_widget_enable_state(self, widget, is_enabled):
		# Set enable state and background color of text entry widget according to enable state
		default_palette = QPalette()
		bg_color = default_palette.color(QPalette.Inactive, QPalette.Base)
		if is_enabled == False:
			bg_color = default_palette.color(QPalette.Disabled, QPalette.Base)
		
		widget.setEnabled(is_enabled)
		palette = widget.palette()
		palette.setColor(widget.backgroundRole(), bg_color)
		widget.setPalette(palette)
	
	def set_qsub_enable_state(self):
		is_enabled = False
		if self.qsub_enable_checkbox.checkState() == Qt.Checked:
			is_enabled = True
		
		# Set enable state and background color of mpi related widgets
		if self.sxcmdwidget.sxcmd.mpi_support:
			self.set_text_entry_widget_enable_state(self.mpi_cmd_line_edit, not is_enabled)
		
		# Set enable state and background color of qsub related widgets
		self.set_text_entry_widget_enable_state(self.qsub_job_name_edit, is_enabled)
		self.set_text_entry_widget_enable_state(self.qsub_cmd_edit, is_enabled)
		self.set_text_entry_widget_enable_state(self.qsub_script_edit, is_enabled)
		self.qsub_script_open_btn.setEnabled(is_enabled)
	
	def handle_restore_widget_event(self, sxcmd_token, widget_index=0):
		if sxcmd_token.type == "function":
			assert(len(sxcmd_token.widget) == 2 and len(sxcmd_token.restore) == 2 and widget_index < 2)
			sxcmd_token.widget[widget_index].setText("%s" % sxcmd_token.restore[widget_index])
		else:
			if sxcmd_token.type == "bool":
				if sxcmd_token.restore == "YES":
					sxcmd_token.widget.setChecked(Qt.Checked)
				else: # sxcmd_token.restore == "NO"
					sxcmd_token.widget.setChecked(Qt.Unchecked)
			else:
				sxcmd_token.widget.setText("%s" % sxcmd_token.restore)

# ========================================================================================
# Command Category Widget (opened by class SXMainWindow)
class SXCmdCategoryWidget(QWidget):
	def __init__(self, sxconst_set, sxcmd_category, parent = None):
		super(SXCmdCategoryWidget, self).__init__(parent)
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		self.sxconst_set = sxconst_set
		self.sxcmd_category = sxcmd_category
		self.cur_sxcmd = None
		
		# Layout constants
		self.sxcmd_btn_row_span = 1
		self.sxcmd_btn_col_span = 1
		
		self.sxcmd_btn_area_row_span = self.sxcmd_btn_row_span * SXLookFeelConst.expected_cmd_counts
		self.sxcmd_btn_area_col_span = self.sxcmd_btn_col_span
		
		self.sxcmd_widget_area_row_span = self.sxcmd_btn_area_row_span
		self.sxcmd_widget_area_col_span = 1
		
		self.grid_row_origin = 0
		self.grid_col_origin = 0
		
		# Layout variables
		self.grid_layout = None # grid layout
		
		self.grid_row = self.grid_row_origin # Keep current row
		self.grid_col = self.grid_col_origin # keep current column
		
		self.sxcmd_btn_group = None
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		
		# --------------------------------------------------------------------------------
		# Setup Window Layout
		# --------------------------------------------------------------------------------
		self.setup_layout(QBrush(SXLookFeelConst.default_bg_color))
		
		# --------------------------------------------------------------------------------
		# Add SX Commands (sx*.py) associated widgets
		# --------------------------------------------------------------------------------
		self.add_sxcmd_widgets()
		
		# --------------------------------------------------------------------------------
		# Load the previously saved parameter setting of this sx command
		# Override the registration of project constant parameter settings with the previously-saved one
		# --------------------------------------------------------------------------------
		for sxcmd in self.sxcmd_category.cmd_list:
			if os.path.exists(sxcmd.widget.gui_settings_file_path):
				sxcmd.widget.read_params(sxcmd.widget.gui_settings_file_path)
		
		# --------------------------------------------------------------------------------
		# Alway select the 1st entry of the command list upon startup
		# --------------------------------------------------------------------------------
		self.handle_sxcmd_btn_event(self.sxcmd_category.cmd_list[0])
	
	def setup_layout(self, background_brush):
		# Setup background color of this widget
		self.setAutoFillBackground(True)
		palette = QPalette()
		palette.setBrush(QPalette.Background, background_brush)
		self.setPalette(palette)
		
		# Setup grid layout in the scroll area
		self.grid_layout = QGridLayout(self)
		self.grid_layout.setMargin(SXLookFeelConst.grid_margin)
		self.grid_layout.setSpacing(SXLookFeelConst.grid_spacing)
		self.grid_layout.setColumnMinimumWidth(0, SXLookFeelConst.sxcmd_btn_area_min_width)
		self.grid_layout.setColumnMinimumWidth(1, SXLookFeelConst.sxcmd_widget_area_min_width)
		# Give the column of the command settings area a higher stretch priority so that the other area does not stretch horizontally
		self.grid_layout.setColumnStretch(self.grid_col_origin + self.sxcmd_btn_area_col_span, self.grid_layout.columnStretch(self.grid_col_origin + self.sxcmd_btn_area_col_span) + 1)
		
	# Add Pipeline SX Commands (sx*.py) associated widgets
	def add_sxcmd_widgets(self):
		self.sxcmd_btn_group = QButtonGroup()
		# self.sxcmd_btn_group.setExclusive(True) # NOTE: 2016/02/18 Toshio Moriya: Without QPushButton.setCheckable(True). This does not do anything. Let manually do this
		
		current_role = None
		
		# Add SX Commands (sx*.py) associated widgets
		for sxcmd in self.sxcmd_category.cmd_list:
			if sxcmd.role != current_role:
				# Add title label and set position and font style
				label_text = ""
				if sxcmd.role == "sxr_pipe":
					label_text = "COMMANDS"
				elif sxcmd.role == "sxr_alt":
					label_text = "ALTERNATIVES"
				elif sxcmd.role == "sxr_util":
					label_text = "UTILITIES"
				else:
					label_text = "UNKNOWN"
				
				if current_role !=  None:
					self.grid_row += 1
				
				# title=QLabel("<span style=\'font-size:18pt; font-weight:600; color:#aa0000;\'><b>%s </b></span><span style=\'font-size:12pt; font-weight:60; color:#aa0000;\'>(shift-click for wiki)</span>" % label_text)
				title=QLabel("<span style=\'font-size:18pt; font-weight:600; color:#000000;\'><b>%s </b></span><span style=\'font-size:12pt; font-weight:60; color:#000000;\'>(shift-click for wiki)</span>" % label_text)
				self.grid_layout.addWidget(title, self.grid_row, self.grid_col_origin, self.sxcmd_btn_row_span, self.sxcmd_btn_col_span)
				
				self.grid_row += 1
				
				current_role = sxcmd.role
				
			# Add buttons for this sx*.py processe
			sxcmd.btn = QPushButton(sxcmd.label)
			# sxcmd.btn.setCheckable(True) # NOTE: 2016/02/18 Toshio Moriya: With this setting, we can not move the focus to the unchecked butttons... PyQt bug?
			sxcmd.btn.setToolTip(sxcmd.short_info)
			self.sxcmd_btn_group.addButton(sxcmd.btn)
			self.grid_layout.addWidget(sxcmd.btn, self.grid_row, self.grid_col_origin, self.sxcmd_btn_row_span, self.sxcmd_btn_col_span)
			
			# Create SXCmdWidget for this sx*.py processe
			sxcmd.widget = SXCmdWidget(self.sxconst_set, sxcmd)
			sxcmd.widget.hide()
			self.grid_layout.addWidget(sxcmd.widget, self.grid_row_origin, self.grid_col_origin + self.sxcmd_btn_area_col_span, self.sxcmd_widget_area_row_span, self.sxcmd_widget_area_col_span)
			
			# connect widget signals
			self.connect(sxcmd.btn, SIGNAL("clicked()"), partial(self.handle_sxcmd_btn_event, sxcmd))
			
			self.grid_row += 1
	
	def handle_sxcmd_btn_event(self, sxcmd):
		modifiers = QApplication.keyboardModifiers()
		if modifiers == Qt.ShiftModifier:
			os.system("python -m webbrowser %s%s" % (SPARX_DOCUMENTATION_WEBSITE, sxcmd.name))
			return
		
		if self.cur_sxcmd == sxcmd: return
		
		if self.cur_sxcmd != None:
			assert(self.cur_sxcmd.widget.isVisible() == True)
			self.cur_sxcmd.widget.hide()
			custom_style = "QPushButton {font: normal; color:black; }" # custom_style = "QPushButton {color:#000; }"
			self.cur_sxcmd.btn.setStyleSheet(custom_style)
			
		self.cur_sxcmd = sxcmd
		
		if self.cur_sxcmd != None:
			assert(self.cur_sxcmd.widget.isVisible() == False)
			self.cur_sxcmd.widget.show()
			custom_style = "QPushButton {font: bold; color:blue; }" # custom_style = "QPushButton {font: bold; color:#8D0; }"
			self.cur_sxcmd.btn.setStyleSheet(custom_style)
			
	def quit_all_child_applications(self):
		# Quit all child applications
		for sxcmd in self.sxcmd_category.cmd_list:
			sxcmd.widget.quit_all_child_applications()
	
# ========================================================================================
# Layout of the project constants parameters widget; owned by the main window
class SXConstSetWidget(QWidget):
	def __init__(self, sxconst_set, sxcmd_category_list, parent=None):
		super(SXConstSetWidget, self).__init__(parent)
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		self.sxconst_set = sxconst_set
		self.sxcmd_category_list = sxcmd_category_list
		
		self.gui_settings_file_path = "%s/gui_settings_project_settings.txt" % (SXLookFeelConst.project_dir)
		
		# Layout constants and variables
		global_row_origin = 0; global_col_origin = 0
		global_row_span = 4; global_col_span = 1
		
		header_row_origin = 0; header_col_origin = 0
		title_row_span = 1; title_col_span = 1
		short_info_row_span = 1; short_info_col_span = 1
		title_min_width = 300
		short_info_min_width = 300
		short_info_min_height = 80
		
		const_set_row_origin = 0; const_set_col_origin = 0
		const_label_row_span = 1; const_label_col_span = 1
		const_register_widget_row_span = 1; const_register_widget_col_span = 1
		const_widget_row_span = 1; const_widget_col_span = 1
		const_label_min_width = 150
		const_register_widget_min_width = const_label_min_width
		const_widget_min_width = const_label_min_width
		
		btn_row_origin = 0; btn_col_origin = 0
		func_btn_row_span = 1; func_btn_col_span = 1
		register_btn_row_span = 1; register_btn_col_span = 2
		func_btn_min_width = 150
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		
		# Set the background color of this widget
		self.setAutoFillBackground(True)
		palette = QPalette()
		palette.setBrush(QPalette.Background, QBrush(SXLookFeelConst.default_bg_color))
		self.setPalette(palette)
		
		global_layout = QGridLayout(self)
		global_layout.setMargin(SXLookFeelConst.grid_margin)
		global_layout.setSpacing(SXLookFeelConst.grid_spacing)
		global_layout.setRowStretch(global_row_span - 1, global_layout.rowStretch(global_row_origin) + 1)
		
		header_layout = QGridLayout()
		header_layout.setMargin(SXLookFeelConst.grid_margin)
		header_layout.setSpacing(SXLookFeelConst.grid_spacing)
		
		const_set_layout = QGridLayout()
		const_set_layout.setMargin(SXLookFeelConst.grid_margin)
		const_set_layout.setSpacing(SXLookFeelConst.grid_spacing)
		
		btn_layout = QGridLayout()
		btn_layout.setMargin(SXLookFeelConst.grid_margin)
		btn_layout.setSpacing(SXLookFeelConst.grid_spacing * 2)
		
		global_grid_row = global_row_origin
		
		# Start add title widgets to the grid layout
		header_grid_row = header_row_origin
		
		# Set a label and its position in this tab
		temp_label = QLabel("<b>%s</b>" % (self.sxconst_set.label))
		temp_label.setMinimumWidth(title_min_width)
		header_layout.addWidget(temp_label, header_grid_row, header_col_origin, title_row_span, title_col_span)
		
		header_grid_row += 1
		
		# NOTE: 2015/11/17 Toshio Moriya
		# Necessary to separate "<b>%s</b>" from the information for avoiding to invoke the tag interpretations of string
		# e.g. < becomes the escape character
		temp_label = QLabel("%s" % (self.sxconst_set.short_info))
		temp_label.setWordWrap(True)
		temp_label.setMinimumWidth(short_info_min_width)
		temp_label.setMinimumHeight(short_info_min_height)
		header_layout.addWidget(temp_label, header_grid_row, header_col_origin, short_info_row_span, short_info_col_span)
		
		# Add const set grid layout to global layout
		global_layout.addLayout(header_layout, global_grid_row, global_col_origin)
		global_grid_row += 1
		
		# Start add project parameter constant widgets to the grid layout
		const_set_grid_row = const_set_row_origin
		
		# Add widget for editing command args and options
		for sxconst in self.sxconst_set.list:
			# Create widget associated to this project constant parameter
			temp_label = QLabel(sxconst.label)
			temp_label.setMinimumWidth(const_label_min_width)
			const_set_layout.addWidget(temp_label, const_set_grid_row, const_set_col_origin, const_label_row_span, const_label_col_span)
			
			sxconst_register_widget = QPushButton("%s" % sxconst.register)
			sxconst_register_widget.setMinimumWidth(const_register_widget_min_width)
			custom_style = "QPushButton {color:green; }"
			sxconst_register_widget.setStyleSheet(custom_style)
			const_set_layout.addWidget(sxconst_register_widget, const_set_grid_row, const_set_row_origin + const_label_col_span, const_register_widget_row_span, const_register_widget_col_span)
			sxconst_register_widget.setToolTip("retrieve this registered value to edit box")
			self.connect(sxconst_register_widget, SIGNAL("clicked()"), partial(self.handle_regster_widget_event, sxconst))
			
			sxconst_widget = QLineEdit()
			sxconst_widget.setMinimumWidth(const_widget_min_width)
			sxconst_widget.setText(sxconst.register)
			sxconst_widget.setToolTip(sxconst.help)
			const_set_layout.addWidget(sxconst_widget, const_set_grid_row, const_set_row_origin + const_label_col_span + const_register_widget_col_span, const_widget_row_span, const_widget_col_span)
			
			const_set_grid_row += 1
			
			# Register this widget
			sxconst.register_widget = sxconst_register_widget
			sxconst.widget = sxconst_widget
		
		# Add const set grid layout to global layout
		global_layout.addLayout(const_set_layout, global_grid_row, global_col_origin)
		global_grid_row += 1
		
		# Start add buttons to the grid layout
		btn_grid_row = btn_row_origin
		
		# Add a register button
		self.execute_btn = QPushButton("Register settings")
		# make 3D textured push button look
		custom_style = "QPushButton {font: bold; color: #000;border: 1px solid #333;border-radius: 11px;padding: 2px;background: qradialgradient(cx: 0, cy: 0,fx: 0.5, fy:0.5,radius: 1, stop: 0 #fff, stop: 1 #8D0);min-width:90px;margin:5px} QPushButton:pressed {font: bold; color: #000;border: 1px solid #333;border-radius: 11px;padding: 2px;background: qradialgradient(cx: 0, cy: 0,fx: 0.5, fy:0.5,radius: 1, stop: 0 #fff, stop: 1 #084);min-width:90px;margin:5px}"
		self.execute_btn.setStyleSheet(custom_style)
		self.execute_btn.setMinimumWidth(func_btn_min_width * register_btn_col_span)
		self.execute_btn.setToolTip("register project constant parameter settings to automatically set values to command arguments and options")
		self.connect(self.execute_btn, SIGNAL("clicked()"), self.register_const_set)
		btn_layout.addWidget(self.execute_btn, btn_grid_row, btn_col_origin, register_btn_row_span, register_btn_col_span)
		
		btn_grid_row += 1
		
		# Add save project constant parameter settings button 
		self.save_consts_btn = QPushButton("Save settings")
		self.save_consts_btn.setMinimumWidth(func_btn_min_width)
		self.save_consts_btn.setToolTip("save project constant parameter settings")
		self.connect(self.save_consts_btn, SIGNAL("clicked()"), self.save_consts)
		btn_layout.addWidget(self.save_consts_btn, btn_grid_row, btn_col_origin, func_btn_row_span, func_btn_col_span)
		
		# Add load project constant parameter settings button 
		self.load_consts_btn = QPushButton("Load settings")
		self.load_consts_btn.setMinimumWidth(func_btn_min_width)
		self.load_consts_btn.setToolTip("load project constant parameter settings to retrieve the previously-saved one")
		self.connect(self.load_consts_btn, SIGNAL("clicked()"), self.load_consts)
		btn_layout.addWidget(self.load_consts_btn, btn_grid_row, btn_col_origin + func_btn_col_span, func_btn_row_span, func_btn_col_span)
		
		btn_grid_row += 1
		
		# Add button grid layout to global layout
		global_layout.addLayout(btn_layout, global_grid_row, global_col_origin)
		
		# Load the previously saved parameter setting of this sx command
		if os.path.exists(self.gui_settings_file_path):
			self.read_consts(self.gui_settings_file_path)
	
	def handle_regster_widget_event(self, sxconst):
		sxconst.widget.setText(sxconst.register)
		
	def register_const_set(self):
		# Loop through all project constant parameters
		for sxconst in self.sxconst_set.list:
			sxconst.register = sxconst.widget.text()
			sxconst.register_widget.setText("%s" % sxconst.register)
		
		# Loop through all command categories
		for sxcmd_category in self.sxcmd_category_list:
			# Loop through all commands of this category
			for sxcmd in sxcmd_category.cmd_list:
				# Loop through all command tokens of this command
				for cmd_token in sxcmd.token_list:
					if cmd_token.type in self.sxconst_set.dict.keys():
						sxconst = self.sxconst_set.dict[cmd_token.type]
						cmd_token.restore = sxconst.register
						cmd_token.restore_widget.setText("%s" % cmd_token.restore)
						cmd_token.widget.setText(cmd_token.restore)
						# print "MRK_DEBUG: %s, %s, %s, %s, %s" % (sxcmd.name, cmd_token.key_base, cmd_token.type, cmd_token.default, cmd_token.restore)
		
		# Save the current state of GUI settings
		if os.path.exists(SXLookFeelConst.project_dir) == False:
			os.mkdir(SXLookFeelConst.project_dir)
		self.write_consts(self.gui_settings_file_path)
	
	def write_consts(self, file_path_out):
		file_out = open(file_path_out,"w")
		
		# Write script name for consistency check upon loading
		file_out.write("@@@@@ project settings gui settings - ")
		file_out.write(EMANVERSION + " (GITHUB: " + DATESTAMP +")" )
		file_out.write(" @@@@@ \n")
		
		# Loop through all project constant parameters
		for sxconst in self.sxconst_set.list:
			# The other type has only one line edit box
			val_str = str(sxconst.widget.text())
			file_out.write("<%s> %s (registered %s) == %s \n" % (sxconst.key, sxconst.label, sxconst.register, val_str))
			
		file_out.close()
	
	def read_consts(self, file_path_in):
		file_in = open(file_path_in,"r")
		
		# Check if this parameter file is for this sx script
		line_in = file_in.readline()
		if line_in.find("@@@@@ project settings gui settings") != -1:
			n_function_type_lines = 2
			function_type_line_counter = 0
			# loop through the rest of lines
			for line_in in file_in:
				# Extract label (which should be left of "=="). Also strip the ending spaces
				label_in = line_in.split("==")[0].strip()
				# Extract value (which should be right of "=="). Also strip all spaces
				val_str_in = line_in.split("==")[1].strip() 
				
				# Extract key_base of this command token
				target_operator = "<"
				item_tail = label_in.find(target_operator)
				if item_tail != 0: 
					QMessageBox.warning(self, "Invalid Project Settings File Format", "Project settings entry should start from \"%s\" for entry key in line (%s). The format of this file might be corrupted. Please save the project settings file again." % (target_operator, line_in))
				label_in = label_in[item_tail + len(target_operator):].strip() # Get the rest of line
				target_operator = ">"
				item_tail = label_in.find(target_operator)
				if item_tail == -1: 
					QMessageBox.warning(self, "Invalid Project Settings File Format", "Project settings entry should have \"%s\" closing entry key in line (%s) The format of this file might be corrupted. Please save the project settings file again." % (target_operator, line_in))
				key = label_in[0:item_tail]
				# Get corresponding sxconst
				if key not in self.sxconst_set.dict.keys(): 
					QMessageBox.warning(self, "Invalid Project Settings File Format", "Invalid entry key for project settings \"%s\" is found in line (%s). This project settings file might be imcompatible with the current version. Please save the project settings file again." % (key, line_in))
				sxconst = self.sxconst_set.dict[key]
				sxconst.widget.setText(val_str_in)
				
		else:
			QMessageBox.warning(self, "Fail to load project settings", "The specified file is not project settings file.")
		
		file_in.close()
	
	def save_consts(self):
		file_path_out = str(QFileDialog.getSaveFileName(self, "Save settings", options = QFileDialog.DontUseNativeDialog))
		if file_path_out != "":
			self.write_consts(file_path_out)
	
	def load_consts(self):
		file_path_in = str(QFileDialog.getOpenFileName(self, "Load settings", options = QFileDialog.DontUseNativeDialog))
		if file_path_in != "":
			self.read_consts(file_path_in)

# ========================================================================================
# Layout of the information widget; owned by the main window
class SXInfoWidget(QWidget):
	def __init__(self, parent = None):
		super(SXInfoWidget, self).__init__(parent)
		
		# Set the background color of this widget
		self.setAutoFillBackground(True)
		palette = QPalette()
		palette.setBrush(QPalette.Background, QBrush(SXLookFeelConst.sxinfo_widget_bg_color))
		self.setPalette(palette)
		
		label_row_span = 1; label_col_span = 3
		close_row_span = 1; close_col_span = 1
		spacer_min_width = 12
		
		grid_layout = QGridLayout(self)
		grid_layout.setMargin(SXLookFeelConst.grid_margin)
		grid_layout.setSpacing(SXLookFeelConst.grid_spacing)
		
		grid_col = 0
		grid_row = 0; grid_layout.setRowMinimumHeight(grid_row, spacer_min_width)
		grid_row += 10; temp_label=QLabel("<span style=\'font-size:18pt; font-weight:600; color:#ffffff;\'><b>SPHIRE GUI Prototype</b></span>")
		temp_label.setAlignment(Qt.AlignHCenter)
		grid_layout.addWidget(temp_label, grid_row, grid_col, label_row_span, label_col_span)
		grid_row += 1; temp_label=QLabel("<span style=\'font-size:18pt; font-weight:600; color:#ffffff;\'><b>Author: Toshio Moriya</b></span>")
		temp_label.setAlignment(Qt.AlignHCenter)
		grid_layout.addWidget(temp_label, grid_row, grid_col, label_row_span, label_col_span)
		grid_row += 1; grid_layout.setRowMinimumHeight(grid_row, spacer_min_width)
		grid_row += 1; temp_label=QLabel("<span style=\'font-size:18pt; font-weight:600; color:#ffffff;\'><b>For more information visit:%s </b></span>" % SPARX_DOCUMENTATION_WEBSITE)
		temp_label.setAlignment(Qt.AlignHCenter)
		grid_layout.addWidget(temp_label, grid_row, grid_col, label_row_span, label_col_span)
		grid_row += 1; grid_layout.setRowMinimumHeight(grid_row, spacer_min_width)
		grid_row += 1; grid_layout.setRowMinimumHeight(grid_row, spacer_min_width)

# ========================================================================================
# Main Window (started by class SXApplication)
class SXMainWindow(QMainWindow): # class SXMainWindow(QWidget):
	
	def __init__(self, parent = None):
		super(SXMainWindow, self).__init__(parent)
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		# class variables
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		self.sxinfo = None
		self.sxconst_set = None
		self.sxcmd_category_list = None
		
		self.cur_sxmenu_item = None
		self.sxmenu_item_widget_stacked_layout = None
		
		# ><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><
		
		# --------------------------------------------------------------------------------
		# Construct menu items
		# --------------------------------------------------------------------------------
		self.construct_sxinfo()              # Construct application information
		self.construct_sxconst_set()         # Construct project constant set for project settings
		self.construct_sxcmd_category_list() # Construct list of categorised sxscript objects (extracted from associated wiki documents)
		
		# --------------------------------------------------------------------------------
		# Setup Window Layout
		# --------------------------------------------------------------------------------
		background_image_file_path = '{0}sxgui_background.png'.format(get_image_directory())
		
		# Central widget
		central_widget = QWidget(self)
		central_widget.setObjectName('central')
		central_widget.setStyleSheet(
			'QWidget#central {{border-image: url("{0}")}}'.format(background_image_file_path)
			)
		self.setCentralWidget(central_widget)
		
		# Layout for central widget
		central_layout = QHBoxLayout(central_widget)
		central_widget.setLayout(central_layout)
		
		# --------------------------------------------------------------------------------
		# Construct and add a widget for menu item button area (containing all menu item buttons)
		# --------------------------------------------------------------------------------
		sxmenu_item_btn_area_widget = SXMenuItemBtnAreaWidget(self.sxconst_set, self.sxcmd_category_list, self.sxinfo, central_widget)
		central_layout.addWidget(sxmenu_item_btn_area_widget)
		
		# --------------------------------------------------------------------------------
		# Construct and add widgets for menu item widget area (containing all menu item widgets)
		# --------------------------------------------------------------------------------
		# Stacked layout for sx menu item widgets area
		self.sxmenu_item_widget_stacked_layout = QStackedLayout()
		central_layout.addLayout(self.sxmenu_item_widget_stacked_layout, stretch = 1)
		
		# Construct and add widgets for sx command categories
		for sxcmd_category in self.sxcmd_category_list:
			# Create SXCmdCategoryWidget for this command category
			sxcmd_category.widget = SXCmdCategoryWidget(self.sxconst_set, sxcmd_category)
			self.sxmenu_item_widget_stacked_layout.addWidget(sxcmd_category.widget)
		
		# Construct and add a widget for project constants settings
		self.sxconst_set.widget = SXConstSetWidget(self.sxconst_set, self.sxcmd_category_list)
		self.sxmenu_item_widget_stacked_layout.addWidget(self.sxconst_set.widget)
		
		# Construct and add a widget for GUI application information
		self.sxinfo.widget = SXInfoWidget()
		self.sxmenu_item_widget_stacked_layout.addWidget(self.sxinfo.widget)
		
		# --------------------------------------------------------------------------------
		# Set up event handler of all menu item buttons
		# --------------------------------------------------------------------------------
		for sxcmd_category in self.sxcmd_category_list:
			sxcmd_category.btn.clicked.connect(partial(self.handle_sxmenu_item_btn_event, sxcmd_category))
		self.sxconst_set.btn.clicked.connect(partial(self.handle_sxmenu_item_btn_event, self.sxconst_set))
		self.sxinfo.btn.clicked.connect(partial(self.handle_sxmenu_item_btn_event, self.sxinfo))
		
		# --------------------------------------------------------------------------------
		# Register project constant parameter settings upon initialization
		# --------------------------------------------------------------------------------
		self.sxconst_set.widget.register_const_set()
		
		# --------------------------------------------------------------------------------
		# Display application information upon startup
		# --------------------------------------------------------------------------------
		self.sxmenu_item_widget_stacked_layout.setCurrentWidget(self.sxinfo.widget)
		
		# --------------------------------------------------------------------------------
		# Get focus to main window
		# --------------------------------------------------------------------------------
		self.setFocus()
		
	def construct_sxinfo(self):
		sxinfo = SXmenu_item(); sxinfo.name = "GUI Information"; sxinfo.label = "GUI Appliation Information"; sxinfo.short_info = "DUMMY STRING"
		
		# Store GUI application information as a class data member
		self.sxinfo = sxinfo
		
	def construct_sxconst_set(self):
		sxconst_set = SXconst_set(); sxconst_set.name = "sxc_project_settings"; sxconst_set.label = "Project Settings"; sxconst_set.short_info = "Set constant parameter values for this project. These constants will be used as default values of associated arugments and options in command settings. However, the setting here is not required to run commands."
		sxconst = SXconst(); sxconst.key = "protein"; sxconst.label = "protein name"; sxconst.help = "a valid string for file names on your OS."; sxconst.register = "MY_PROTEIN"; sxconst.type = "string"; sxconst_set.list.append(sxconst); sxconst_set.dict[sxconst.key] = sxconst
		sxconst = SXconst(); sxconst.key = "apix"; sxconst.label = "micrograph pixel size [A]"; sxconst.help = ""; sxconst.register = "1.0"; sxconst.type = "float"; sxconst_set.list.append(sxconst); sxconst_set.dict[sxconst.key] = sxconst
		sxconst = SXconst(); sxconst.key = "ctfwin"; sxconst.label = "CTF window size [pixels]"; sxconst.help = "it should be slightly larger than particle box size"; sxconst.register = "512"; sxconst.type = "int"; sxconst_set.list.append(sxconst); sxconst_set.dict[sxconst.key] = sxconst
		sxconst = SXconst(); sxconst.key = "box"; sxconst.label = "particle box size [pixels]" ; sxconst.help = ""; sxconst.register = "-1"; sxconst.type = "int"; sxconst_set.list.append(sxconst); sxconst_set.dict[sxconst.key] = sxconst
		sxconst = SXconst(); sxconst.key = "radius"; sxconst.label = "protein particle radius [pixels]"; sxconst.help = ""; sxconst.register = "-1"; sxconst.type = "int"; sxconst_set.list.append(sxconst); sxconst_set.dict[sxconst.key] = sxconst
		sxconst = SXconst(); sxconst.key = "sym"; sxconst.label = "point-group symmetry"; sxconst.help = "e.g. c1, c4, d5"; sxconst.register = "c1"; sxconst.type = "string"; sxconst_set.list.append(sxconst); sxconst_set.dict[sxconst.key] = sxconst
		sxconst = SXconst(); sxconst.key = "mass"; sxconst.label = "protein molecular mass [kDa]"; sxconst.help = ""; sxconst.register = "-1.0"; sxconst.type = "float"; sxconst_set.list.append(sxconst); sxconst_set.dict[sxconst.key] = sxconst
		sxconst = SXconst(); sxconst.key = "config"; sxconst.label = "imaging configrations"; sxconst.help = "a free-style string for your record. please use it to describe the set of imaging configrations used in this project (e.g. types of microscope, detector, enegy filter, abbration corrector, phase plate, and etc."; sxconst.register = "MY_MICROSCOPE"; sxconst.type = "int"; sxconst_set.list.append(sxconst); sxconst_set.dict[sxconst.key] = sxconst
		
		# Store the project constant parameter set as a class data member
		self.sxconst_set = sxconst_set
		
	def construct_sxcmd_category_list(self):
		sxcmd_category_list = []
		sxcmd_list = []           # Used only within this function
		sxcmd_category_dict = {}  # Used only within this function
		
		# Actual configurations of all sx command categories and sx commands are inserted into the following section by wikiparser.py
		# as sxcmd_category_list and sxcmd_list
		# @@@@@ START_INSERTION @@@@@
		sxcmd_category = SXcmd_category(); sxcmd_category.name = "sxc_movie_micrograph"; sxcmd_category.label = "Movie Micrograph"; sxcmd_category.short_info = "movie frame alignemnt, and drift assessment"
		sxcmd_category_list.append(sxcmd_category)
		sxcmd_category = SXcmd_category(); sxcmd_category.name = "sxc_ctf"; sxcmd_category.label = "CTF"; sxcmd_category.short_info = "ctf estinatim, and ctf assessment"
		sxcmd_category_list.append(sxcmd_category)
		sxcmd_category = SXcmd_category(); sxcmd_category.name = "sxc_particle_stack"; sxcmd_category.label = "Particle Stack"; sxcmd_category.short_info = "particle picking, and particle windowing"
		sxcmd_category_list.append(sxcmd_category)
		sxcmd_category = SXcmd_category(); sxcmd_category.name = "sxc_2d_clustering"; sxcmd_category.label = "2D Clustering"; sxcmd_category.short_info = "2d clustering with isac, and post-processing"
		sxcmd_category_list.append(sxcmd_category)
		sxcmd_category = SXcmd_category(); sxcmd_category.name = "sxc_initial_3d_modeling"; sxcmd_category.label = "Initial 3D Modeling"; sxcmd_category.short_info = "initial 3d modeling with viper/rviper"
		sxcmd_category_list.append(sxcmd_category)
		sxcmd_category = SXcmd_category(); sxcmd_category.name = "sxc_3d_refinement"; sxcmd_category.label = "3D Refinement"; sxcmd_category.short_info = "3d refinement, post-processing, local resolution, and local filter"
		sxcmd_category_list.append(sxcmd_category)
		sxcmd_category = SXcmd_category(); sxcmd_category.name = "sxc_3d_clustering"; sxcmd_category.label = "3D Clustering"; sxcmd_category.short_info = "3d variability, and 3d clustering protocol I & II"
		sxcmd_category_list.append(sxcmd_category)
		sxcmd_category = SXcmd_category(); sxcmd_category.name = "sxc_utilities"; sxcmd_category.label = "Utilities"; sxcmd_category.short_info = "miscellaneous utlitity commands"
		sxcmd_category_list.append(sxcmd_category)

		sxcmd = SXcmd(); sxcmd.name = "sxunblur"; sxcmd.mode = ""; sxcmd.label = "Micrograph Alignment"; sxcmd.short_info = "Performs 2D Micrograph alignment with Unblur."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_movie_micrograph"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "unblur"; token.key_prefix = ""; token.label = "path to unblur executable"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "any_file"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "input_mrc_micrograph"; token.key_prefix = ""; token.label = "name pattern of input micrographs (mrc)"; token.help = "use the wild card (*) to specify the place of micrograph id (e.g. serial number, time stamp, or etc). "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "mrc"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output"; token.key_prefix = ""; token.label = "output directory"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nr_frames"; token.key_prefix = "--"; token.label = "number of frames in the set of micrographs"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pixel_size"; token.key_prefix = "--"; token.label = "pixel size [A]"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "apix"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "dose_filter"; token.key_prefix = "--"; token.label = "apply dose filter options"; token.help = "exposure_per_frame, voltage, pre_exposure. "; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "exposure_per_frame"; token.key_prefix = "--"; token.label = "exposure per frame [e/A^2]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "voltage"; token.key_prefix = "--"; token.label = "accelerate voltage [kV]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "300.0"; token.restore = "300.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pre_exposure"; token.key_prefix = "--"; token.label = "pre exposure amount [e/A^2]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0.0"; token.restore = "0.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "save_frames"; token.key_prefix = "--"; token.label = "save aligned frames"; token.help = ""; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "expert_mode"; token.key_prefix = "--"; token.label = "set expert mode settings"; token.help = "shift_initial, shift_radius, b_factor, fourier_vertical, fourier_horizontal, shift_threshold, iterations, restore_noise, verbose. "; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "shift_initial"; token.key_prefix = "--"; token.label = "minimum shift for inital search [A]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "2.0"; token.restore = "2.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "shift_radius"; token.key_prefix = "--"; token.label = "outer radius shift limit [A]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "200.0"; token.restore = "200.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "b_factor"; token.key_prefix = "--"; token.label = "b-factor to appy to image [A^2]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "1500.0"; token.restore = "1500.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fourier_vertical"; token.key_prefix = "--"; token.label = "half-width of central vertical line of fourier mask"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fourier_horizontal"; token.key_prefix = "--"; token.label = "half-width of central horizontal line of fourier mask"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "shift_threshold"; token.key_prefix = "--"; token.label = "termination shift threshold"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0.1"; token.restore = "0.1"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "iterations"; token.key_prefix = "--"; token.label = "maximum number of iterations"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "10"; token.restore = "10"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "restore_noise"; token.key_prefix = "--"; token.label = "restore noise power"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose output"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "filter_sum"; token.key_prefix = "--"; token.label = "filter the output images"; token.help = ""; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "lowpass"; token.key_prefix = "--"; token.label = "apply a lowpass filter"; token.help = "abolute frequency. "; token.group = "main"; token.is_required = False; token.default = "0.033"; token.restore = "0.033"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "highpass"; token.key_prefix = "--"; token.label = "apply a highpass filter"; token.help = "abolute frequency. "; token.group = "main"; token.is_required = False; token.default = "0.00033"; token.restore = "0.00033"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "remove_sum"; token.key_prefix = "--"; token.label = "remove the calculated sum files"; token.help = ""; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxgui_unblur"; sxcmd.mode = ""; sxcmd.label = "Drift Assessment"; sxcmd.short_info = "GUI tool to assess micrographs based on drift estimation produced by Unblur."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_movie_micrograph"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "inputfile"; token.key_prefix = ""; token.label = "a set of shift files"; token.help = "name with wild card * to process multiple micrographs "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "any_file"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "e2display"; sxcmd.mode = ""; sxcmd.label = "Display Data"; sxcmd.short_info = "Display 2D images, 3D volumes, or 1D plots with e2display."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_movie_micrograph"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "input_data_list"; token.key_prefix = ""; token.label = "list of input 2D images, 3D volumes, or 1D plots"; token.help = "it is possible but not recommend to name with wild card * for multiple micrographs when the number is very large. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "any_file_list"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classmx"; token.key_prefix = "--"; token.label = "show particles in one class from a classification matrix"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classes"; token.key_prefix = "--"; token.label = "show particles associated class-averages"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pdb"; token.key_prefix = "--"; token.label = "show PDB structure"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "singleimage"; token.key_prefix = "--"; token.label = "display a stack in a single image view"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 2-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot3"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 3-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fullrange"; token.key_prefix = "--"; token.label = "a specialized flag that disables auto contrast for the display of particles stacks and 2D images only"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "newwidget"; token.key_prefix = "--"; token.label = "use the new 3D widgetD. Highly recommended!!!!"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ppid"; token.key_prefix = "--"; token.label = "set the PID of the parent process, used for cross platform PPID"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-2"; token.restore = "-2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose level [0-9], higher number means higher level of verboseness"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxcter"; sxcmd.mode = ""; sxcmd.label = "CTF Estimation"; sxcmd.short_info = "Automated estimation of CTF parameters with error assessment."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = True; sxcmd.category = "sxc_ctf"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "input_image"; token.key_prefix = ""; token.label = "a set of micrographs (exclude bdb)"; token.help = "name with wild card * to process multiple micrographs (milti-micrograph mode). it can be 2D images in a stack file with --stack_mode. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "any_image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_directory"; token.key_prefix = ""; token.label = "output directory name"; token.help = "into which the partres file, rotinf, and thumb files will be written. The program creates the directory automatically. The directory should not exists upon the execution. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "wn"; token.key_prefix = "--"; token.label = "CTF window size [pixels]"; token.help = "should be slightly larger than particle box size. used only in micrograph modes. "; token.group = "main"; token.is_required = False; token.default = "512"; token.restore = "512"; token.type = "ctfwin"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "apix"; token.key_prefix = "--"; token.label = "pixel size [A]"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "-1.0"; token.restore = "-1.0"; token.type = "apix"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "Cs"; token.key_prefix = "--"; token.label = "microscope spherical aberration (Cs) [mm]"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "2.0"; token.restore = "2.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "voltage"; token.key_prefix = "--"; token.label = "microscope voltage [kV]"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "300.0"; token.restore = "300.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ac"; token.key_prefix = "--"; token.label = "amplitude contrast [%]"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "10.0"; token.restore = "10.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "f_start"; token.key_prefix = "--"; token.label = "starting frequency [1/A]"; token.help = "by default determined automatically "; token.group = "main"; token.is_required = False; token.default = "-1.0"; token.restore = "-1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "f_stop"; token.key_prefix = "--"; token.label = "stop frequency [1/A]"; token.help = "by default determined automatically "; token.group = "main"; token.is_required = False; token.default = "-1.0"; token.restore = "-1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "kboot"; token.key_prefix = "--"; token.label = "number of defocus estimates for micrograph"; token.help = "used for error assessment "; token.group = "advanced"; token.is_required = False; token.default = "16"; token.restore = "16"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "overlap_x"; token.key_prefix = "--"; token.label = "overlap x [%]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "50"; token.restore = "50"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "overlap_y"; token.key_prefix = "--"; token.label = "overlap y [%]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "50"; token.restore = "50"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "edge_x"; token.key_prefix = "--"; token.label = "edge x [pixels]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "edge_y"; token.key_prefix = "--"; token.label = "edge y [pixels]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "set_ctf_header"; token.key_prefix = "--"; token.label = "set estimated CTF parameters to image header"; token.help = "used only in micrograph modes. "; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "debug"; token.key_prefix = "--"; token.label = "print out debug info"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxgui_cter"; sxcmd.mode = ""; sxcmd.label = "CTF Assessment"; sxcmd.short_info = "GUI tool to assess micrographs based on CTF estimation produced by CTER."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_ctf"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "cter_ctf_file"; token.key_prefix = ""; token.label = "CTF parameters file in cter format"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "parameters"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "e2display"; sxcmd.mode = ""; sxcmd.label = "Display Data"; sxcmd.short_info = "Display 2D images, 3D volumes, or 1D plots with e2display."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_ctf"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "input_data_list"; token.key_prefix = ""; token.label = "list of input 2D images, 3D volumes, or 1D plots"; token.help = "it is possible but not recommend to name with wild card * for multiple micrographs when the number is very large. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "any_file_list"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classmx"; token.key_prefix = "--"; token.label = "show particles in one class from a classification matrix"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classes"; token.key_prefix = "--"; token.label = "show particles associated class-averages"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pdb"; token.key_prefix = "--"; token.label = "show PDB structure"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "singleimage"; token.key_prefix = "--"; token.label = "display a stack in a single image view"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 2-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot3"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 3-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fullrange"; token.key_prefix = "--"; token.label = "a specialized flag that disables auto contrast for the display of particles stacks and 2D images only"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "newwidget"; token.key_prefix = "--"; token.label = "use the new 3D widgetD. Highly recommended!!!!"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ppid"; token.key_prefix = "--"; token.label = "set the PID of the parent process, used for cross platform PPID"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-2"; token.restore = "-2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose level [0-9], higher number means higher level of verboseness"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "e2boxer"; sxcmd.mode = ""; sxcmd.label = "Particle Picking"; sxcmd.short_info = "Pick particles with e2boxer."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_particle_stack"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "input_micrograph_list"; token.key_prefix = ""; token.label = "list of input micrograph names"; token.help = "it is possible but not recommend to name with wild card * for multiple micrographs when the number is very large. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "any_image_list"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "boxsize"; token.key_prefix = "--"; token.label = "box size in pixels"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "box"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "write_dbbox"; token.key_prefix = "--"; token.label = "write coordinate file (eman1 dbbox) files"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "write_ptcls"; token.key_prefix = "--"; token.label = "write particles to disk"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "exclude_edges"; token.key_prefix = "--"; token.label = "don't generate output for any particles extending outside the micrograph"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "force"; token.key_prefix = "--"; token.label = "force overwrite"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "format"; token.key_prefix = "--"; token.label = "format of the output particle images [HDF]"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "hdf"; token.restore = "hdf"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "norm"; token.key_prefix = "--"; token.label = "normalization processor to apply to written particle images"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "normalize.edgemean"; token.restore = "normalize.edgemean"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "invert"; token.key_prefix = "--"; token.label = "if writing outputt inverts pixel intensities"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "suffix"; token.key_prefix = "--"; token.label = "suffix which is appended to the names of output particle and coordinate files"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "_ptcls"; token.restore = "_ptcls"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "dbls"; token.key_prefix = "--"; token.label = "data base list storage, used by the workflow"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "autoboxer"; token.key_prefix = "--"; token.label = "a key of the swarm_boxers dict in the local directory, used by the workflow"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ppid"; token.key_prefix = "--"; token.label = "set the PID of the parent process, used for cross platform PPID"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose level [0-9], higner number means higher level of verboseness"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "gauss_autoboxer"; token.key_prefix = "--"; token.label = "name of autoboxed file whose autoboxing parameters should be used for automatic boxing"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxwindow"; sxcmd.mode = ""; sxcmd.label = "Particle Windowing"; sxcmd.short_info = "Window out particles with known coordinates from a micrograph."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_particle_stack"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "input_micrograph_pattern"; token.key_prefix = ""; token.label = "name pattern of input micrographs (exclude bdb)"; token.help = "use the wild card (*) to specify the place of micrograph id (e.g. serial number, time stamp, or etc). "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "any_image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "input_coordinates_pattern"; token.key_prefix = ""; token.label = "name pattern of input coordinates files"; token.help = "use the wild card (*) to specify the place of micrograph id (e.g. serial number, time stamp, and etc). "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "parameters"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_directory"; token.key_prefix = ""; token.label = "output directory name"; token.help = "into which the results will be written. the directory should not exists upon the execution. the program creates it automatically. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "coordinates_format"; token.key_prefix = "--"; token.label = "format of input coordinates files"; token.help = "'sparx', 'eman1', 'eman2', or 'spider'. the coordinates of sparx, eman2, and spider format is particle center. the coordinates of eman1 format is particle box conner associated with the original box size. "; token.group = "main"; token.is_required = False; token.default = "eman1"; token.restore = "eman1"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "box_size"; token.key_prefix = "--"; token.label = "x and y dimension of square area to be windowed (in pixels)"; token.help = "pixel size after resampling is assumed when resample_ratio < 1.0 "; token.group = "main"; token.is_required = False; token.default = "256"; token.restore = "256"; token.type = "box"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "invert"; token.key_prefix = "--"; token.label = "invert image contrast"; token.help = "recommended for cryo data "; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "import_ctf"; token.key_prefix = "--"; token.label = "file name of sxcter output"; token.help = "normally partres.txt "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "parameters"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "limit_ctf"; token.key_prefix = "--"; token.label = "filter micrographs based on the CTF limit"; token.help = "this option requires --import_ctf. "; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "resample_ratio"; token.key_prefix = "--"; token.label = "ratio of new to old image size (or old to new pixel size) for resampling"; token.help = "Valid range is 0.0 < resample_ratio <= 1.0. "; token.group = "advanced"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "defocus_error"; token.key_prefix = "--"; token.label = "defocus errror limit"; token.help = "exclude micrographs whose relative defocus error as estimated by sxcter is larger than defocus_error percent. the error is computed as (std dev defocus)/defocus*100%. "; token.group = "advanced"; token.is_required = False; token.default = "1000000.0"; token.restore = "1000000.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "astigmatism_error"; token.key_prefix = "--"; token.label = "astigmatism error limit"; token.help = "set to zero astigmatism for micrographs whose astigmatism angular error as estimated by sxcter is larger than astigmatism_error degrees. "; token.group = "advanced"; token.is_required = False; token.default = "360.0"; token.restore = "360.0"; token.type = "float"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "e2display"; sxcmd.mode = ""; sxcmd.label = "Display Data"; sxcmd.short_info = "Display 2D images, 3D volumes, or 1D plots with e2display."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_particle_stack"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "input_data_list"; token.key_prefix = ""; token.label = "list of input 2D images, 3D volumes, or 1D plots"; token.help = "it is possible but not recommend to name with wild card * for multiple micrographs when the number is very large. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "any_file_list"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classmx"; token.key_prefix = "--"; token.label = "show particles in one class from a classification matrix"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classes"; token.key_prefix = "--"; token.label = "show particles associated class-averages"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pdb"; token.key_prefix = "--"; token.label = "show PDB structure"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "singleimage"; token.key_prefix = "--"; token.label = "display a stack in a single image view"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 2-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot3"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 3-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fullrange"; token.key_prefix = "--"; token.label = "a specialized flag that disables auto contrast for the display of particles stacks and 2D images only"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "newwidget"; token.key_prefix = "--"; token.label = "use the new 3D widgetD. Highly recommended!!!!"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ppid"; token.key_prefix = "--"; token.label = "set the PID of the parent process, used for cross platform PPID"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-2"; token.restore = "-2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose level [0-9], higher number means higher level of verboseness"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxisac"; sxcmd.mode = ""; sxcmd.label = "2D Clustering with ISAC"; sxcmd.short_info = "Iterative Stable Alignment and Clustering (ISAC) of a 2-D image stack."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_2d_clustering"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "stack_file"; token.key_prefix = ""; token.label = "2-D images in a stack file (bdb or hdf)"; token.help = "images have to be square (''nx''=''ny'') "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_directory"; token.key_prefix = ""; token.label = "output directory name"; token.help = "into which the results will be written (if it does not exist, it will be created, if it does exist, the results will be written possibly overwriting previous results) "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radius"; token.key_prefix = "--"; token.label = "particle radius"; token.help = "there is no default, a sensible number has to be provided, units - pixels "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "img_per_grp"; token.key_prefix = "--"; token.label = "number of images per class"; token.help = "in the ideal case (essentially maximum size of class) "; token.group = "main"; token.is_required = False; token.default = "100"; token.restore = "100"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "CTF"; token.key_prefix = "--"; token.label = "apply phase-flip for CTF correction"; token.help = "if set the data will be phase-flipped using CTF information included in image headers "; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "restart_section"; token.key_prefix = "--"; token.label = "restart section"; token.help = "each generation (iteration) contains three sections: 'restart', 'candidate_class_averages', and 'reproducible_class_averages'. To restart from a particular step, for example, generation 4 and section 'candidate_class_averages' the following option is needed: '--restart_section=candidate_class_averages,4'. The option requires no white space before or after the comma. The default behavior is to restart execution from where it stopped intentionally or unintentionally. For default restart, it is assumed that the name of the directory is provided as argument. Alternatively, the '--use_latest_master_directory' option can be used. "; token.group = "main"; token.is_required = False; token.default = "' '"; token.restore = "' '"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "target_radius"; token.key_prefix = "--"; token.label = "target particle radius"; token.help = "actual particle radius on which isac will process data. Images will be shrinked/enlarged to achieve this radius "; token.group = "main"; token.is_required = False; token.default = "29"; token.restore = "29"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "target_nx"; token.key_prefix = "--"; token.label = "target particle image size"; token.help = "actual image size on which isac will process data. Images will be shrinked/enlarged according to target particle radius and then cut/padded to achieve target_nx size. When xr > 0, the final image size for isac processing is 'target_nx + xr - 1'  "; token.group = "main"; token.is_required = False; token.default = "76"; token.restore = "76"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ir"; token.key_prefix = "--"; token.label = "inner ring"; token.help = "of the resampling to polar coordinates. units - pixels "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "rs"; token.key_prefix = "--"; token.label = "ring step"; token.help = "of the resampling to polar coordinates. units - pixels "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "xr"; token.key_prefix = "--"; token.label = "x range"; token.help = "of translational search. By default, set by the program. "; token.group = "main"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "yr"; token.key_prefix = "--"; token.label = "y range"; token.help = "of translational search. By default, same as xr. "; token.group = "advanced"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ts"; token.key_prefix = "--"; token.label = "search step"; token.help = "of translational search: units - pixels "; token.group = "advanced"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "maxit"; token.key_prefix = "--"; token.label = "number of iterations for reference-free alignment"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "30"; token.restore = "30"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "center_method"; token.key_prefix = "--"; token.label = "method for centering"; token.help = "of global 2D average during initial prealignment of data (0 : no centering; -1 : average shift method; please see center_2D in utilities.py for methods 1-7) "; token.group = "advanced"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "dst"; token.key_prefix = "--"; token.label = "discrete angle used in within group alignment"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "90.0"; token.restore = "90.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "FL"; token.key_prefix = "--"; token.label = "lowest stopband"; token.help = "frequency used in the tangent filter "; token.group = "advanced"; token.is_required = False; token.default = "0.2"; token.restore = "0.2"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "FH"; token.key_prefix = "--"; token.label = "highest stopband"; token.help = "frequency used in the tangent filter "; token.group = "advanced"; token.is_required = False; token.default = "0.3"; token.restore = "0.3"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "FF"; token.key_prefix = "--"; token.label = "fall-off of the tangent filter"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0.2"; token.restore = "0.2"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "init_iter"; token.key_prefix = "--"; token.label = "SAC initialization iterations"; token.help = "number of runs of ab-initio within-cluster alignment for stability evaluation in SAC initialization "; token.group = "advanced"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "main_iter"; token.key_prefix = "--"; token.label = "SAC main iterations"; token.help = "number of runs of ab-initio within-cluster alignment for stability evaluation in SAC "; token.group = "advanced"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "iter_reali"; token.key_prefix = "--"; token.label = "SAC stability check interval"; token.help = "every iter_reali iterations of SAC stability checking is performed "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "match_first"; token.key_prefix = "--"; token.label = "number of iterations to run 2-way matching in the first phase"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "max_round"; token.key_prefix = "--"; token.label = "maximum rounds"; token.help = "of generating candidate class averages in the first phase "; token.group = "advanced"; token.is_required = False; token.default = "20"; token.restore = "20"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "match_second"; token.key_prefix = "--"; token.label = "number of iterations to run 2-way (or 3-way) matching in the second phase"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "5"; token.restore = "5"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "stab_ali"; token.key_prefix = "--"; token.label = "number of alignments when checking stability"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "5"; token.restore = "5"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "thld_err"; token.key_prefix = "--"; token.label = "threshold of pixel error when checking stability"; token.help = "equals root mean square of distances between corresponding pixels from set of found transformations and theirs average transformation, depends linearly on square of radius (parameter ou). units - pixels. "; token.group = "advanced"; token.is_required = False; token.default = "0.7"; token.restore = "0.7"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "indep_run"; token.key_prefix = "--"; token.label = "level of m-way matching for reproducibility tests"; token.help = "By default, perform full ISAC to 4-way matching. Value indep_run=2 will restrict ISAC to 2-way matching and 3 to 3-way matching.  Note the number of used MPI processes requested in mpirun must be a multiplicity of indep_run. "; token.group = "advanced"; token.is_required = False; token.default = "4"; token.restore = "4"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "thld_grp"; token.key_prefix = "--"; token.label = "minimum size of reproducible class"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "10"; token.restore = "10"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "n_generations"; token.key_prefix = "--"; token.label = "maximum number of generations"; token.help = "program stops when reaching this total number of generations: "; token.group = "advanced"; token.is_required = False; token.default = "100"; token.restore = "100"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "rand_seed"; token.key_prefix = "--"; token.label = "random seed set before calculations"; token.help = "useful for testing purposes. By default, total randomness "; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "new"; token.key_prefix = "--"; token.label = "use new code"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "debug"; token.key_prefix = "--"; token.label = "debug info printout"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "use_latest_master_directory"; token.key_prefix = "--"; token.label = "use latest master directory"; token.help = "when active, the program looks for the latest directory that starts with the word 'master', so the user does not need to provide a directory name. "; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "stop_after_candidates"; token.key_prefix = "--"; token.label = "stop after candidates"; token.help = "stops after the 'candidate_class_averages' section. "; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "skip_prealignment"; token.key_prefix = "--"; token.label = "skip pre-alignment step"; token.help = "to be used if images are already centered. 2dalignment directory will still be generated but the parameters will be zero. "; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxisac_post_processing"; sxcmd.mode = ""; sxcmd.label = "2D Clustering Postprocess"; sxcmd.short_info = "Postprocess 2D clustering result produced by ISAC."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_2d_clustering"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "stack_file"; token.key_prefix = ""; token.label = "2-D images in a stack file (format must be bdb)"; token.help = "images have to be square (''nx''=''ny'') "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "bdb"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "isac_directory"; token.key_prefix = ""; token.label = "isac output directory name"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "directory"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radius"; token.key_prefix = "--"; token.label = "particle radius"; token.help = "there is no default, a sensible number has to be provided, units - pixels "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "CTF"; token.key_prefix = "--"; token.label = "apply phase-flip for CTF correction"; token.help = "if set, the data will be phase-flipped using CTF information included in image headers "; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "e2display"; sxcmd.mode = ""; sxcmd.label = "Display Data"; sxcmd.short_info = "Display 2D images, 3D volumes, or 1D plots with e2display."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_2d_clustering"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "input_data_list"; token.key_prefix = ""; token.label = "list of input 2D images, 3D volumes, or 1D plots"; token.help = "it is possible but not recommend to name with wild card * for multiple micrographs when the number is very large. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "any_file_list"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classmx"; token.key_prefix = "--"; token.label = "show particles in one class from a classification matrix"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classes"; token.key_prefix = "--"; token.label = "show particles associated class-averages"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pdb"; token.key_prefix = "--"; token.label = "show PDB structure"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "singleimage"; token.key_prefix = "--"; token.label = "display a stack in a single image view"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 2-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot3"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 3-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fullrange"; token.key_prefix = "--"; token.label = "a specialized flag that disables auto contrast for the display of particles stacks and 2D images only"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "newwidget"; token.key_prefix = "--"; token.label = "use the new 3D widgetD. Highly recommended!!!!"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ppid"; token.key_prefix = "--"; token.label = "set the PID of the parent process, used for cross platform PPID"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-2"; token.restore = "-2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose level [0-9], higher number means higher level of verboseness"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxrviper"; sxcmd.mode = ""; sxcmd.label = "Initial 3D Model with RVIPER"; sxcmd.short_info = "Reproducible ''ab initio'' 3D structure determination, aka Reproducible VIPER.  The program is designed to determine a validated initial intermediate resolution structure using a small set (<100?) of class averages produced by ISAC [[sxisac]]."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_initial_3d_modeling"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "stack"; token.key_prefix = ""; token.label = "set of 2-D images in a stack file (format hdf)"; token.help = "images have to be squares (''nx''=''ny'', nx, ny denotes the image size) "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_directory"; token.key_prefix = ""; token.label = "directory name into which the results will be written"; token.help = "if it does not exist, it will be created, if it does exist, the results will be written possibly overwriting previous results. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ir"; token.key_prefix = "--"; token.label = "inner radius for rotational search"; token.help = "> 0 "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radius"; token.key_prefix = "--"; token.label = "radius of the particle"; token.help = "has to be less than < int(nx/2)-1 "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "rs"; token.key_prefix = "--"; token.label = "step between rings in rotational search"; token.help = ">0 "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "xr"; token.key_prefix = "--"; token.label = "range for translation search in x direction"; token.help = "search is +/xr in pixels "; token.group = "advanced"; token.is_required = False; token.default = "'0'"; token.restore = "'0'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "yr"; token.key_prefix = "--"; token.label = "range for translation search in y direction"; token.help = "if omitted will be set to xr, search is +/yr in pixels "; token.group = "advanced"; token.is_required = False; token.default = "'0'"; token.restore = "'0'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ts"; token.key_prefix = "--"; token.label = "step size of the translation search in x-y directions"; token.help = "search is -xr, -xr+ts, 0, xr-ts, xr, can be fractional "; token.group = "advanced"; token.is_required = False; token.default = "'1.0'"; token.restore = "'1.0'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "delta"; token.key_prefix = "--"; token.label = "angular step of reference projections"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "'2.0'"; token.restore = "'2.0'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "center"; token.key_prefix = "--"; token.label = "centering of 3D template"; token.help = "average shift method; 0: no centering; 1: center of gravity "; token.group = "advanced"; token.is_required = False; token.default = "-1.0"; token.restore = "-1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "maxit1"; token.key_prefix = "--"; token.label = "maximum number of iterations performed for the GA part"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "400"; token.restore = "400"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "maxit2"; token.key_prefix = "--"; token.label = "maximum number of iterations performed for the finishing up part"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "50"; token.restore = "50"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "L2threshold"; token.key_prefix = "--"; token.label = "stopping criterion of GA"; token.help = "given as a maximum relative dispersion of volumes' L2 norms: "; token.group = "advanced"; token.is_required = False; token.default = "0.03"; token.restore = "0.03"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "doga"; token.key_prefix = "--"; token.label = "do GA when fraction of orientation changes less than 1.0 degrees is at least doga"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0.1"; token.restore = "0.1"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ref_a"; token.key_prefix = "--"; token.label = "method for generating the quasi-uniformly distributed projection directions"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "S"; token.restore = "S"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sym"; token.key_prefix = "--"; token.label = "point-group symmetry of the structure"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "c1"; token.restore = "c1"; token.type = "sym"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "n_shc_runs"; token.key_prefix = "--"; token.label = "number of quasi-independent shc runs (same as '--nruns' parameter from sxviper.py)"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "4"; token.restore = "4"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "n_rv_runs"; token.key_prefix = "--"; token.label = "number of rviper iterations"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "10"; token.restore = "10"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "n_v_runs"; token.key_prefix = "--"; token.label = "number of viper runs for each r_viper cycle"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "outlier_percentile"; token.key_prefix = "--"; token.label = "percentile above which outliers are removed every rviper iteration"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "95.0"; token.restore = "95.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "iteration_start"; token.key_prefix = "--"; token.label = "starting iteration for rviper"; token.help = "0 means go to the most recent one "; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "npad"; token.key_prefix = "--"; token.label = "padding size for 3D reconstruction"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "2"; token.restore = "2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fl"; token.key_prefix = "--"; token.label = "cut-off frequency applied to the template volume"; token.help = "using a hyperbolic tangent low-pass filter "; token.group = "advanced"; token.is_required = False; token.default = "0.25"; token.restore = "0.25"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "aa"; token.key_prefix = "--"; token.label = "fall-off of hyperbolic tangent low-pass filter"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0.1"; token.restore = "0.1"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pwreference"; token.key_prefix = "--"; token.label = "text file with a reference power spectrum"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "parameters"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "mask3D"; token.key_prefix = "--"; token.label = "3D mask file"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "sphere"; token.restore = "sphere"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "moon_elimination"; token.key_prefix = "--"; token.label = "elimination of disconnected pieces"; token.help = "two arguments: mass in KDa and pixel size in px/A separated by comma, no space "; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "criterion_name"; token.key_prefix = "--"; token.label = "criterion deciding if volumes have a core set of stable projections"; token.help = "'80th percentile', other options:'fastest increase in the last quartile' "; token.group = "advanced"; token.is_required = False; token.default = "80th percentile"; token.restore = "80th percentile"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "outlier_index_threshold_method"; token.key_prefix = "--"; token.label = "method that decides which images to keep"; token.help = "discontinuity_in_derivative, other options:percentile, angle_measure "; token.group = "advanced"; token.is_required = False; token.default = "discontinuity_in_derivative"; token.restore = "discontinuity_in_derivative"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "angle_threshold"; token.key_prefix = "--"; token.label = "angle threshold for projection removal if using 'angle_measure'"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "30"; token.restore = "30"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxviper"; sxcmd.mode = ""; sxcmd.label = "Initial 3D Model with VIPER"; sxcmd.short_info = "Validated ''ab initio'' 3D structure determination, aka Validation of Individual Parameter Reproducibility. The program is designed to determine a validated initial intermediate resolution structure using a small set (<100?) of class averages produced by ISAC [[sxisac]]."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_initial_3d_modeling"; sxcmd.role = "sxr_alt"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "stack"; token.key_prefix = ""; token.label = "2D images in a stack file"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "directory"; token.key_prefix = ""; token.label = "output directory name"; token.help = "into which the results will be written (if it does not exist, it will be created, if it does exist, the results will be written possibly overwriting previous results) "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ir"; token.key_prefix = "--"; token.label = "inner radius for rotational search"; token.help = "> 0 "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radius"; token.key_prefix = "--"; token.label = "radius of the particle"; token.help = "has to be less than < int(nx/2)-1 "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "rs"; token.key_prefix = "--"; token.label = "step between rings in rotational search"; token.help = ">0 "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "xr"; token.key_prefix = "--"; token.label = "range for translation search in x direction"; token.help = "search is +/xr in pixels "; token.group = "advanced"; token.is_required = False; token.default = "'0'"; token.restore = "'0'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "yr"; token.key_prefix = "--"; token.label = "range for translation search in y direction"; token.help = "if omitted will be set to xr, search is +/yr in pixels "; token.group = "advanced"; token.is_required = False; token.default = "'0'"; token.restore = "'0'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "mask3D"; token.key_prefix = "--"; token.label = "3D mask file"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "sphere"; token.restore = "sphere"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "moon_elimination"; token.key_prefix = "--"; token.label = "elimination of disconnected pieces"; token.help = "two arguments: mass in KDa and pixel size in px/A separated by comma, no space "; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ts"; token.key_prefix = "--"; token.label = "step size of the translation search in x-y directions"; token.help = "search is -xr, -xr+ts, 0, xr-ts, xr, can be fractional "; token.group = "advanced"; token.is_required = False; token.default = "'1.0'"; token.restore = "'1.0'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "delta"; token.key_prefix = "--"; token.label = "angular step of reference projections"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "'2.0'"; token.restore = "'2.0'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "center"; token.key_prefix = "--"; token.label = "centering of 3D template"; token.help = "average shift method; 0: no centering; 1: center of gravity "; token.group = "advanced"; token.is_required = False; token.default = "-1.0"; token.restore = "-1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "maxit1"; token.key_prefix = "--"; token.label = "maximum number of iterations performed for the GA part"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "400"; token.restore = "400"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "maxit2"; token.key_prefix = "--"; token.label = "maximum number of iterations performed for the finishing up part"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "50"; token.restore = "50"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "L2threshold"; token.key_prefix = "--"; token.label = "stopping criterion of GA"; token.help = "given as a maximum relative dispersion of volumes' L2 norms: "; token.group = "advanced"; token.is_required = False; token.default = "0.03"; token.restore = "0.03"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ref_a"; token.key_prefix = "--"; token.label = "method for generating the quasi-uniformly distributed projection directions"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "S"; token.restore = "S"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sym"; token.key_prefix = "--"; token.label = "point-group symmetry of the structure"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "c1"; token.restore = "c1"; token.type = "sym"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nruns"; token.key_prefix = "--"; token.label = "GA population"; token.help = "aka number of quasi-independent volumes "; token.group = "advanced"; token.is_required = False; token.default = "6"; token.restore = "6"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "doga"; token.key_prefix = "--"; token.label = "do GA when fraction of orientation changes less than 1.0 degrees is at least doga"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0.1"; token.restore = "0.1"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fl"; token.key_prefix = "--"; token.label = "cut-off frequency applied to the template volume"; token.help = "using a hyperbolic tangent low-pass filter "; token.group = "advanced"; token.is_required = False; token.default = "0.25"; token.restore = "0.25"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "aa"; token.key_prefix = "--"; token.label = "fall-off of hyperbolic tangent low-pass filter"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0.1"; token.restore = "0.1"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pwreference"; token.key_prefix = "--"; token.label = "text file with a reference power spectrum"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "parameters"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "debug"; token.key_prefix = "--"; token.label = "debug info printout"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxpdb2em"; sxcmd.mode = ""; sxcmd.label = "PDB File Conversion"; sxcmd.short_info = "Convert atomic model (pdb file) into sampled electron density map"; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_initial_3d_modeling"; sxcmd.role = "sxr_alt"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "input_pdb"; token.key_prefix = ""; token.label = "pdb file with atomic coordinates"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "pdb"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_hdf"; token.key_prefix = ""; token.label = "output 3-D electron density map (any EM format)"; token.help = "Attribute pixel_size will be set to the specified value. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "apix"; token.key_prefix = "--"; token.label = "pixel size (in Angstrom) of the output map"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "apix"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "box"; token.key_prefix = "--"; token.label = "size of the output map in voxels"; token.help = "If not given, the program will find the minimum box size that includes the structre.  However, in most cases this will result in a rectangular box, i.e., each dimension will be different. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "box"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "het"; token.key_prefix = "--"; token.label = "Include HET atoms in the map"; token.help = ""; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "center"; token.key_prefix = "--"; token.label = "specify whether to center the atomic model"; token.help = "before converting to electron density map (warning: pdb deposited atomic models are not necesserily centered).  Options: c - center using coordinates of atoms; a - center by setting center of gravity to zero (recommended); a triplet x,y,z (no spaces in between) - coordinates (in Angstrom) to be substracted from all the PDB coordinates. Default: no centering, in which case (0,0,0) in the PDB space will map to the center of the EM volume, i.e., (nx/2, ny/2, nz/2). "; token.group = "main"; token.is_required = False; token.default = "n"; token.restore = "n"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "O"; token.key_prefix = "--"; token.label = "apply additional rotation"; token.help = "so the model will appear in O in the same rotation as in chimera. "; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "tr0"; token.key_prefix = "--"; token.label = "name of a file containing a 3x4 transformation matrix"; token.help = "to be applied to the PDB coordinates after centering, prior to computing the density map. The translation vector (last column of the matrix) must be specified in Angstrom. If this parameter is omitted, no transformation is applied. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "parameters"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "quiet"; token.key_prefix = "--"; token.label = "do not print any information to the monitor"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "e2display"; sxcmd.mode = ""; sxcmd.label = "Display Data"; sxcmd.short_info = "Display 2D images, 3D volumes, or 1D plots with e2display."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_initial_3d_modeling"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "input_data_list"; token.key_prefix = ""; token.label = "list of input 2D images, 3D volumes, or 1D plots"; token.help = "it is possible but not recommend to name with wild card * for multiple micrographs when the number is very large. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "any_file_list"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classmx"; token.key_prefix = "--"; token.label = "show particles in one class from a classification matrix"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classes"; token.key_prefix = "--"; token.label = "show particles associated class-averages"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pdb"; token.key_prefix = "--"; token.label = "show PDB structure"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "singleimage"; token.key_prefix = "--"; token.label = "display a stack in a single image view"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 2-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot3"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 3-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fullrange"; token.key_prefix = "--"; token.label = "a specialized flag that disables auto contrast for the display of particles stacks and 2D images only"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "newwidget"; token.key_prefix = "--"; token.label = "use the new 3D widgetD. Highly recommended!!!!"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ppid"; token.key_prefix = "--"; token.label = "set the PID of the parent process, used for cross platform PPID"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-2"; token.restore = "-2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose level [0-9], higher number means higher level of verboseness"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxprocess"; sxcmd.mode = "adaptive_mask"; sxcmd.label = "Adaptive 3D Mask"; sxcmd.short_info = "Create adavptive 3D mask from a given 3D volume. "; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_initial_3d_modeling"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "adaptive_mask"; token.key_prefix = "--"; token.label = "Create adavptive 3D mask from a given 3D volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = True; token.restore = True; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "input_volume"; token.key_prefix = ""; token.label = "input volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_mask3D"; token.key_prefix = ""; token.label = "output 3D mask"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nsigma"; token.key_prefix = "--"; token.label = "factor of input volume sigma to obtain large density cluster"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ndilation"; token.key_prefix = "--"; token.label = "number of dilations applied to the largest density cluster"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "kernel_size"; token.key_prefix = "--"; token.label = "convolution kernel for mask edge smoothing"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "11"; token.restore = "11"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "gauss_standard_dev"; token.key_prefix = "--"; token.label = "standard deviation to generate Gaussian edge"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "9"; token.restore = "9"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "threshold"; token.key_prefix = "--"; token.label = "threshold to binarize input volume"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "9999.0"; token.restore = "9999.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ne"; token.key_prefix = "--"; token.label = "number of erosions applied to the binarized input image"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nd"; token.key_prefix = "--"; token.label = "number of dilations applied to the binarized input image"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxmeridien"; sxcmd.mode = ""; sxcmd.label = "3D Refinement"; sxcmd.short_info = "Performs 3D structure refinement."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_refinement"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "stack"; token.key_prefix = ""; token.label = "name of input stack"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_directory"; token.key_prefix = ""; token.label = "output folder"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "current directory"; token.restore = "current directory"; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "initial_volume"; token.key_prefix = ""; token.label = "initial 3D structure"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radius"; token.key_prefix = "--"; token.label = "particle radius"; token.help = "radius of the structure in pixels. if not sure, set to boxsize/2-2 "; token.group = "main"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "outlier_percentile"; token.key_prefix = "--"; token.label = "percentile above which outliers"; token.help = "are removed every iteration. "; token.group = "main"; token.is_required = False; token.default = "95.0"; token.restore = "95.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ref_a"; token.key_prefix = "--"; token.label = "method for generating the quasi-uniformly distributed projection directions"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "S"; token.restore = "S"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sym"; token.key_prefix = "--"; token.label = "point-group symmetry of the structure"; token.help = "cn, dn, where n is multiplicity (for example c5 or d3). "; token.group = "main"; token.is_required = False; token.default = "c1"; token.restore = "c1"; token.type = "sym"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "startangles"; token.key_prefix = "--"; token.label = "Use orientation parameters in the input file header"; token.help = "to jumpstart the procedure "; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "restrict_shifts"; token.key_prefix = "--"; token.label = "Restrict initial searches for translation"; token.help = "unit - original size pixel. By default, no restriction. "; token.group = "main"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "local_filter"; token.key_prefix = "--"; token.label = "Use local filtration"; token.help = "By default, uses generic tangent filter. "; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "smear"; token.key_prefix = "--"; token.label = "Use rotational smear"; token.help = ""; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sausage"; token.key_prefix = "--"; token.label = "Sausage-making filter"; token.help = ""; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "inires"; token.key_prefix = "--"; token.label = "initial resolution"; token.help = "of the initial_volume: unit - angstroms."; token.group = "main"; token.is_required = False; token.default = "25.0"; token.restore = "25.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "mask3D"; token.key_prefix = "--"; token.label = "3D mask"; token.help = "that defines outline of the structure, preferable with soft edges if not given, set to spherical mask with radius boxsize/2-1. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "CTF"; token.key_prefix = "--"; token.label = "Use CTF"; token.help = ""; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "function"; token.key_prefix = "--"; token.label = "name of the reference preparation function"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "do_volume_mrk02"; token.restore = "do_volume_mrk02"; token.type = "function"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxprocess"; sxcmd.mode = "postprocess"; sxcmd.label = "3D Refinement Postprocess"; sxcmd.short_info = "Adjust power spectrum of 3D or 2D images based on B-factor. B-factor is estimated from unfiltered odd-even 3D volumes or a 2D image. "; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_refinement"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "postprocess"; token.key_prefix = "--"; token.label = "Adjust power spectrum of 3D or 2D images based on B-factor"; token.help = "B-factor is estimated from unfiltered odd-even 3D volumes or a 2D image. "; token.group = "main"; token.is_required = True; token.default = True; token.restore = True; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "firstvolume"; token.key_prefix = ""; token.label = "first unfiltered half-volume "; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "secondvolume"; token.key_prefix = ""; token.label = "second unfiltered half-volume "; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fsc_weighted"; token.key_prefix = "--"; token.label = "apply FSC-based low-pass-filter"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "low_pass_filter"; token.key_prefix = "--"; token.label = "apply generic tangent low-pass-filter"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ff"; token.key_prefix = "--"; token.label = "tangent low-pass-filter stop band frequency"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0.25"; token.restore = "0.25"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "aa"; token.key_prefix = "--"; token.label = "tangent low-pass-filter falloff"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0.1"; token.restore = "0.1"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "mask"; token.key_prefix = "--"; token.label = "input 3D or 2D mask file name"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output"; token.key_prefix = "--"; token.label = "output file name"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "postprocessed.hdf"; token.restore = "postprocessed.hdf"; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pixel_size"; token.key_prefix = "--"; token.label = "pixel size of the input data"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "apix"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "B_start"; token.key_prefix = "--"; token.label = "starting frequency in Angstrom for B-factor estimation"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "10.0"; token.restore = "10.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "FSC_cutoff"; token.key_prefix = "--"; token.label = "stop frequency in Angstrom for B-factor estimation"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0.143"; token.restore = "0.143"; token.type = "float"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxlocres"; sxcmd.mode = ""; sxcmd.label = "Local Resolution Estimation"; sxcmd.short_info = "Compute local resolution in real space within are outlined by the maskfile and within regions wn x wn x wn."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = True; sxcmd.category = "sxc_3d_refinement"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "firstvolume"; token.key_prefix = ""; token.label = "first half-volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "secondvolume"; token.key_prefix = ""; token.label = "second half-volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "maskfile"; token.key_prefix = ""; token.label = "mask volume"; token.help = "outlining the region within which local resolution values will be computed (optional). "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "outputfile"; token.key_prefix = ""; token.label = "output local resolution volume"; token.help = "contains, for each voxel, an [[absolute_frequency_units|absolute frequency]] value for which local resolution at this location drops below the specified cut-off FSC value (only regions specified by the mask film or within a sphere have non-zero values). "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "wn"; token.key_prefix = "--"; token.label = "size of window within which local real-space FSC is computed"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "7"; token.restore = "7"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "step"; token.key_prefix = "--"; token.label = "shell step in Fourier size in pixels"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "cutoff"; token.key_prefix = "--"; token.label = "resolution cut-off for FSC"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "0.5"; token.restore = "0.5"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radius"; token.key_prefix = "--"; token.label = "radius for the mask in pixels"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fsc"; token.key_prefix = "--"; token.label = "name output file"; token.help = "that will contain the overall FSC curve computed by rotational averaging of local resolution values (migh be truncated) "; token.group = "main"; token.is_required = False; token.default = "no curve"; token.restore = "no curve"; token.type = "string"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxfilterlocal"; sxcmd.mode = ""; sxcmd.label = "3D Local Filter"; sxcmd.short_info = "Locally filter input volume based on values within the associated local resolution volume ([[sxlocres.py]]) within area outlined by the maskfile."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = True; sxcmd.category = "sxc_3d_refinement"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "input_volume"; token.key_prefix = ""; token.label = "input volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "locres_volume"; token.key_prefix = ""; token.label = "local resolution volume"; token.help = "as produced by [[sxlocres.py]]. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "maskfile"; token.key_prefix = ""; token.label = "mask volume"; token.help = "outlining the region within which local filtration will be applied (optional). "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "outputfile"; token.key_prefix = ""; token.label = "locally filtered volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radius"; token.key_prefix = "--"; token.label = "radius for the mask in pixels"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "falloff"; token.key_prefix = "--"; token.label = "fall-off of low-pass filter"; token.help = "program uses [[filt_tanl|tangent low-pass filter]]. unit - [[absolute_frequency_units|absolute frequency units]]. "; token.group = "main"; token.is_required = False; token.default = "0.1"; token.restore = "0.1"; token.type = "float"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "e2display"; sxcmd.mode = ""; sxcmd.label = "Display Data"; sxcmd.short_info = "Display 2D images, 3D volumes, or 1D plots with e2display."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_refinement"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "input_data_list"; token.key_prefix = ""; token.label = "list of input 2D images, 3D volumes, or 1D plots"; token.help = "it is possible but not recommend to name with wild card * for multiple micrographs when the number is very large. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "any_file_list"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classmx"; token.key_prefix = "--"; token.label = "show particles in one class from a classification matrix"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classes"; token.key_prefix = "--"; token.label = "show particles associated class-averages"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pdb"; token.key_prefix = "--"; token.label = "show PDB structure"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "singleimage"; token.key_prefix = "--"; token.label = "display a stack in a single image view"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 2-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot3"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 3-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fullrange"; token.key_prefix = "--"; token.label = "a specialized flag that disables auto contrast for the display of particles stacks and 2D images only"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "newwidget"; token.key_prefix = "--"; token.label = "use the new 3D widgetD. Highly recommended!!!!"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ppid"; token.key_prefix = "--"; token.label = "set the PID of the parent process, used for cross platform PPID"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-2"; token.restore = "-2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose level [0-9], higher number means higher level of verboseness"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxprocess"; sxcmd.mode = "adaptive_mask"; sxcmd.label = "Adaptive 3D Mask"; sxcmd.short_info = "Create adavptive 3D mask from a given 3D volume. "; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_refinement"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "adaptive_mask"; token.key_prefix = "--"; token.label = "Create adavptive 3D mask from a given 3D volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = True; token.restore = True; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "input_volume"; token.key_prefix = ""; token.label = "input volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_mask3D"; token.key_prefix = ""; token.label = "output 3D mask"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nsigma"; token.key_prefix = "--"; token.label = "factor of input volume sigma to obtain large density cluster"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ndilation"; token.key_prefix = "--"; token.label = "number of dilations applied to the largest density cluster"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "kernel_size"; token.key_prefix = "--"; token.label = "convolution kernel for mask edge smoothing"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "11"; token.restore = "11"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "gauss_standard_dev"; token.key_prefix = "--"; token.label = "standard deviation to generate Gaussian edge"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "9"; token.restore = "9"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "threshold"; token.key_prefix = "--"; token.label = "threshold to binarize input volume"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "9999.0"; token.restore = "9999.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ne"; token.key_prefix = "--"; token.label = "number of erosions applied to the binarized input image"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nd"; token.key_prefix = "--"; token.label = "number of dilations applied to the binarized input image"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sx3dvariability"; sxcmd.mode = "symmetrize"; sxcmd.label = "3D Variability Preprocess"; sxcmd.short_info = "Prepare input stack for handling symmetry. "; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_clustering"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "symmetrize"; token.key_prefix = "--"; token.label = "Prepare input stack for handling symmetry"; token.help = ""; token.group = "main"; token.is_required = True; token.default = True; token.restore = True; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "input_volume"; token.key_prefix = ""; token.label = "input volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sym"; token.key_prefix = "--"; token.label = "point-group symmetry of the structure"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "c1"; token.restore = "c1"; token.type = "sym"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sx3dvariability"; sxcmd.mode = ""; sxcmd.label = "3D Variablity"; sxcmd.short_info = "Calculate 3D variability field using a set of aligned 2D projection images as an input. The structures with symmetry require preparing data before calculating variability. The data preparation step would symmetrize the data and output a bdb:sdata for variability calculation."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_clustering"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "prj_stack"; token.key_prefix = ""; token.label = "stack of 2D images"; token.help = "with 3D orientation parameters in header and (optionally) CTF information "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ave2D"; token.key_prefix = "--"; token.label = "write to the disk a stack of 2D averages"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "var2D"; token.key_prefix = "--"; token.label = "write to the disk a stack of 2D variances"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ave3D"; token.key_prefix = "--"; token.label = "write to the disk reconstructed 3D average"; token.help = "3D reconstruction computed from projections averaged within respective angular neighborhood. It should be used to assess the resolvability and possible artifacts of the variability map. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "var3D"; token.key_prefix = "--"; token.label = "compute 3D variability"; token.help = "time consuming! "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "img_per_grp"; token.key_prefix = "--"; token.label = "number of projections"; token.help = "from the angular neighborhood that will be used to estimate 2D variance for each projection data. The larger the number the less noisy the estimate, but the lower the resolution. Usage of large number also results in rotational artifacts in variances that will be visible in 3D variability volume. "; token.group = "main"; token.is_required = False; token.default = "10"; token.restore = "10"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "no_norm"; token.key_prefix = "--"; token.label = "do not use normalization"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radiusvar"; token.key_prefix = "--"; token.label = "radius for 3D var"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "npad"; token.key_prefix = "--"; token.label = "number of time to pad the original images"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "2"; token.restore = "2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sym"; token.key_prefix = "--"; token.label = "point-group symmetry of the structure"; token.help = "specified in case the input structure has symmetry higher than c1. It is specified together with option --sym in the first step for preparing data. Notice this step can be run with only one CPU and there is no MPI version for it. "; token.group = "main"; token.is_required = False; token.default = "c1"; token.restore = "c1"; token.type = "sym"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fl"; token.key_prefix = "--"; token.label = "stop-band frequency of the low pass filter"; token.help = "to be applied to 2D data prior to variability calculation By default, no filtration. "; token.group = "main"; token.is_required = False; token.default = "0.0"; token.restore = "0.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "aa"; token.key_prefix = "--"; token.label = "fall-off frequency of the low pass filter"; token.help = "to be applied to 2D data prior to variability calculation By default, no filtration. "; token.group = "main"; token.is_required = False; token.default = "0.0"; token.restore = "0.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "CTF"; token.key_prefix = "--"; token.label = "use CFT correction"; token.help = ""; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "VERBOSE"; token.key_prefix = "--"; token.label = "Long output for debugging"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "VAR"; token.key_prefix = "--"; token.label = "stack on input consists of 2D variances"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "SND"; token.key_prefix = "--"; token.label = "compute squared normalized differences"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxsort3d"; sxcmd.mode = ""; sxcmd.label = "3D Clustering Protocol I (P1)"; sxcmd.short_info = "Sort out 3D heterogeneity based on the reproducible members of K-means and Equal K-means classification. It runs after 3D refinement where the alignment parameters (xform.projection) are determined."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_clustering"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "stack"; token.key_prefix = ""; token.label = "2D images in a stack file"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "outdir"; token.key_prefix = ""; token.label = "master output directory"; token.help = "will contain multiple subdirectories. There is a log.txt that describes the sequences of computations in the program. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "mask"; token.key_prefix = ""; token.label = "3D mask"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "focus"; token.key_prefix = "--"; token.label = "3D mask for focused clustering"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ir"; token.key_prefix = "--"; token.label = "inner radius for rotational correlation"; token.help = "> 0. "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radius"; token.key_prefix = "--"; token.label = "outer radius for rotational correlation"; token.help = "< nx - 1. Please set to the radius of the particle. "; token.group = "main"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "maxit"; token.key_prefix = "--"; token.label = "maximum number of iteration"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "25"; token.restore = "25"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "rs"; token.key_prefix = "--"; token.label = "step between rings in rotational correlation"; token.help = "> 0. "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "xr"; token.key_prefix = "--"; token.label = "range for translation search in x direction"; token.help = "search is +/-xr. "; token.group = "advanced"; token.is_required = False; token.default = "'1'"; token.restore = "'1'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "yr"; token.key_prefix = "--"; token.label = "range for translation search in y direction"; token.help = "search is +/-yr. By default, same as xr. "; token.group = "advanced"; token.is_required = False; token.default = "'-1'"; token.restore = "'-1'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ts"; token.key_prefix = "--"; token.label = "step size of the translation search"; token.help = "in both directions direction. search is -xr, -xr+ts, 0, xr-ts, xr. "; token.group = "advanced"; token.is_required = False; token.default = "'0.25'"; token.restore = "'0.25'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "delta"; token.key_prefix = "--"; token.label = "angular step of reference projections"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "'2'"; token.restore = "'2'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "an"; token.key_prefix = "--"; token.label = "angular neighborhood for local searches"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "'-1'"; token.restore = "'-1'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "center"; token.key_prefix = "--"; token.label = "centering method"; token.help = "0 - if you do not want the volume to be centered, 1 - center the volume using cog. "; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nassign"; token.key_prefix = "--"; token.label = "number of reassignment iterations"; token.help = "performed for each angular step. "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nrefine"; token.key_prefix = "--"; token.label = "number of alignment iterations"; token.help = "performed for each angular step. "; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "CTF"; token.key_prefix = "--"; token.label = "Consider CTF correction"; token.help = "during the alignment. "; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "stoprnct"; token.key_prefix = "--"; token.label = "Minimum percentage of assignment change to stop the program"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "3.0"; token.restore = "3.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sym"; token.key_prefix = "--"; token.label = "point-group symmetry of the structure"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "c1"; token.restore = "c1"; token.type = "sym"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "function"; token.key_prefix = "--"; token.label = "name of the reference preparation function"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "do_volume_mrk02"; token.restore = "do_volume_mrk02"; token.type = "function"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "independent"; token.key_prefix = "--"; token.label = "number of independent run"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "number_of_images_per_group"; token.key_prefix = "--"; token.label = "number of images per group"; token.help = "critical number defined by user. "; token.group = "main"; token.is_required = False; token.default = "1000"; token.restore = "1000"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "low_pass_filter"; token.key_prefix = "--"; token.label = "absolute frequency of low-pass filter"; token.help = "for 3d sorting on the original image size. "; token.group = "advanced"; token.is_required = False; token.default = "-1.0"; token.restore = "-1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nxinit"; token.key_prefix = "--"; token.label = "initial image size for sorting"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "64"; token.restore = "64"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "unaccounted"; token.key_prefix = "--"; token.label = "reconstruct the unaccounted images"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "seed"; token.key_prefix = "--"; token.label = "random seed"; token.help = "for create initial random assignment for EQ Kmeans "; token.group = "advanced"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "smallest_group"; token.key_prefix = "--"; token.label = "minimum members for identified group"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "500"; token.restore = "500"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sausage"; token.key_prefix = "--"; token.label = "way of filter volume"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "chunkdir"; token.key_prefix = "--"; token.label = "chunkdir for computing margin of error"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "directory"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "PWadjustment"; token.key_prefix = "--"; token.label = "1-D power spectrum of PDB file"; token.help = "used for EM volume power spectrum correction "; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "parameters"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "upscale"; token.key_prefix = "--"; token.label = "scaling parameter to adjust the power spectrum"; token.help = "of EM volumes "; token.group = "advanced"; token.is_required = False; token.default = "0.5"; token.restore = "0.5"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "wn"; token.key_prefix = "--"; token.label = "optimal window size for data processing"; token.help = "of EM volumes "; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxrsort3d"; sxcmd.mode = ""; sxcmd.label = "3D Clustering Protocol II (P2)"; sxcmd.short_info = "Sort out 3D heterogeneity of 2D data whose 3D reconstruction parameters (xform.projection) have been determined already using 3D sorting protocol I (P1)."; sxcmd.mpi_support = True; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_clustering"; sxcmd.role = "sxr_pipe"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "stack"; token.key_prefix = ""; token.label = "input visual 2D stack file"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "outdir"; token.key_prefix = ""; token.label = "output master directory"; token.help = "that contains multiple subdirectories and a log file termed as 'log.txt', which records the sequences of major computational operations. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "mask"; token.key_prefix = ""; token.label = "global 3D mask"; token.help = "this is optional. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "previous_run1"; token.key_prefix = "--"; token.label = "master directory of first sxsort3d.py run"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "directory"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "previous_run2"; token.key_prefix = "--"; token.label = "master directory of second sxsort3d.py run"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "directory"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "focus"; token.key_prefix = "--"; token.label = "3D mask for focused clustering"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ir"; token.key_prefix = "--"; token.label = "inner radius for rotational correlation"; token.help = "> 0 "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "radius"; token.key_prefix = "--"; token.label = "radius of the protein particles in pixel"; token.help = "Please set to the radius of the particle. "; token.group = "main"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "radius"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "maxit"; token.key_prefix = "--"; token.label = "maximum number of iteration"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "50"; token.restore = "50"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "rs"; token.key_prefix = "--"; token.label = "step between rings in rotational correlation"; token.help = "> 0. "; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "xr"; token.key_prefix = "--"; token.label = "range for translation search in x direction"; token.help = "search is +/-xr. "; token.group = "advanced"; token.is_required = False; token.default = "'1'"; token.restore = "'1'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "yr"; token.key_prefix = "--"; token.label = "range for translation search in y direction"; token.help = "search is +/-yr. By default, same as xr. "; token.group = "advanced"; token.is_required = False; token.default = "'-1'"; token.restore = "'-1'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ts"; token.key_prefix = "--"; token.label = "step size of the translation search"; token.help = "in both directions direction. search is -xr, -xr+ts, 0, xr-ts, xr. "; token.group = "advanced"; token.is_required = False; token.default = "'0.25'"; token.restore = "'0.25'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "delta"; token.key_prefix = "--"; token.label = "angular step of the reference projections"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "'2'"; token.restore = "'2'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "an"; token.key_prefix = "--"; token.label = "angular neighborhood for local search"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "'-1'"; token.restore = "'-1'"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "center"; token.key_prefix = "--"; token.label = "centering method"; token.help = "0 - if you do not want the volume to be centered, 1 - center the volume using cog. "; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nassign"; token.key_prefix = "--"; token.label = "number of assignment during one iteration cycle"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "1"; token.restore = "1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nrefine"; token.key_prefix = "--"; token.label = "number of alignment iterations"; token.help = "performed for each angular step. "; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "CTF"; token.key_prefix = "--"; token.label = "Consider CTF correction"; token.help = "during the alignment. "; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "stoprnct"; token.key_prefix = "--"; token.label = "Minimum percentage of assignment change to stop the program"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "3.0"; token.restore = "3.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sym"; token.key_prefix = "--"; token.label = "point-group symmetry of the structure"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "c1"; token.restore = "c1"; token.type = "sym"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "independent"; token.key_prefix = "--"; token.label = "number of independent run of equal-Kmeans clustering"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "number_of_images_per_group"; token.key_prefix = "--"; token.label = "number of images per group"; token.help = "critical number defined by user. "; token.group = "main"; token.is_required = False; token.default = "1000"; token.restore = "1000"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "low_pass_filter"; token.key_prefix = "--"; token.label = "absolute frequency of low-pass filter"; token.help = "for 3d sorting on the original image size. "; token.group = "advanced"; token.is_required = False; token.default = "-1.0"; token.restore = "-1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nxinit"; token.key_prefix = "--"; token.label = "initial image size for sorting"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "64"; token.restore = "64"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "unaccounted"; token.key_prefix = "--"; token.label = "reconstruct the unaccounted images"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "function"; token.key_prefix = "--"; token.label = "name of the reference preparation function"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "do_volume_mrk02"; token.restore = "do_volume_mrk02"; token.type = "function"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "seed"; token.key_prefix = "--"; token.label = "random seed"; token.help = "for create initial random assignment for EQ Kmeans "; token.group = "advanced"; token.is_required = False; token.default = "-1"; token.restore = "-1"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "smallest_group"; token.key_prefix = "--"; token.label = "minimum members for identified group"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "500"; token.restore = "500"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "group_size_for_unaccounted"; token.key_prefix = "--"; token.label = "group size for unaccounted particles"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "sausage"; token.key_prefix = "--"; token.label = "the way of filtering reference volume"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "chunkdir"; token.key_prefix = "--"; token.label = "chunkdir for computing margin of error"; token.help = "two chunks of arbitrary assigned data while refined independently during the 3-D reconstruction: By default the program generates it internally. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "directory"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "PWadjustment"; token.key_prefix = "--"; token.label = "1-D power spectrum of PDB file"; token.help = "used for EM volume power spectrum correction "; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "parameters"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "upscale"; token.key_prefix = "--"; token.label = "scaling parameter to adjust the power spectrum"; token.help = "of EM volumes "; token.group = "advanced"; token.is_required = False; token.default = "0.5"; token.restore = "0.5"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "wn"; token.key_prefix = "--"; token.label = "optimal window size for data processing"; token.help = "of EM volumes "; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "e2display"; sxcmd.mode = ""; sxcmd.label = "Display Data"; sxcmd.short_info = "Display 2D images, 3D volumes, or 1D plots with e2display."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_clustering"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "input_data_list"; token.key_prefix = ""; token.label = "list of input 2D images, 3D volumes, or 1D plots"; token.help = "it is possible but not recommend to name with wild card * for multiple micrographs when the number is very large. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "any_file_list"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classmx"; token.key_prefix = "--"; token.label = "show particles in one class from a classification matrix"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classes"; token.key_prefix = "--"; token.label = "show particles associated class-averages"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pdb"; token.key_prefix = "--"; token.label = "show PDB structure"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "singleimage"; token.key_prefix = "--"; token.label = "display a stack in a single image view"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 2-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot3"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 3-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fullrange"; token.key_prefix = "--"; token.label = "a specialized flag that disables auto contrast for the display of particles stacks and 2D images only"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "newwidget"; token.key_prefix = "--"; token.label = "use the new 3D widgetD. Highly recommended!!!!"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ppid"; token.key_prefix = "--"; token.label = "set the PID of the parent process, used for cross platform PPID"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-2"; token.restore = "-2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose level [0-9], higher number means higher level of verboseness"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxprocess"; sxcmd.mode = "adaptive_mask"; sxcmd.label = "Adaptive 3D Mask"; sxcmd.short_info = "Create adavptive 3D mask from a given 3D volume. "; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_3d_clustering"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "adaptive_mask"; token.key_prefix = "--"; token.label = "Create adavptive 3D mask from a given 3D volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = True; token.restore = True; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "input_volume"; token.key_prefix = ""; token.label = "input volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_mask3D"; token.key_prefix = ""; token.label = "output 3D mask"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nsigma"; token.key_prefix = "--"; token.label = "factor of input volume sigma to obtain large density cluster"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ndilation"; token.key_prefix = "--"; token.label = "number of dilations applied to the largest density cluster"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "kernel_size"; token.key_prefix = "--"; token.label = "convolution kernel for mask edge smoothing"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "11"; token.restore = "11"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "gauss_standard_dev"; token.key_prefix = "--"; token.label = "standard deviation to generate Gaussian edge"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "9"; token.restore = "9"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "threshold"; token.key_prefix = "--"; token.label = "threshold to binarize input volume"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "9999.0"; token.restore = "9999.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ne"; token.key_prefix = "--"; token.label = "number of erosions applied to the binarized input image"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nd"; token.key_prefix = "--"; token.label = "number of dilations applied to the binarized input image"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "e2display"; sxcmd.mode = ""; sxcmd.label = "Display Data"; sxcmd.short_info = "Display 2D images, 3D volumes, or 1D plots with e2display."; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_utilities"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = False
		token = SXcmd_token(); token.key_base = "input_data_list"; token.key_prefix = ""; token.label = "list of input 2D images, 3D volumes, or 1D plots"; token.help = "it is possible but not recommend to name with wild card * for multiple micrographs when the number is very large. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "any_file_list"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classmx"; token.key_prefix = "--"; token.label = "show particles in one class from a classification matrix"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "classes"; token.key_prefix = "--"; token.label = "show particles associated class-averages"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "pdb"; token.key_prefix = "--"; token.label = "show PDB structure"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "singleimage"; token.key_prefix = "--"; token.label = "display a stack in a single image view"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 2-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "plot3"; token.key_prefix = "--"; token.label = "data file(s) should be plotted rather than displayed in 3-D"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "fullrange"; token.key_prefix = "--"; token.label = "a specialized flag that disables auto contrast for the display of particles stacks and 2D images only"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "newwidget"; token.key_prefix = "--"; token.label = "use the new 3D widgetD. Highly recommended!!!!"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ppid"; token.key_prefix = "--"; token.label = "set the PID of the parent process, used for cross platform PPID"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "-2"; token.restore = "-2"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "verbose"; token.key_prefix = "--"; token.label = "verbose level [0-9], higher number means higher level of verboseness"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxpdb2em"; sxcmd.mode = ""; sxcmd.label = "PDB File Conversion"; sxcmd.short_info = "Convert atomic model (pdb file) into sampled electron density map"; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_utilities"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "input_pdb"; token.key_prefix = ""; token.label = "pdb file with atomic coordinates"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "pdb"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_hdf"; token.key_prefix = ""; token.label = "output 3-D electron density map (any EM format)"; token.help = "Attribute pixel_size will be set to the specified value. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "apix"; token.key_prefix = "--"; token.label = "pixel size (in Angstrom) of the output map"; token.help = ""; token.group = "main"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "apix"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "box"; token.key_prefix = "--"; token.label = "size of the output map in voxels"; token.help = "If not given, the program will find the minimum box size that includes the structre.  However, in most cases this will result in a rectangular box, i.e., each dimension will be different. "; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "box"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "het"; token.key_prefix = "--"; token.label = "Include HET atoms in the map"; token.help = ""; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "center"; token.key_prefix = "--"; token.label = "specify whether to center the atomic model"; token.help = "before converting to electron density map (warning: pdb deposited atomic models are not necesserily centered).  Options: c - center using coordinates of atoms; a - center by setting center of gravity to zero (recommended); a triplet x,y,z (no spaces in between) - coordinates (in Angstrom) to be substracted from all the PDB coordinates. Default: no centering, in which case (0,0,0) in the PDB space will map to the center of the EM volume, i.e., (nx/2, ny/2, nz/2). "; token.group = "main"; token.is_required = False; token.default = "n"; token.restore = "n"; token.type = "string"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "O"; token.key_prefix = "--"; token.label = "apply additional rotation"; token.help = "so the model will appear in O in the same rotation as in chimera. "; token.group = "main"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "tr0"; token.key_prefix = "--"; token.label = "name of a file containing a 3x4 transformation matrix"; token.help = "to be applied to the PDB coordinates after centering, prior to computing the density map. The translation vector (last column of the matrix) must be specified in Angstrom. If this parameter is omitted, no transformation is applied. "; token.group = "main"; token.is_required = False; token.default = "none"; token.restore = "none"; token.type = "parameters"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "quiet"; token.key_prefix = "--"; token.label = "do not print any information to the monitor"; token.help = ""; token.group = "advanced"; token.is_required = False; token.default = False; token.restore = False; token.type = "bool"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		sxcmd = SXcmd(); sxcmd.name = "sxprocess"; sxcmd.mode = "adaptive_mask"; sxcmd.label = "Adaptive 3D Mask"; sxcmd.short_info = "Create adavptive 3D mask from a given 3D volume. "; sxcmd.mpi_support = False; sxcmd.mpi_add_flag = False; sxcmd.category = "sxc_utilities"; sxcmd.role = "sxr_util"; sxcmd.is_submittable = True
		token = SXcmd_token(); token.key_base = "adaptive_mask"; token.key_prefix = "--"; token.label = "Create adavptive 3D mask from a given 3D volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = True; token.restore = True; token.type = "bool"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "input_volume"; token.key_prefix = ""; token.label = "input volume"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "image"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "output_mask3D"; token.key_prefix = ""; token.label = "output 3D mask"; token.help = ""; token.group = "main"; token.is_required = True; token.default = ""; token.restore = ""; token.type = "output"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nsigma"; token.key_prefix = "--"; token.label = "factor of input volume sigma to obtain large density cluster"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "1.0"; token.restore = "1.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ndilation"; token.key_prefix = "--"; token.label = "number of dilations applied to the largest density cluster"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "3"; token.restore = "3"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "kernel_size"; token.key_prefix = "--"; token.label = "convolution kernel for mask edge smoothing"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "11"; token.restore = "11"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "gauss_standard_dev"; token.key_prefix = "--"; token.label = "standard deviation to generate Gaussian edge"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "9"; token.restore = "9"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "threshold"; token.key_prefix = "--"; token.label = "threshold to binarize input volume"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "9999.0"; token.restore = "9999.0"; token.type = "float"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "ne"; token.key_prefix = "--"; token.label = "number of erosions applied to the binarized input image"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)
		token = SXcmd_token(); token.key_base = "nd"; token.key_prefix = "--"; token.label = "number of dilations applied to the binarized input image"; token.help = "main"; token.group = "main"; token.is_required = False; token.default = "0"; token.restore = "0"; token.type = "int"; sxcmd.token_list.append(token)

		sxcmd_list.append(sxcmd)

		# @@@@@ END_INSERTION @@@@@
		
		# Create dictionaries from the constructed lists
		for sxcmd_category in sxcmd_category_list:
			sxcmd_category_dict[sxcmd_category.name] = sxcmd_category
		
		# Create command token dictionary for each SXcmd instance
		# Then, register SXcmd instance to an associated SXcmd_category
		for sxcmd in sxcmd_list:
			for sxcmd_token in sxcmd.token_list:
				# Handle very special cases
				if sxcmd_token.type == "function":
					n_widgets = 2 # function type has two line edit boxes
					sxcmd_token.label = [sxcmd_token.label, "Python script containing the user function"]
					sxcmd_token.help = [sxcmd_token.help, "Please leave it blank if file is not external to sphire"]
					sxcmd_token.default = [sxcmd_token.default, "None"]
					sxcmd_token.restore = sxcmd_token.default
				# else: Do nothing for the other types
			
				# Register this to command token dictionary
				sxcmd.token_dict[sxcmd_token.key_base] = sxcmd_token
			
			# Register this to command to command category dictionary
			assert sxcmd_category_dict.has_key(sxcmd.category), "sxcmd.category %s" % (sxcmd.category)
			sxcmd_category_dict[sxcmd.category].cmd_list.append(sxcmd)
			
		# Store the constructed lists and dictionary as a class data member
		self.sxcmd_category_list = sxcmd_category_list
	
	def handle_sxmenu_item_btn_event(self, sxmenu_item):
		assert(isinstance(sxmenu_item, SXmenu_item) == True) # Assuming the sxmenu_item is an instance of class SXmenu_item
		
		if self.cur_sxmenu_item == sxmenu_item: return
		
		if self.cur_sxmenu_item != None:
			self.cur_sxmenu_item.btn.setStyleSheet(self.cur_sxmenu_item.btn.customButtonStyle)
		
		self.cur_sxmenu_item = sxmenu_item
		
		if self.cur_sxmenu_item != None:
			self.cur_sxmenu_item.btn.setStyleSheet(self.cur_sxmenu_item.btn.customButtonStyleClicked)
			self.sxmenu_item_widget_stacked_layout.setCurrentWidget(self.cur_sxmenu_item.widget)
	
	def closeEvent(self, event):
		event.ignore() # event.accept()
		
		# Quit child applications of all sxcmd widgets
		for sxcmd_category in self.sxcmd_category_list:
			sxcmd_category.widget.quit_all_child_applications()
		
		print("bye bye")
		QtCore.QCoreApplication.instance().quit()

# ========================================================================================
def main(args):
	sxapp = QApplication(args)
	# The valid keys can be retrieved using the keys() function. 
	# Typically they include "windows", "motif", "cde", "plastique" and "cleanlooks".
	# Depending on the platform, "windowsxp", "windowsvista" and "macintosh" may be available. Note that keys are case insensitive.
	# sxapp.setStyle("macintosh")
	sxapp.setStyle("cleanlooks")
	# sxapp.setStyle("plastique")
	
	# print "MRK_DEBUG:"
	# print "MRK_DEBUG: sxapp.style().metaObject().className() == %s" % (str(sxapp.style().metaObject().className()))
	# for key in QStyleFactory.keys():
	# 	print "MRK_DEBUG: str(key) == %s" % str(key)
	# 	print "MRK_DEBUG: QStyleFactory.create(key) = %s" % (str(QStyleFactory.create(key).metaObject().className()))
	# 	if sxapp.style().metaObject().className() == QStyleFactory.create(key).metaObject().className():
	# 		print "MRK_DEBUG: !!!USING THE STYLE: %s!!!" % str(key)
	# print "MRK_DEBUG:"
	
	sxapp.setWindowIcon(QIcon(get_image_directory()+"sparxicon.png"))
	
	sxapp_font = sxapp.font()
	sxapp_font_info = QFontInfo(sxapp.font())
	new_point_size = sxapp_font_info.pointSize() + 1
	# # MRK_DEBUG: Check the default system font
	# print "MRK_DEBUG: sxapp_font_info.style()      = ", sxapp_font_info.style()
	# print "MRK_DEBUG: sxapp_font_info.styleHint()  = ", sxapp_font_info.styleHint()
	# print "MRK_DEBUG: sxapp_font_info.styleName()  = ", sxapp_font_info.styleName()
	# print "MRK_DEBUG: sxapp_font_info.family()     = ", sxapp_font_info.family()
	# print "MRK_DEBUG: sxapp_font_info.fixedPitch() = ", sxapp_font_info.fixedPitch()
	# print "MRK_DEBUG: sxapp_font_info.pixelSize()  = ", sxapp_font_info.pixelSize()
	# print "MRK_DEBUG: sxapp_font_info.pointSize()  = ", sxapp_font_info.pointSize()
	# print "MRK_DEBUG: sxapp_font_info.pointSizeF() = ", sxapp_font_info.pointSizeF()
	# print "MRK_DEBUG: sxapp_font_info.bold ()      = ", sxapp_font_info.bold()
	# print "MRK_DEBUG: sxapp_font_info.italic()     = ", sxapp_font_info.italic()
	# 
	# NOTE: 2019/02/19 Toshio Moriya
	# The following method of changing font size works with Linux.
	# However, it does not work Mac OSX. The text of widget classes below won't change,
	# still showing the default font size:
	# QPushButton, QLable, Window Title, and QToolTip
	# 
	sxapp_font.setPointSize(new_point_size) # and setPointSizeF() are device independent, while setPixelSize() is device dependent
	sxapp.setFont(sxapp_font)
	
	# sxapp.setStyleSheet("QPushButton {font-size:18pt;}");  # NOTE: 2016/02/19 Toshio Moriya: Doesn't work 
	# sxapp.setStyleSheet("QLabel {font-size:18pt;}"); # NOTE: 2016/02/19 Toshio Moriya: Doesn't work 
	# sxapp.setStyleSheet("QToolTip {font-size:14pt; color:white; padding:2px; border-width:2px; border-style:solid; border-radius:20px; background-color: black; border: 1px solid white;}");
	sxapp.setStyleSheet("QToolTip {font-size:%dpt;}" % (new_point_size));
	
	# Initialise a singleton class for look & feel constants
	SXLookFeelConst.initialise(sxapp)
	
	# Define the main window (class SXMainWindow)
	sxmain_window = SXMainWindow()
	sxmain_window.setWindowTitle("SPHIRE-GUI Main (Alpha Version)")
	sxmain_window.setMinimumWidth(SXLookFeelConst.sxmain_window_width)
	sxmain_window.setMinimumHeight(SXLookFeelConst.sxmain_window_height)
	sxmain_window.resize(SXLookFeelConst.sxmain_window_width, SXLookFeelConst.sxmain_window_height)
	sxmain_window.move(QPoint(SXLookFeelConst.sxmain_window_left, SXLookFeelConst.sxmain_window_top));
	
	# Show main window
	sxmain_window.show()
	sxmain_window.raise_()
	
	# Start event handling loop
	sxapp.exec_()

# ========================================================================================
if __name__ == "__main__":
	main(sys.argv)

# ========================================================================================
# END OF SCRIPT
# ========================================================================================

