"""
Halloween skull with NeoPixel eye pockets - procedural Blender build script.

Run headless:
  Blender -b -P build_skull.py -- <output_dir>
or paste into Blender's Scripting tab and press Run.

Units: 1 Blender unit = 1 mm. Face points toward -Y, Z is up.
"""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.dirname(bpy.data.filepath or os.path.expanduser("~/halloween-skull/"))
DO_RENDER = "--norender" not in argv

# ------------------------------------------------------------------ parameters (mm)
WIDTH = 50.0          # overall skull width
WALL = 2.5            # minimum shell thickness around the hollow cranium
LED_D = 5.3           # bore for the 5 mm NeoPixel body (5.0 + clearance)
LED_FLANGE_D = 6.6    # bore behind the lip, clears the 5.8 mm LED flange
LED_LIP = 3.0         # length of the narrow bore at the socket; LED flange stops here
BASE_HOLE_D = 18.0    # access opening in the bottom (LEDs go in through here)
WIRE_SLOT_W = 5.0     # groove in the base so wires exit out the back
WIRE_SLOT_H = 3.0
VOXEL = 0.3           # remesh resolution
EYE = (11.0, -4.0)    # eye socket centre (x, z) in design space

# ------------------------------------------------------------------ helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    us = bpy.context.scene.unit_settings
    us.system, us.scale_length, us.length_unit = 'METRIC', 0.001, 'MILLIMETERS'

def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o

def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    return link(bpy.data.objects.new(name, me))

def box(name, lo, hi):
    lo, hi = Vector(lo), Vector(hi)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=hi - lo, verts=bm.verts)
    bmesh.ops.translate(bm, vec=(lo + hi) / 2, verts=bm.verts)
    return mesh_obj(name, bm)

def cyl(name, p0, p1, d, seg=64):
    p0, p1 = Vector(p0), Vector(p1)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=d / 2, radius2=d / 2,
                          depth=(p1 - p0).length)
    rot = (p1 - p0).to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ rot, verts=bm.verts)
    return mesh_obj(name, bm)

def ellipsoid(name, c, semi):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=48, radius=1.0)
    bmesh.ops.scale(bm, vec=semi, verts=bm.verts)
    bmesh.ops.translate(bm, vec=c, verts=bm.verts)
    return mesh_obj(name, bm)

