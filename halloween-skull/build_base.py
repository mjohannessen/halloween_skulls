"""
Cemetery-stone skull base - procedural Blender build script.

A weathered stone grave pedestal: two stepped base courses cut into blocks, a
drum with a Gothic lancet niche on each of its four sides, a projecting cap stone
with five crouching winged gargoyles on its ledge, and a stout stone column. The
stone is voxel-remeshed and displaced with noise so it reads as worn, with
chipped edges; the gargoyles (metaballs) go on after that so their faces stay
crisp. The functional parts are added after the weathering so they
stay exact: a 23 mm seat cut from the skull model itself (skull.blend), so it
matches the skull's sloped underside; a spigot that fits up into the skull's
opening; a centre hole for the LED's four wires; a cone-shaped splice cavity
underneath; and a notch at the back where the chain pigtails leave.

Run headless (after build_skull.py, which writes skull.blend):
  Blender -b -P build_base.py -- <output_dir>

Units: 1 Blender unit = 1 mm. Front is -Y (the way the skull faces), Z is up.
Prints as modelled: plinth on the bed, no supports.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.dirname(bpy.data.filepath or os.path.expanduser("~/halloween-skull/"))
DO_RENDER = "--norender" not in argv
SKULL_BLEND = os.path.join(OUT, "skull.blend")

# ------------------------------------------------------------------ parameters (mm)
BASE_D = 62.0         # bottom course diameter
PLINTH_H = 28.5       # height of the pedestal (top of the cap stone's weathering slope)
STEM_H = 20.0         # pedestal top to the seat (the lowest point the skull touches)
SEAT_D = 23.0         # diameter of the seat the skull sits on
SEAT_T = 3.0          # seat thickness below its lowest point
SEAT_CLEAR = 0.2      # gap between seat and skull surface, for glue and print tolerance
SKULL_HOLE_C = (0.0, 6.0)   # centre of the skull's base opening, in skull.blend coordinates
SKULL_HOLE_D = 18.0   # the skull's base opening as modelled (BASE_HOLE_D in build_skull.py)
SPIGOT_D = 16.6       # locating spigot into the opening (prints of the 18 mm hole measure ~17)
SPIGOT_H = 6.0        # spigot height above the seat's lowest point
WIRE_HOLE_D = 5.0     # four 22 AWG wires (1.6-2.0 mm insulation) bundle to 3.9-4.8 mm
CAVITY_D = 44.0       # splice cavity under the pedestal, 45-degree cone so it prints unsupported
NOTCH_W = 12.0        # pigtail exit notch at the back, two 3-wire JST pigtails
NOTCH_H = 6.0
DRUM_D = 51.0         # the carved drum between the base courses and the cap stone
NICHE_W = 6.5         # lancet niches, one on each side
NICHE_DEPTH = 1.6
COLUMN_D = 16.0       # stone column, tapering slightly towards the top
GARGOYLES = 5         # crouching gargoyles on the cap stone ledge, facing out, one at the front
GARGOYLE_R = 22.0     # radius of each gargoyle's centre (between its hind and front feet)
GARGOYLE_SCALE = 1.0  # 1.0 = ~13 mm tall, ~10 mm wide
JOINT_W = 0.8         # mortar joints between the base course blocks
JOINT_DEPTH = 0.7
WEATHER = 0.35        # noise displacement amplitude on the stone (mm)
CHIPS = 22            # chipped edges
SEED = 13             # change for a different pattern of chips (each skull can differ)
VOXEL = 0.25          # remesh resolution before weathering

R = BASE_D / 2
DRUM_R = DRUM_D / 2
Z_TOP = PLINTH_H + STEM_H      # the seat's lowest point

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

def cone(name, z0, z1, r0, r1, c=(0, 0), seg=96):
    """Vertical cylinder or cone from z0 (radius r0) to z1 (radius r1)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r0, radius2=r1, depth=z1 - z0)
    bmesh.ops.translate(bm, vec=(c[0], c[1], (z0 + z1) / 2), verts=bm.verts)
    return mesh_obj(name, bm)

