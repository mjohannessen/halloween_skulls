"""Generator for skull_bases.FCStd - the two skull bases:

  * Control_base_body - the master skull's base. Holds the Pico W (on
    standoffs, micro-USB out the back wall) and a perfboard with the level
    shifter, resistor and bulk cap. A link-cable hole in the right wall
    carries 5V / GND / data to the second skull.
  * Stand_body - the second skull's base. Same shell, empty inside; the
    link cable comes in through its left wall.
  * Lid - one design, print two. A hollow locating tube on top drops into
    the skull's 18 mm base opening, so the skull sits centred on the lid and
    the eye LED wires run straight down through the tube into the box.

The .FCStd it writes is a normal parametric FreeCAD document - edit THAT
file, not this script: every dimension is a cell in the "Params"
spreadsheet, and every part is a Part Box/Cylinder/Cut/Fusion whose sizes and
positions are expressions on those cells. Change a cell, press Recompute,
and the parts and the component placeholders follow. Use File -> Export on
Control_base_body / Stand_body / Lid to make STLs after editing.

Re-run this script only to regenerate from scratch (it won't overwrite an
existing .FCStd unless SKULL_OVERWRITE=1 is set, so hand edits aren't lost):
  freecadcmd skull_bases.py           (or Macro -> Execute in FreeCAD)

The corner fillet radius is fixed when the document is generated (Part::Fillet
radii can't be expressions).

Coordinates: origin is the inside bottom-front-left corner of a box.
X runs left->right, Y front->back, Z up from the inside floor. The skull
faces -Y (front). Stand_body is drawn STAND_OFFSET to the right of the
control base (its Placement) - the offset is display-only.

The skull numbers (opening diameter and position) are measured from
halloween-skull/skull.stl. The Pico W is the standard 51 x 21 mm board.
The perfboard size is a placeholder - measure the real board and change
PERF_L / PERF_W.
"""

import os
import re

import FreeCAD as App
from FreeCAD import Placement, Rotation
from FreeCAD import Vector as V

DOC_NAME = "skull_bases"