def apply_mods(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    bpy.data.meshes.remove(old)

def boolean(target, cutter, op='DIFFERENCE', keep=False):
    m = target.modifiers.new("bool", 'BOOLEAN')
    m.operation, m.object = op, cutter
    try:
        m.solver = 'MANIFOLD'
    except TypeError:
        m.solver = 'EXACT'
    cutter.hide_render = True
    apply_mods(target)
    if not keep:
        bpy.data.objects.remove(cutter)

def bvh(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    t = BVHTree.FromBMesh(bm); bm.free()
    return t

def is_inside(tree, p):
    # odd number of hits along +X ray => inside
    n, o, d = 0, Vector(p), Vector((1, 0.0001, 0.0002)).normalized()
    while True:
        hit = tree.ray_cast(o, d)
        if hit[0] is None:
            return n % 2 == 1
        n += 1
        o = hit[0] + d * 1e-4

def min_wall(tree, obj):
    """Smallest distance from obj's vertices to the surface in tree (all must be inside)."""
    best = 1e9
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        loc, _, _, dist = tree.find_nearest(p)
        if not is_inside(tree, p):
            return -dist
        best = min(best, dist)
    return best

def mesh_stats(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume()
    bm.free()
    return nm, vol

# ------------------------------------------------------------------ organic skull (metaballs)
T = 0.6
def _k(s):  # isolated-element surface radius as fraction of element radius
    return math.sqrt(1 - (T / s) ** (1 / 3))

def ell(mb, c, semi, s=2.0, neg=False, rot=(0, 0, 0)):
    e = mb.elements.new(type='ELLIPSOID')
    m = max(semi)
    e.co = c
    e.radius = m / _k(s)
    e.size_x, e.size_y, e.size_z = (v / m for v in semi)
    e.stiffness = s
    e.use_negative = neg
    e.rotation = Euler([math.radians(a) for a in rot]).to_quaternion()

def sym(mb, c, semi, rot=(0, 0, 0), **kw):
    x, y, z = c
    ell(mb, (x, y, z), semi, rot=rot, **kw)
    ell(mb, (-x, y, z), semi, rot=(rot[0], -rot[1], -rot[2]), **kw)

def build_organic():
    mb = bpy.data.metaballs.new("SkullMB")
    mb.resolution = mb.render_resolution = 0.5
    mb.threshold = T
    mbo = link(bpy.data.objects.new("SkullMB", mb))

    # cranium
    ell(mb, (0, 6, 13), (23, 31, 23))
    ell(mb, (0, -12, 12), (19, 12, 15))            # forehead
    ell(mb, (0, 26, 5), (17, 11, 12))              # occiput
    # brow + upper face
    ell(mb, (0, -21, 1), (21, 6, 5))               # brow ridge
    ell(mb, (0, -17, -5), (20, 9, 10))             # orbit block
    sym(mb, (17, -17, -8), (7, 7, 6))              # cheekbones
    sym(mb, (19.5, -7, -7), (3, 7, 2.5))               # zygomatic arches
    # maxilla + upper teeth
    ell(mb, (0, -17, -17), (15, 10, 9))
    ell(mb, (0, -21, -24), (13, 7, 5))
    # mandible
    ell(mb, (0, -21, -30), (13, 7, 4.5))           # lower teeth
    ell(mb, (0, -19, -37), (12, 7, 6))             # chin
    sym(mb, (12, -11, -35), (5, 10, 5), rot=(0, 0, -30))    # jaw body
    sym(mb, (17, -1, -31), (5, 6, 6))              # jaw angle
    sym(mb, (18, 0, -20), (3.5, 6, 9))             # ramus
    # base / neck filler so it stands on a flat footprint
    ell(mb, (0, 5, -22), (16, 16, 20))

    # carve-outs
    sym(mb, (EYE[0], -27, EYE[1]), (7.5, 9, 6.5), s=8.0, neg=True)   # eye sockets
    ell(mb, (0, -27, -13), (5, 5, 7), s=4.0, neg=True)              # recess round the nose

    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(mbo.evaluated_get(dg))
    bpy.data.objects.remove(mbo)
    return link(bpy.data.objects.new("Skull", me))

def prism(name, outline, y0, y1):
    """Extrude a closed (x, z) outline along Y."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in outline]
    b = [bm.verts.new((x, y1, z)) for x, z in outline]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(a[::-1]); bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    return mesh_obj(name, bm)

def nose_cut(skull, s):
    half = [(0, -6.5), (1.8, -9), (3.4, -12.5), (4.4, -15.5), (3.8, -18.2), (1.6, -19.0), (0, -17.8)]
    pts = half + [(-x, z) for x, z in reversed(half[1:-1])]
    boolean(skull, prism("nose", [(x * s, z * s) for x, z in pts], -45 * s, -19 * s))

def ring(name, c, r_in, r_out, z0, z1):
    outer = cyl(name, (c[0], c[1], z0), (c[0], c[1], z1), 2 * r_out, seg=128)
    boolean(outer, cyl("in", (c[0], c[1], z0 - 1), (c[0], c[1], z1 + 1), 2 * r_in, seg=128))
    return outer

def teeth_cuts(skull, s):
    cx, cy = 0, -11 * s
    # mouth line between upper and lower teeth (shallow, follows the dental arch)
    groove = ring("groove", (cx, cy), 12.5 * s, 30 * s, -27.6 * s, -26.8 * s)
    boolean(groove, box("back", (-100, -18 * s, -100), (100, 100, 100)))
    boolean(skull, groove)
    # gaps between teeth, radial around the arch
    for i in range(-5, 6):
        a = math.radians(i * 11 + 5.5)
        d = Vector((math.sin(a), -math.cos(a), 0))
        p0 = Vector((cx, cy, -31.5 * s)) + d * 13 * s
        slot = box("slot", (-0.3, -12 * s, 0), (0.3, 0, 9 * s))
        slot.matrix_world = Matrix.Translation(p0) @ d.to_track_quat('-Y', 'Z').to_matrix().to_4x4()
        apply_world(slot)
        boolean(skull, slot)

def apply_world(o):
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)

# ------------------------------------------------------------------ build
def build():
    reset()
    skull = build_organic()

    # weld into one clean manifold surface, then soften voxel steps
    m = skull.modifiers.new("remesh", 'REMESH'); m.mode, m.voxel_size = 'VOXEL', VOXEL
    m = skull.modifiers.new("smooth", 'LAPLACIANSMOOTH'); m.iterations, m.lambda_factor = 4, 0.4
    apply_mods(skull)

    # scale to exact width
    xs = [v.co.x for v in skull.data.vertices]
    s = WIDTH / (max(xs) - min(xs))
    skull.data.transform(Matrix.Scale(s, 4))
    print(f"scale factor {s:.3f}")

    nose_cut(skull, s)
    teeth_cuts(skull, s)
    outer = bvh(skull)

    # --- hollow: cranium lobe + a lobe behind the eyes, each the largest that keeps WALL
    cavs = []
    for c0, semi0 in (((0, 6, 13), (23, 31, 23)), ((0, -1, -1), (17, 13, 10))):
        c0, semi0 = Vector(c0) * s, Vector(semi0) * s
        f = 1.0
        while True:
            cav = ellipsoid("cavity", c0, semi0 * f)
            w = min_wall(outer, cav)
            if w >= WALL:
                break
            bpy.data.objects.remove(cav)
            f -= 0.02
        print(f"cavity lobe factor {f:.2f}, min wall {w:.2f} mm")
        cavs.append(cav)
    c0 = cavs[0].location + Vector((0, 6, 13)) * s
    cav_trees = [bvh(c) for c in cavs]

    zs = [v.co.z for v in skull.data.vertices]
    zmin = min(zs)
    zcut = zmin + 3.0
    shaft_c = Vector((0, 6 * s, 0))

    # --- LED bores in each eye socket
    leds = []
    for sx in (1, -1):
        ex, ez = sx * EYE[0] * s, EYE[1] * s
        hit = outer.ray_cast(Vector((ex, -200, ez)), Vector((0, 1, 0)))
        yb = hit[0].y                                   # back of the eye socket
        hits = [t.ray_cast(Vector((ex, yb, ez)), Vector((0, 1, 0)))[0] for t in cav_trees]
        hits = [h.y for h in hits if h is not None]
        if not hits:
            raise RuntimeError("LED bore does not reach the cavity")
        yc = min(hits)
        leds.append((ex, ez, yb, yc))
        print(f"LED {'R' if sx > 0 else 'L'}: socket back y={yb:.1f}, cavity y={yc:.1f}, "
              f"solid between {yc - yb:.1f} mm")

    # --- cuts
    for cav in cavs:
        boolean(skull, cav)
    shaft = cyl("shaft", (shaft_c.x, shaft_c.y, zcut - 5), (shaft_c.x, shaft_c.y, c0.z), BASE_HOLE_D)
    boolean(skull, shaft)
    for ex, ez, yb, yc in leds:
        boolean(skull, cyl("led", (ex, yb - 3, ez), (ex, yb + LED_LIP, ez), LED_D))
        boolean(skull, cyl("ledf", (ex, yb + LED_LIP, ez), (ex, yc + 3, ez), LED_FLANGE_D))
    boolean(skull, box("floor", (-100, -100, zmin - 50), (100, 100, zcut)))
    boolean(skull, box("wireslot", (-WIRE_SLOT_W / 2, shaft_c.y, zcut - 1),
                       (WIRE_SLOT_W / 2, 100, zcut + WIRE_SLOT_H)))

    # move so it sits on z=0
    skull.data.transform(Matrix.Translation((0, 0, -zcut)))
    for p in skull.data.polygons:
        p.use_smooth = True

    nm, vol = mesh_stats(skull)
    bb = [skull.matrix_world @ Vector(c) for c in skull.bound_box]
    dims = [max(v[i] for v in bb) - min(v[i] for v in bb) for i in range(3)]
    print(f"size W{dims[0]:.1f} x D{dims[1]:.1f} x H{dims[2]:.1f} mm, "
          f"volume {vol / 1000:.1f} cm3, non-manifold edges {nm}, faces {len(skull.data.polygons)}")
    return skull, leds, zcut

# ------------------------------------------------------------------ preview renders
def render_views(skull, leds, zcut):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x = sc.render.resolution_y = 700
    sh = sc.display.shading
    sh.light, sh.color_type = 'STUDIO', 'SINGLE'
    sh.single_color = (0.85, 0.80, 0.68)
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.show_shadows = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new("W")
    sc.world.color = (0.12, 0.12, 0.14)

    cam = link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    cam.data.type, cam.data.ortho_scale, cam.data.clip_end = 'ORTHO', 95, 2000
    sc.camera = cam
    tgt = Vector((0, 4, 36))

    def shot(name, d, obj=skull):
        d = Vector(d).normalized()
        cam.location = tgt + d * 300
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        for o in sc.objects:
            if o.type == 'MESH':
                o.hide_render = o is not obj
        sc.render.filepath = os.path.join(OUT, "renders", name + ".png")
        bpy.ops.render.render(write_still=True)

    shot("front", (0, -1, 0))
    shot("three_quarter", (-1, -1.3, 0.45))
    shot("side", (1, 0, 0))
    shot("back", (0.6, 1, 0.3))
    shot("bottom", (0.0001, 0, -1))

    # cross-sections
    for name, x in (("section_center", 0.0), ("section_eye", leds[0][0])):
        sec = skull.copy(); sec.data = skull.data.copy(); link(sec)
        boolean(sec, box("half", (x, -200, -200), (200, 200, 200)))
        shot(name, (1, 0, 0), sec)
        bpy.data.objects.remove(sec)
    bpy.data.objects.remove(cam)

def write_stl(obj, path):
    """Binary STL straight from the mesh triangles (mm)."""
    import struct
    me = obj.data
    me.calc_loop_triangles()
    m = obj.matrix_world
    with open(path, "wb") as f:
        f.write(b"Halloween skull".ljust(80, b" "))
        f.write(struct.pack("<I", len(me.loop_triangles)))
        for t in me.loop_triangles:
            vs = [m @ me.vertices[i].co for i in t.vertices]
            n = (vs[1] - vs[0]).cross(vs[2] - vs[0]).normalized()
            f.write(struct.pack("<12fH", *n, *vs[0], *vs[1], *vs[2], 0))
    print(f"wrote {path}: {len(me.loop_triangles)} triangles")

# ------------------------------------------------------------------ main
skull, leds, zcut = build()
if DO_RENDER:
    render_views(skull, leds, zcut)
for o in list(bpy.context.scene.objects):
    if o is not skull:
        bpy.data.objects.remove(o)
bpy.ops.object.select_all(action='DESELECT')
skull.select_set(True)
bpy.context.view_layer.objects.active = skull
write_stl(skull, os.path.join(OUT, "skull.stl"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "skull.blend"))
print("done")
