import numpy as np
from cpymad.madx import Madx
import xtrack as xt

mad = Madx()
mad.input("""
beam, particle=proton, pc = 14.0;
BRHO      = BEAM->PC * 3.3356;
""")
mad.call("../../test_data/ps_sftpro/ps.seq")
mad.call("../../test_data/ps_sftpro/ps_hs_sftpro.str")
mad.use('ps')
twm = mad.twiss()

line = xt.Line.from_madx_sequence(mad.sequence.ps, allow_thick=True,
                                  deferred_expressions=True,
                                  )
line.particle_ref = xt.Particles(mass0=xt.PROTON_MASS_EV,
                                    q0=1, gamma0=mad.sequence.ps.beam.gamma)
line.twiss_default['method'] = '4d'

tw = line.twiss()

opt = line.match(
    solve=False,
    vary=[xt.VaryList(['kf', 'kd'], step=1e-5)],
    targets=[xt.TargetSet(qx=6.255278, qy=6.29826, tol=1e-7)],
)
opt.solve()


r0 = np.linspace(0, 100, 50)
p = line.build_particles(
    x_norm=r0*np.cos(np.pi/20.),
    px_norm=r0*np.sin(np.pi/20.),
    nemitt_x=1e-6, nemitt_y=1e-6)

line.track(p, num_turns=1000, turn_by_turn_monitor=True)
mon = line.record_last_track

tw_mt = line.twiss(co_guess={'x': 0.025}, num_turns=4)
tw_core = line.twiss(co_guess={'x': 0.0}, num_turns=0)

# Inspect and plot
tw_start_turns = tw_mt.rows['_turn_.*']
tw_start_turns.show()
import matplotlib.pyplot as plt
plt.close('all')
plt.figure(1)
plt.plot(mon.x.flatten(), mon.px.flatten(), '.', markersize=1)
plt.plot(tw_start_turns.x, tw_start_turns.px, '*')
plt.ylim(-0.004, 0.004)
plt.xlim(-0.08, 0.08)

plt.figure(2)
ax1 = plt.subplot(3,1,1)
plt.plot(tw_mt.s, tw_mt.x)
plt.plot(tw_mt.s, tw_mt.y)
plt.subplot(3,1,2, sharex=ax1)
plt.plot(tw_mt.s, tw_mt.betx)
plt.plot(tw_core.s, tw_core.betx)
plt.subplot(3,1,3, sharex=ax1)
plt.plot(tw_mt.s, tw_mt.bety)
plt.plot(tw_core.s, tw_core.bety)

plt.show()

assert len(tw_mt.rows['_turn.*']) == 4
assert len(tw_mt.rows['_end_poi.*']) == 1

assert '_turn_0' in tw_mt.name
assert '_turn_1' in tw_mt.name
assert '_turn_2' in tw_mt.name
assert '_turn_3' in tw_mt.name

assert np.all(np.diff(tw_mt.s) >= 0)

circum = line.get_length()

assert np.isclose(tw_mt.s[-1], 4 * circum, atol=1e-10, rtol=0)
assert np.isclose(tw_mt['s', '_turn_0'], 0, atol=1e-10, rtol=0)
assert np.isclose(tw_mt['s', '_turn_1'], circum, atol=1e-10, rtol=0)
assert np.isclose(tw_mt['s', '_turn_2'], 2 * circum, atol=1e-10, rtol=0)
assert np.isclose(tw_mt['s', '_turn_3'], 3 * circum, atol=1e-10, rtol=0)
assert np.isclose(tw_mt['s', '_end_point'], 4 * circum, atol=1e-10, rtol=0)

assert np.isclose(tw_mt.mux[-1], 4 * tw.mux[-1], rtol=0, atol=0.05)
assert np.isclose(tw_mt.muy[-1], 4 * tw.muy[-1], rtol=0, atol=0.05)

assert 'qx' in tw
assert 'qy' in tw
assert 'qx' not in tw_mt
assert 'qy' not in tw_mt

assert tw_mt['x', '_turn_0'] > 2e-2
assert np.abs(tw_mt['x', '_turn_1']) < 1e-2
assert tw_mt['x', '_turn_2'] < -2e-2
assert np.abs(tw_mt['x', '_turn_3']) < 1e-2

assert np.isclose(tw_mt.x[-1], tw_mt.x[0], rtol=0, atol=1e-8)
assert np.isclose(tw_mt.y[-1], tw_mt.y[0], rtol=0, atol=1e-8)
assert np.isclose(tw_mt.px[-1], tw_mt.px[0], rtol=0, atol=1e-10)
assert np.isclose(tw_mt.py[-1], tw_mt.py[0], rtol=0, atol=1e-10)
assert np.isclose(tw_mt.betx[-1], tw_mt.betx[0], rtol=0, atol=1e-5)
assert np.isclose(tw_mt.bety[-1], tw_mt.bety[0], rtol=0, atol=1e-5)
assert np.isclose(tw_mt.alfx[-1], tw_mt.alfx[0], rtol=0, atol=1e-5)
assert np.isclose(tw_mt.alfy[-1], tw_mt.alfy[0], rtol=0, atol=1e-5)