# (name, value or "=formula", note). Formulas may reference earlier names.
PARAMS = [
    ("IN_X", 62.0, "inside width (X)"),
    ("IN_Y", 62.0, "inside depth (Y)"),
    ("IN_Z", 24.0, "inside height (Z)"),
    ("WALL", 2.5, "wall thickness"),
    ("FLOOR", 2.5, "floor thickness"),

    ("LID_T", 2.5, "lid plate thickness"),
    ("LIP_H", 3.0, "locating lip height (drops inside the walls)"),
    ("LIP_W", 1.5, "locating lip thickness"),
    ("LIP_CLEAR", 0.3, "gap between lip and inside wall"),

    ("POST", 7.0, "corner post size (square)"),
    ("INSERT_D", 4.0, "M3 heat-set insert hole diameter"),
    ("INSERT_DEPTH", 6.0, "M3 heat-set insert hole depth"),
    ("SCREW_CLEAR_D", 3.4, "lid screw clearance hole"),
    ("SCREW_HEAD_D", 6.2, "lid screw head counterbore diameter"),
    ("SCREW_HEAD_DEPTH", 1.3, "lid screw head counterbore depth"),

    ("SKULL_HOLE_D", 18.0, "skull base opening (BASE_HOLE_D in build_skull.py)"),
    ("SKULL_HOLE_DY", 0.27, "skull opening centre minus skull footprint centre, Y (measured from skull.stl: 6.0 - 5.73)"),
    ("TUBE_CLEAR", 0.3, "radial clearance of the locating tube in the skull opening"),
    ("TUBE_OD", "=SKULL_HOLE_D - 2 * TUBE_CLEAR", "locating tube outside diameter"),
    ("TUBE_ID", 11.0, "locating tube bore - the eye wires pass through it"),
    ("TUBE_H", 5.0, "locating tube height above the lid"),
    ("TUBE_X", "=IN_X / 2", "tube centre X (skull centred on the box)"),
    ("TUBE_Y", "=IN_Y / 2 + SKULL_HOLE_DY", "tube centre Y (skull centred on the box)"),

    ("CRADLE_CLEAR", 0.4, "cradle clearance around PCB"),
    ("CRADLE_FENCE", 1.6, "cradle bracket wall thickness"),
    ("CRADLE_LEDGE_H", 4.0, "PCB underside height in cradle (solder pin room)"),
    ("CRADLE_LEDGE_W", 1.5, "cradle ledge reach under the PCB"),
    ("CRADLE_FENCE_H", 3.0, "cradle fence height above the ledge"),
    ("CRADLE_CORNER", 6.0, "cradle corner bracket arm length"),
    ("PCB_T", 1.6, "perfboard thickness"),

    ("PICO_L", 51.0, "Pico W length (runs along Y, USB end at the back)"),
    ("PICO_W", 21.0, "Pico W width"),
    ("PICO_T", 1.0, "Pico W PCB thickness"),
    ("PICO_HOLE_L1", 2.0, "Pico mounting hole, along the length (board-local)"),
    ("PICO_HOLE_L2", 49.0, "Pico mounting hole, along the length (board-local)"),
    ("PICO_HOLE_W1", 4.8, "Pico mounting hole, across the width (board-local)"),
    ("PICO_HOLE_W2", 16.2, "Pico mounting hole, across the width (board-local)"),
    ("PICO_STANDOFF_H", 5.0, "Pico standoff height"),
    ("PICO_STANDOFF_D", 5.0, "Pico standoff diameter"),
    ("PICO_PILOT_D", 1.8, "Pico standoff pilot hole (M2 self-tapping)"),
    ("PICO_X0", 9.0, "Pico board X (left edge)"),
    ("PICO_Y0", "=IN_Y - 1.5 - PICO_L", "Pico board Y (USB end 1.5 mm from back wall)"),
    ("USB_CUT_W", 12.0, "micro-USB slot width (room for plug overmold)"),
    ("USB_CUT_H", 8.0, "micro-USB slot height"),

    ("PERF_L", 40.0, "perfboard size along Y (placeholder - measure)"),
    ("PERF_W", 22.0, "perfboard size along X (placeholder - measure)"),
    ("PERF_H", 10.0, "perfboard component height (placeholder)"),
    ("PERF_X0", 34.0, "perfboard cradle X"),
    ("PERF_Y0", 10.0, "perfboard cradle Y"),

    ("LINK_HOLE_D", 6.0, "link cable hole (5V / GND / data to the other skull)"),
    ("LINK_Y", "=IN_Y / 2", "link cable hole centre Y"),
    ("LINK_Z", 8.0, "link cable hole centre Z"),

    ("STAND_OFFSET", 100.0, "display-only: how far right Stand_body is drawn"),
]

CORNER_FILLET = 3.0     # outer vertical edge radius


class Builder:
    def __init__(self, doc):
        self.doc = doc
        self.sheet = doc.addObject("Spreadsheet::Sheet", "Params")
        self.names = [p[0] for p in PARAMS]
        self.sheet.set("A1", "Parameter")
        self.sheet.set("B1", "Value (mm)")
        self.sheet.set("C1", "Notes")
        for i, (name, val, note) in enumerate(PARAMS, start=2):
            self.sheet.set("A%d" % i, name)
            self.sheet.set("B%d" % i, str(val))
            self.sheet.set("C%d" % i, note)
            self.sheet.setAlias("B%d" % i, name)
        self.sheet.setColumnWidth("A", 160)
        self.sheet.setColumnWidth("C", 420)
        self._pat = re.compile(r"\b(%s)\b" % "|".join(sorted(self.names, key=len, reverse=True)))

    def expr(self, e):
        return self._pat.sub(r"Params.\1", str(e))

    def _place(self, obj, x, y, z, rot=None):
        if rot is not None:
            obj.Placement = Placement(V(0, 0, 0), rot)
        for axis, e in zip("xyz", (x, y, z)):
            obj.setExpression("Placement.Base." + axis, self.expr(e))

    def box(self, name, x, y, z, dx, dy, dz):
        o = self.doc.addObject("Part::Box", name)
        o.setExpression("Length", self.expr(dx))
        o.setExpression("Width", self.expr(dy))
        o.setExpression("Height", self.expr(dz))
        self._place(o, x, y, z)
        return o

    def cyl(self, name, axis, x, y, z, d, h):
        o = self.doc.addObject("Part::Cylinder", name)
        o.setExpression("Radius", self.expr("(%s) / 2" % d))
        o.setExpression("Height", self.expr(h))
        rot = {"z": None,
               "x": Rotation(V(0, 1, 0), 90),     # cylinder axis Z -> +X
               "y": Rotation(V(1, 0, 0), -90)}[axis]   # cylinder axis Z -> +Y
        self._place(o, x, y, z, rot)
        return o

    def fuse(self, name, shapes):
        o = self.doc.addObject("Part::MultiFuse", name)
        o.Shapes = shapes
        o.Refine = True
        return o

    def cut(self, name, base, tool):
        o = self.doc.addObject("Part::Cut", name)
        o.Base, o.Tool = base, tool
        o.Refine = True
        return o

    def fillet_vertical(self, name, base, r):
        """Fillet the four vertical edges of a Part::Box."""
        self.doc.recompute()
        f = self.doc.addObject("Part::Fillet", name)
        f.Base = base
        edges = []
        for i, e in enumerate(base.Shape.Edges, start=1):
            a, b = e.Vertexes[0].Point, e.Vertexes[-1].Point
            if abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6:
                edges.append((i, r, r))
        f.Edges = edges
        return f


