#lever up pen
M03 S255

#Positioning defined with reference to part zero.
G90

#Programming in millimeters (mm)
G21

G1 F3000

#go to zero
G1  X0 Y0

#lever down pen
M05 S255

G2 X0 Y50
G2 X50 Y50
G2 X50 Y0
G2 X0 Y0


#lever up pen
M03 S255