def lathe(name, profile, seg=160):
    """Solid of revolution about Z from a closed (r, z) outline that starts and ends on the axis."""
    bm = bmesh.new()
    bot = bm.verts.new((0, 0, profile[0][1]))
    top = bm.verts.new((0, 0, profile[-1][1]))
    inner = profile[1:-1]
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))
              for i in range(seg)] for r, z in inner]
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((bot, rings[0][j], rings[0][i]))
        bm.faces.new((top, rings[-1][i], rings[-1][j]))
        for k in range(len(rings) - 1):
            bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj(name, bm)

def facing_prism(name, outline, r0, r1, angle):
    """Extrude a closed (x, z) outline radially from r0 to r1 in front of the axis, then turn it
    to face `angle` (0 = front, -Y). Used for niches and joints."""
    bm = bmesh.new()
    a = [bm.verts.new((x, -r0, z)) for x, z in outline]
    b = [bm.verts.new((x, -r1, z)) for x, z in outline]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(a[::-1]); bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(angle, 3, 'Z'))
    return mesh_obj(name, bm)

def pointed_arch(w, z0, zs, rad, n=10):
    """Closed (x, z) outline: a w-wide opening from z0, springing at zs, two-centred arch of radius rad."""
    off = rad - w / 2
    rise = math.sqrt(rad ** 2 - off ** 2)
    pts = [(-w / 2, z0), (w / 2, z0), (w / 2, zs)]
    a_end = math.degrees(math.atan2(rise, -off))
    for i in range(1, n + 1):                       # right half, centred left of the axis
        a = math.radians(a_end * i / n)
        pts.append((-off + rad * math.cos(a), zs + rad * math.sin(a)))
    for i in range(n - 1, -1, -1):                  # left half, mirrored
        a = math.radians(a_end * i / n)
        pts.append((off - rad * math.cos(a), zs + rad * math.sin(a)))
    return pts

def remesh(obj, voxel):
    m = obj.modifiers.new("remesh", 'REMESH')
    m.mode, m.voxel_size = 'VOXEL', voxel
    apply_mods(obj)