def cradle(b, tag, x0, y0, L, W):
    ox = "(%s + 2 * (CRADLE_CLEAR + CRADLE_FENCE))" % L
    oy = "(%s + 2 * (CRADLE_CLEAR + CRADLE_FENCE))" % W
    oz = "(CRADLE_LEDGE_H + CRADLE_FENCE_H)"
    inset = "(CRADLE_FENCE + CRADLE_CLEAR + CRADLE_LEDGE_W)"
    outer = b.box(tag + "_outer", x0, y0, 0, ox, oy, oz)
    tools = [
        b.box(tag + "_pocket", "%s + CRADLE_FENCE" % x0, "%s + CRADLE_FENCE" % y0, "CRADLE_LEDGE_H",
              "%s + 2 * CRADLE_CLEAR" % L, "%s + 2 * CRADLE_CLEAR" % W, oz),
        b.box(tag + "_under", "%s + %s" % (x0, inset), "%s + %s" % (y0, inset), -1,
              "%s - 2 * %s" % (ox, inset), "%s - 2 * %s" % (oy, inset), "%s + 2" % oz),
        b.box(tag + "_slotX", "%s + CRADLE_CORNER" % x0, "%s - 1" % y0, -1,
              "%s - 2 * CRADLE_CORNER" % ox, "%s + 2" % oy, "%s + 2" % oz),
        b.box(tag + "_slotY", "%s - 1" % x0, "%s + CRADLE_CORNER" % y0, -1,
              "%s + 2" % ox, "%s - 2 * CRADLE_CORNER" % oy, "%s + 2" % oz),
    ]
    return b.cut(tag, outer, b.fuse(tag + "_cuts", tools))


POSTS = [("POST / 2", "POST / 2"), ("IN_X - POST / 2", "POST / 2"),
         ("POST / 2", "IN_Y - POST / 2"), ("IN_X - POST / 2", "IN_Y - POST / 2")]
# Pico runs along Y: board-local length -> global Y, width -> global X.
PICO_HOLES = [("PICO_HOLE_W1", "PICO_HOLE_L1"), ("PICO_HOLE_W2", "PICO_HOLE_L1"),
              ("PICO_HOLE_W1", "PICO_HOLE_L2"), ("PICO_HOLE_W2", "PICO_HOLE_L2")]
USB_X = "(PICO_X0 + PICO_W / 2)"
USB_Z = "(PICO_STANDOFF_H + PICO_T + 1.3)"


