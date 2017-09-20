;
M03 S255; lever up pen
;
G90; Positioning defined with reference to part zero.
;
G21; Programming in millimeters (mm)
;
G1 F3000
;
G1  X0 Y0; go to zero
;
M05 S255; lever down pen
;
G1 X0 Y50
G1 X50 Y50
G1 X50 Y0
G1 X0 Y0
;
M03 S255; lever up pen