def apply_mods(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    bpy.data.meshes.remove(old)

def boolean(target, cutter, op='DIFFERENCE', keep=False, solver='MANIFOLD'):
    m = target.modifiers.new("bool", 'BOOLEAN')
    m.operation, m.object = op, cutter
    try:
        m.solver = solver
    except TypeError:
        m.solver = 'EXACT'
    cutter.hide_render = True
    apply_mods(target)
    if not keep:
        bpy.data.objects.remove(cutter)

def mesh_stats(obj):
    """Non-manifold edge count, volume and number of separate pieces (must be 1 to print)."""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume()
    seen, parts = set(), 0
    for v in bm.verts:
        if v.index in seen:
            continue
        parts += 1
        stack = [v]; seen.add(v.index)
        while stack:
            u = stack.pop()
            for e in u.link_edges:
                w = e.other_vert(u)
                if w.index not in seen:
                    seen.add(w.index); stack.append(w)
    bm.free()
    return nm, vol, parts

# ------------------------------------------------------------------ gargoyle
def gargoyle():
    """A crouching winged gargoyle built from metaballs, facing -Y, feet on z = 0, in mm.
    Hunched dog-like pose: haunches behind, straight forelegs, head on the chest so the
    snout only overhangs a little, folded wings rising behind the head; prints unsupported."""
    mb = bpy.data.metaballs.new("gargoyle")
    mb.resolution = mb.render_resolution = 0.18
    mb.threshold = 0.6
    obj = link(bpy.data.objects.new("gargoyle", mb))
    K = 1.74                          # field radius for a surface at ~1.0 (stiffness 2, threshold 0.6)

    def el(co, semi, rot=(0, 0, 0), neg=False, mirror=True):
        for sx in ((1, -1) if mirror and co[0] else (1,)):
            e = mb.elements.new(type='ELLIPSOID')
            e.co = (co[0] * sx, co[1], co[2])
            e.radius = K
            e.size_x, e.size_y, e.size_z = semi
            e.rotation = Euler((rot[0], rot[1] * sx, rot[2] * sx)).to_quaternion()
            e.use_negative = neg

    d = math.radians
    el((0, 1.5, 2.0), (2.7, 2.4, 2.0))                          # haunches
    el((2.5, 0.8, 2.1), (1.4, 2.4, 1.8), (d(-25), 0, 0))        # thighs, knees up
    el((2.4, -1.1, 0.55), (1.1, 1.8, 0.6))                      # hind feet
    el((0, 0.2, 5.0), (2.3, 2.0, 2.8), (d(35), 0, 0))           # torso, hunched forward
    el((0, -1.5, 6.0), (2.2, 1.6, 1.9))                         # chest
    el((2.2, -0.9, 7.4), (1.5, 1.4, 1.3))                       # high, bony shoulders
    el((0, 0.6, 7.8), (1.6, 1.3, 1.0))                          # hump between the shoulders
    el((1.8, -2.4, 3.6), (0.95, 0.95, 2.9), (d(-12), 0, 0))     # forelegs
    el((1.7, -3.4, 0.55), (1.1, 1.4, 0.6))                      # front paws
    for x in (0.0, 0.75):
        el((1.7 + x - 0.375, -4.6, 0.45), (0.35, 0.5, 0.35))    # claws
    el((0, -2.9, 8.2), (1.9, 1.9, 1.7))                         # head, low between the shoulders
    el((0, -4.6, 8.0), (1.5, 1.4, 0.85), (d(10), 0, 0))         # broad upper muzzle
    el((0, -4.3, 6.9), (1.3, 1.3, 0.55), (d(-10), 0, 0))        # lower jaw, hanging open
    el((0, -5.6, 7.45), (1.2, 0.9, 0.28), neg=True)             # mouth
    el((0, -4.0, 9.2), (1.9, 0.8, 0.6), (d(-10), 0, 0))         # heavy brow
    el((0.8, -4.55, 8.75), (0.42, 0.4, 0.38), neg=True)         # eye sockets under the brow
    el((1.4, -2.2, 10.2), (0.5, 0.5, 1.6), (d(-55), d(15), 0))  # horns, swept back
    el((1.6, -0.8, 11.0), (0.35, 0.35, 1.0), (d(-95), d(10), 0))  #  and curling down at the tips
    el((2.1, -2.0, 9.0), (0.3, 0.9, 0.7), (d(-30), d(35), 0))   # pointed ears
    # bat wings, folded half open: one overlapping chain from the shoulder blade up to the tip
    el((2.3, 0.9, 7.6), (0.8, 1.8, 1.6))                        # wing root
    el((2.7, 2.1, 8.7), (0.6, 2.0, 2.3), (d(-20), d(18), 0))    # main membrane
    el((3.0, 2.8, 10.4), (0.5, 1.3, 1.6), (d(-30), d(18), 0))   # upper finger
    el((3.2, 3.3, 11.8), (0.4, 0.7, 1.1), (d(-35), d(18), 0))   # tip, above the head
    el((2.7, 3.3, 6.8), (0.5, 1.3, 1.3), (d(20), d(18), 0))     # trailing scallop
    el((0, 3.7, 1.0), (0.75, 2.0, 0.7), (d(-10), 0, 0))         # tail along the ledge
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    bpy.data.objects.remove(obj)
    g = link(bpy.data.objects.new("gargoyle", me))
    g.data.transform(Matrix.Scale(GARGOYLE_SCALE, 4))
    remesh(g, 0.1)                                  # one closed manifold for the boolean
    tex = bpy.data.textures.new("garg_stone", 'CLOUDS')
    tex.noise_scale, tex.noise_depth, tex.noise_basis = 0.8, 2, 'VORONOI_F2'
    m = g.modifiers.new("stone", 'DISPLACE')
    m.texture, m.texture_coords, m.strength, m.mid_level = tex, 'LOCAL', 0.18, 0.5
    apply_mods(g)                                   # light pitting to match the weathered stone
    return g

def place_gargoyles(base):
    """Union GARGOYLES copies onto the cap stone, each sunk 0.4 mm below the lowest point
    of the weathered ledge under its footprint so it is fused all round."""
    tree = BVHTree.FromObject(base, bpy.context.evaluated_depsgraph_get())
    proto = gargoyle()
    foot = [(x * GARGOYLE_SCALE, y * GARGOYLE_SCALE) for x in (-2.4, 0, 2.4) for y in (-4.8, -3.4, 0, 1.6, 4.0)]
    for k in range(GARGOYLES):
        rot = Matrix.Rotation(2 * math.pi * k / GARGOYLES, 4, 'Z')
        zs = []
        for x, y in foot:
            p = rot @ Vector((x, y - GARGOYLE_R, 0))
            hit = tree.ray_cast(Vector((p.x, p.y, PLINTH_H + 6)), Vector((0, 0, -1)))
            zs.append(hit[0].z if hit[0] is not None else PLINTH_H - 3)
        g = proto.copy(); g.data = proto.data.copy(); link(g)
        g.data.transform(rot @ Matrix.Translation((0, -GARGOYLE_R, min(zs) - 0.4)))
        boolean(base, g, 'UNION')
    bpy.data.objects.remove(proto)

# ------------------------------------------------------------------ skull (for the seat and the assembly view)
def load_skull():
    with bpy.data.libraries.load(SKULL_BLEND) as (src, dst):
        dst.objects = [n for n in src.objects if n == "Skull"]
    sk = link(dst.objects[0])
    sk.name = "SkullRef"
    # lowest point of the underside within the seat, around the opening
    bm = bmesh.new(); bm.from_mesh(sk.data); tree = BVHTree.FromBMesh(bm); bm.free()
    zmin = 1e9
    cx, cy = SKULL_HOLE_C
    for ri in range(0, 21):
        r = SKULL_HOLE_D / 2 + 0.05 + (SEAT_D / 2 - SKULL_HOLE_D / 2 - 0.05) * ri / 20
        for ai in range(0, 360, 3):
            a = math.radians(ai)
            hit = tree.ray_cast(Vector((cx + r * math.cos(a), cy + r * math.sin(a), -20)), Vector((0, 0, 1)))
            if hit[0] is not None:
                zmin = min(zmin, hit[0].z)
    sk.data.transform(Matrix.Translation((-cx, -cy, Z_TOP - zmin)))
    print(f"skull underside: lowest point in the seat {zmin:.2f} mm above the skull's chin plane")
    return sk

def underside_cutter(skull):
    """Everything above the skull's underside over the seat's annulus, lowered by SEAT_CLEAR.
    Cutting this (rather than the skull itself) leaves no material standing up round the neck."""
    bm = bmesh.new(); bm.from_mesh(skull.data); tree = BVHTree.FromBMesh(bm); bm.free()
    r_in, r_out, nr, na = SKULL_HOLE_D / 2 + 0.1, SEAT_D / 2 + 1.0, 18, 120
    z_hi = Z_TOP + 30
    bm = bmesh.new()
    low, high = [], []
    for i in range(nr + 1):
        r = r_in + (r_out - r_in) * i / nr
        lo_row, hi_row = [], []
        for j in range(na):
            a = 2 * math.pi * j / na
            x, y = r * math.cos(a), r * math.sin(a)
            hit = tree.ray_cast(Vector((x, y, Z_TOP - 20)), Vector((0, 0, 1)))
            z = hit[0].z if hit[0] is not None and hit[0].z < Z_TOP + 15 else Z_TOP + 15
            lo_row.append(bm.verts.new((x, y, z - SEAT_CLEAR)))
            hi_row.append(bm.verts.new((x, y, z_hi)))
        low.append(lo_row); high.append(hi_row)
    for j in range(na):
        k = (j + 1) % na
        for i in range(nr):
            bm.faces.new((low[i][j], low[i + 1][j], low[i + 1][k], low[i][k]))      # underside surface
            bm.faces.new((high[i][j], high[i][k], high[i + 1][k], high[i + 1][j]))  # flat top
        for rows, i in ((0, 0), (1, nr)):                                            # inner and outer walls
            q = (low[i][j], low[i][k], high[i][k], high[i][j])
            bm.faces.new(q if rows == 0 else q[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_obj("underside", bm)

# ------------------------------------------------------------------ build
def build():
    reset()
    skull = load_skull()

    rnd = random.Random(SEED)

    # --- stone pedestal, one solid of revolution: two base courses, drum, cap stone, column
    zc1, zc2, zd, zcap = 4.5, 9.0, 22.0, 25.0         # tops of: course 1, course 2, drum, cap stone edge
    r2 = R - 2.5
    rcap = DRUM_R + 2.5
    rcol = COLUMN_D / 2
    zcap0 = Z_TOP - SEAT_T - 4.0                       # column capital starts flaring here
    p = [(0, -1.0), (R, -1.0), (R, zc1 - 0.6), (R - 0.6, zc1),          # course 1 (from below the bed;
         (r2, zc1), (r2, zc2 - 1.2), (r2 - 1.2, zc2),                    #  the bottom is cut flat later)
         (DRUM_R, zc2), (DRUM_R, zd),                                    # course 2, drum
         (rcap, zd + 2.5 - 0.0), (rcap, zcap + 0.6), (rcap - 0.6, zcap + 1.0),   # cap stone, 45-degree underside
         (rcol + 3.0, PLINTH_H - 1.2), (rcol + 2.2, PLINTH_H),           # weathering slope, column base block
         (rcol + 2.2, PLINTH_H + 1.4), (rcol + 0.4, PLINTH_H + 3.2),     #  with a 45-degree chamfer
         (rcol, PLINTH_H + 3.2), (rcol - 0.7, zcap0),                   # shaft, slight taper
         (SEAT_D / 2 - 0.2, zcap0 + (SEAT_D / 2 - 0.2 - rcol + 0.7)),   # capital, 45 degrees
         (SEAT_D / 2 - 0.2, Z_TOP - SEAT_T + 0.5), (0, Z_TOP - SEAT_T + 0.5)]
    base = lathe("SkullBase", p)

    # --- mortar joints: course 1 in 10 blocks, course 2 in 9, staggered
    for n, r_out, z0, z1, phase in ((10, R, -1.0, zc1 + 0.1, 0.5), (9, r2, zc1 - 0.1, zc2 + 0.1, 0.0)):
        for k in range(n):
            ang = 2 * math.pi * (k + phase) / n
            boolean(base, facing_prism("joint", [(-JOINT_W / 2, z0), (JOINT_W / 2, z0),
                                                 (JOINT_W / 2, z1), (-JOINT_W / 2, z1)],
                                       r_out - JOINT_DEPTH, r_out + 2, ang))

    # --- lancet niches, one on each side
    niche = pointed_arch(NICHE_W, zc2 + 1.5, zc2 + 6.0, NICHE_W * 0.85)
    for ang in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
        boolean(base, facing_prism("niche", niche, DRUM_R - NICHE_DEPTH, DRUM_R + 3, ang))

    # --- chipped edges: irregular bites out of the upper outside edges
    edges = [(R, zc1), (r2, zc2), (rcap, zcap + 0.8), (rcol + 2.2, PLINTH_H + 1.4)]
    for i in range(CHIPS):
        r_e, z_e = edges[i % len(edges)]
        a = rnd.uniform(0, 2 * math.pi)
        if abs(math.atan2(math.sin(a), math.cos(a)) + math.pi / 2) < 0.45 and r_e == R:
            a += 0.9                                    # keep chips off the front of the bottom course
        size = rnd.uniform(1.0, 2.2) * (0.6 if r_e < 15 else 1.0)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=size)
        for v in bm.verts:
            v.co *= rnd.uniform(0.7, 1.3)
        bmesh.ops.scale(bm, vec=(rnd.uniform(1.2, 2.0), rnd.uniform(0.8, 1.2), rnd.uniform(0.6, 1.0)),
                        verts=bm.verts)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=Matrix.Rotation(a + math.pi / 2, 3, 'Z'))
        bmesh.ops.translate(bm, vec=(r_e * math.cos(a), r_e * math.sin(a), z_e + 0.2), verts=bm.verts)
        boolean(base, mesh_obj("chip", bm))

    # --- weathering: remesh into an even surface, then displace with two scales of noise
    remesh(base, VOXEL)
    for name, scale, amp in (("coarse", 5.0, WEATHER), ("fine", 1.2, WEATHER * 0.45)):
        tex = bpy.data.textures.new(name, 'CLOUDS')
        tex.noise_scale, tex.noise_depth = scale, 3
        tex.noise_basis = 'ORIGINAL_PERLIN' if name == "coarse" else 'VORONOI_F2'
        m = base.modifiers.new(name, 'DISPLACE')
        m.texture, m.texture_coords, m.strength, m.mid_level = tex, 'LOCAL', amp * 2, 0.5
    m = base.modifiers.new("decimate", 'DECIMATE')
    m.ratio = 0.35
    apply_mods(base)
    boolean(base, box("bed", (-100, -100, -10), (100, 100, 0)))   # flat bottom for the bed

    # --- gargoyles on the cap stone ledge, added after weathering so their detail stays crisp
    place_gargoyles(base)

    # --- seat: a 23 mm block with the skull's underside cut out of it
    seat = cone("seat", Z_TOP - SEAT_T, Z_TOP + 8.0, SEAT_D / 2, SEAT_D / 2, seg=128)
    boolean(seat, underside_cutter(skull))
    boolean(seat, cone("opening", Z_TOP - SEAT_CLEAR - 0.05, Z_TOP + 20, SKULL_HOLE_D / 2 + 0.2,
                       SKULL_HOLE_D / 2 + 0.2, seg=128))
    boolean(base, seat, 'UNION')
    boolean(base, cone("spigot", Z_TOP - 1.0, Z_TOP + SPIGOT_H - 0.6, SPIGOT_D / 2, SPIGOT_D / 2,
                       seg=128), 'UNION')
    boolean(base, cone("spigot_tip", Z_TOP + SPIGOT_H - 0.6, Z_TOP + SPIGOT_H, SPIGOT_D / 2,
                       SPIGOT_D / 2 - 0.6, seg=128), 'UNION')                     # lead-in chamfer

    # --- wire path: centre hole, splice cavity, pigtail notch at the back
    boolean(base, cone("wirehole", -1, Z_TOP + SPIGOT_H + 1, WIRE_HOLE_D / 2, WIRE_HOLE_D / 2, seg=48))
    rc = CAVITY_D / 2
    boolean(base, cone("cavity", -1, rc - 1, rc + 1, 0.0))
    boolean(base, box("notch", (-NOTCH_W / 2, 0, -1), (NOTCH_W / 2, R + 5, NOTCH_H)))

    for f in base.data.polygons:
        f.use_smooth = True
    nm, vol, parts = mesh_stats(base)
    bb = [Vector(c) for c in base.bound_box]
    dims = [max(v[i] for v in bb) - min(v[i] for v in bb) for i in range(3)]
    print(f"base W{dims[0]:.1f} x D{dims[1]:.1f} x H{dims[2]:.1f} mm, volume {vol / 1000:.1f} cm3, "
          f"non-manifold edges {nm}, pieces {parts}, faces {len(base.data.polygons)}")
    return base, skull

# ------------------------------------------------------------------ preview renders
def render_views(base, skull):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x = sc.render.resolution_y = 700
    sh = sc.display.shading
    sh.light, sh.color_type = 'STUDIO', 'OBJECT'
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.show_shadows = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new("W")
    sc.world.color = (0.12, 0.12, 0.14)
    base.color = (0.50, 0.50, 0.48, 1)
    skull.color = (0.85, 0.80, 0.68, 1)

    cam = link(bpy.data.objects.new("cam", bpy.data.cameras.new("cam")))
    cam.data.type, cam.data.clip_end = 'ORTHO', 2000
    sc.camera = cam

    def shot(name, d, objs, tgt, scale):
        d = Vector(d).normalized()
        cam.data.ortho_scale = scale
        cam.location = Vector(tgt) + d * 400
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        for o in sc.objects:
            if o.type == 'MESH':
                o.hide_render = o not in objs
        sc.render.filepath = os.path.join(OUT, "renders", name + ".png")
        bpy.ops.render.render(write_still=True)

    tb = (0, 0, (Z_TOP + SPIGOT_H) / 2)
    shot("base_front", (0, -1, 0), [base], tb, 75)
    shot("base_three_quarter", (-1, -1.3, 0.6), [base], tb, 80)
    shot("base_top", (0.0001, 0, 1), [base], tb, 75)
    shot("base_bottom", (0.0001, 0, -1), [base], tb, 75)
    shot("base_gargoyle", (-0.25, -1, 0.35), [base], (0, -GARGOYLE_R, PLINTH_H + 5), 22)
    sec = base.copy(); sec.data = base.data.copy(); link(sec)
    sec.color = base.color
    boolean(sec, box("half", (0, -200, -200), (200, 200, 200)))
    sk_sec = skull.copy(); sk_sec.data = skull.data.copy(); link(sk_sec)
    sk_sec.color = skull.color
    boolean(sk_sec, box("half", (0, -200, -200), (200, 200, 200)))
    shot("base_section", (1, 0, 0), [sec, sk_sec], (0, 0, Z_TOP), 80)
    bpy.data.objects.remove(sec); bpy.data.objects.remove(sk_sec)
    ta = (0, 2, (Z_TOP + 76) / 2 + 5)
    shot("assembly_front", (0, -1, 0), [base, skull], ta, 135)
    shot("assembly_three_quarter", (-1, -1.3, 0.45), [base, skull], ta, 140)
    shot("assembly_side", (1, 0, 0), [base, skull], ta, 135)
    bpy.data.objects.remove(cam)

def write_stl(obj, path):
    """Binary STL straight from the mesh triangles (mm)."""
    import struct
    me = obj.data
    me.calc_loop_triangles()
    m = obj.matrix_world
    with open(path, "wb") as f:
        f.write(b"Halloween skull base".ljust(80, b" "))
        f.write(struct.pack("<I", len(me.loop_triangles)))
        for t in me.loop_triangles:
            vs = [m @ me.vertices[i].co for i in t.vertices]
            n = (vs[1] - vs[0]).cross(vs[2] - vs[0]).normalized()
            f.write(struct.pack("<12fH", *n, *vs[0], *vs[1], *vs[2], 0))
    print(f"wrote {path}: {len(me.loop_triangles)} triangles")

# ------------------------------------------------------------------ main
base, skull = build()
if DO_RENDER:
    render_views(base, skull)
for o in list(bpy.context.scene.objects):
    if o is not base:
        bpy.data.objects.remove(o)
bpy.ops.object.select_all(action='DESELECT')
base.select_set(True)
bpy.context.view_layer.objects.active = base
write_stl(base, os.path.join(OUT, "base.stl"))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "base.blend"))
print("done")