def shell(b, tag):
    """Walls, floor and corner posts with insert holes - shared by both bases."""
    outer = b.box(tag + "_outer", "-WALL", "-WALL", "-FLOOR",
                  "IN_X + 2 * WALL", "IN_Y + 2 * WALL", "IN_Z + FLOOR")
    rounded = b.fillet_vertical(tag + "_outer_rounded", outer, CORNER_FILLET)
    walls = b.cut(tag + "_shell", rounded, b.box(tag + "_cavity", 0, 0, 0, "IN_X", "IN_Y", "IN_Z + 1"))
    posts = [b.box("%s_post_%d" % (tag, i), "%s - POST / 2" % cx, "%s - POST / 2" % cy, 0,
                   "POST", "POST", "IN_Z")
             for i, (cx, cy) in enumerate(POSTS, start=1)]
    inserts = [b.cyl("%s_insert_hole_%d" % (tag, i), "z", cx, cy, "IN_Z - INSERT_DEPTH",
                     "INSERT_D", "INSERT_DEPTH + 1")
               for i, (cx, cy) in enumerate(POSTS, start=1)]
    return [walls] + posts, inserts


def build_control_base(b):
    adds, holes = shell(b, "Ctrl")
    for i, (hx, hy) in enumerate(PICO_HOLES, start=1):
        adds.append(b.cyl("Pico_standoff_%d" % i, "z", "PICO_X0 + " + hx, "PICO_Y0 + " + hy, 0,
                          "PICO_STANDOFF_D", "PICO_STANDOFF_H"))
    adds.append(cradle(b, "Perf_cradle", "PERF_X0", "PERF_Y0", "PERF_W", "PERF_L"))
    solid = b.fuse("Ctrl_solid", adds)

    for i, (hx, hy) in enumerate(PICO_HOLES, start=1):
        holes.append(b.cyl("Pico_pilot_%d" % i, "z", "PICO_X0 + " + hx, "PICO_Y0 + " + hy, 0.5,
                           "PICO_PILOT_D", "PICO_STANDOFF_H"))
    holes.append(b.box("USB_slot", "%s - USB_CUT_W / 2" % USB_X, "IN_Y - 1", "%s - USB_CUT_H / 2" % USB_Z,
                       "USB_CUT_W", "WALL + 2", "USB_CUT_H"))
    holes.append(b.cyl("Ctrl_link_hole", "x", "IN_X - 1", "LINK_Y", "LINK_Z", "LINK_HOLE_D", "WALL + 2"))
    return b.cut("Control_base_body", solid, b.fuse("Ctrl_holes", holes))


def build_stand(b):
    adds, holes = shell(b, "Stand")
    solid = b.fuse("Stand_solid", adds)
    holes.append(b.cyl("Stand_link_hole", "x", "-WALL - 1", "LINK_Y", "LINK_Z", "LINK_HOLE_D", "WALL + 2"))
    body = b.cut("Stand_body", solid, b.fuse("Stand_holes", holes))
    body.setExpression("Placement.Base.x", b.expr("STAND_OFFSET"))
    return body


def build_lid(b):
    plate = b.box("Lid_plate_raw", "-WALL", "-WALL", "IN_Z", "IN_X + 2 * WALL", "IN_Y + 2 * WALL", "LID_T")
    rounded = b.fillet_vertical("Lid_plate", plate, CORNER_FILLET)
    lip_outer = b.box("Lip_outer", "LIP_CLEAR", "LIP_CLEAR", "IN_Z - LIP_H",
                      "IN_X - 2 * LIP_CLEAR", "IN_Y - 2 * LIP_CLEAR", "LIP_H")
    lip_cuts = [b.box("Lip_inner", "LIP_CLEAR + LIP_W", "LIP_CLEAR + LIP_W", "IN_Z - LIP_H - 1",
                      "IN_X - 2 * (LIP_CLEAR + LIP_W)", "IN_Y - 2 * (LIP_CLEAR + LIP_W)", "LIP_H + 2")]
    for i, (cx, cy) in enumerate(POSTS, start=1):
        lip_cuts.append(b.box("Lip_post_notch_%d" % i,
                              "%s - POST / 2 - LIP_CLEAR" % cx, "%s - POST / 2 - LIP_CLEAR" % cy,
                              "IN_Z - LIP_H - 1", "POST + 2 * LIP_CLEAR", "POST + 2 * LIP_CLEAR", "LIP_H + 2"))
    lip = b.cut("Lip", lip_outer, b.fuse("Lip_cuts", lip_cuts))
    tube = b.cyl("Locating_tube", "z", "TUBE_X", "TUBE_Y", "IN_Z + LID_T - 0.01", "TUBE_OD", "TUBE_H + 0.01")
    solid = b.fuse("Lid_solid", [rounded, lip, tube])

    holes = [b.cyl("Wire_bore", "z", "TUBE_X", "TUBE_Y", "IN_Z - 1", "TUBE_ID", "LID_T + TUBE_H + 2")]
    for i, (cx, cy) in enumerate(POSTS, start=1):
        holes.append(b.cyl("Lid_screw_%d" % i, "z", cx, cy, "IN_Z - 1", "SCREW_CLEAR_D", "LID_T + 2"))
        holes.append(b.cyl("Lid_counterbore_%d" % i, "z", cx, cy, "IN_Z + LID_T - SCREW_HEAD_DEPTH",
                           "SCREW_HEAD_D", "SCREW_HEAD_DEPTH + 1"))
    return b.cut("Lid", solid, b.fuse("Lid_holes", holes))


def build_components(b):
    """Reference placeholders for checking fit - not printed."""
    pz = "PICO_STANDOFF_H"
    pico = b.fuse("Pico_W", [
        b.box("Pico_pcb", "PICO_X0", "PICO_Y0", pz, "PICO_W", "PICO_L", "PICO_T"),
        b.box("Pico_usb", "%s - 4" % USB_X, "PICO_Y0 + PICO_L - 5", "%s + PICO_T" % pz, 8, 6.3, 2.6),
        b.box("Pico_rf_can", "PICO_X0 + 4", "PICO_Y0 + 3", "%s + PICO_T" % pz, 13, 11, 2),
    ])
    off = "(CRADLE_FENCE + CRADLE_CLEAR)"
    perf = b.box("Perfboard", "PERF_X0 + " + off, "PERF_Y0 + " + off, "CRADLE_LEDGE_H",
                 "PERF_W", "PERF_L", "PCB_T + PERF_H")
    return [pico, perf]


def out_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.expanduser("~/git-projects/halloween_skulls/cad")


def main():
    path = os.path.join(out_dir(), DOC_NAME + ".FCStd")
    if os.path.exists(path) and os.environ.get("SKULL_OVERWRITE") != "1":
        raise RuntimeError("%s exists - edit it in FreeCAD, or set SKULL_OVERWRITE=1 to regenerate" % path)
    if DOC_NAME in App.listDocuments():
        App.closeDocument(DOC_NAME)
    doc = App.newDocument(DOC_NAME)
    b = Builder(doc)

    ctrl, stand, lid = build_control_base(b), build_stand(b), build_lid(b)
    comps = build_components(b)
    grp = doc.addObject("App::DocumentObjectGroup", "Components")
    for c in comps:
        grp.addObject(c)
    doc.recompute()

    bad = [o.Name for o in doc.Objects if "Invalid" in o.State or "Error" in o.State]
    if bad:
        raise RuntimeError("recompute failed: %s" % bad)

    final = {ctrl, stand, lid, *comps}
    for o in doc.Objects:
        if hasattr(o, "Visibility") and o not in final and o is not grp:
            o.Visibility = False
    if App.GuiUp:
        import FreeCADGui as Gui
        lid.ViewObject.Transparency = 70
        for c in comps:
            c.ViewObject.ShapeColor = (0.2, 0.5, 0.9)
        Gui.SendMsgToActiveView("ViewFit")
        Gui.activeDocument().activeView().viewIsometric()

    doc.saveAs(path)
    stl = os.path.join(out_dir(), "stl")
    os.makedirs(stl, exist_ok=True)
    ctrl.Shape.exportStl(os.path.join(stl, "control_base_body.stl"))
    shape = stand.Shape.copy()
    shape.Placement = Placement()       # export the stand at the origin, not at STAND_OFFSET
    shape.exportStl(os.path.join(stl, "stand_body.stl"))
    lid.Shape.exportStl(os.path.join(stl, "lid_x2.stl"))
    for o in (ctrl, stand, lid):
        App.Console.PrintMessage("%s: valid=%s volume=%.0f mm3 bbox=%s\n"
                                 % (o.Name, o.Shape.isValid(), o.Shape.Volume, o.Shape.BoundBox))
    App.Console.PrintMessage("skull bases written to %s\n" % path)
    return doc


# freecadcmd runs a script with __name__ set to its file name, not "__main__".
if __name__ in ("__main__", "skull_bases") or App.GuiUp:
    main()
