import xtrack as xt

ARC_NAMES = ['12', '23', '34', '45', '56', '67', '78', '81']

def get_arc_periodic_solution(collider, line_name=None, arc_name=None):

    assert collider.lhcb1.twiss_default.get('reverse', False) is False
    assert collider.lhcb2.twiss_default['reverse'] is True

    if (line_name is None or arc_name is None
        or isinstance(line_name, (list, tuple))
        or isinstance(arc_name, (list, tuple))):

        if line_name is None:
            line_name = ['lhcb1', 'lhcb2']
        if arc_name is None:
            arc_name = ARC_NAMES

        res = {'lhcb1': {}, 'lhcb2': {}}
        for ll in line_name:
            res[ll] = {}
            for aa in arc_name:
                res[ll][aa] = get_arc_periodic_solution(
                    collider, line_name=ll, arc_name=aa)
        return res


    assert arc_name in ARC_NAMES
    assert line_name in ['lhcb1', 'lhcb2']

    beam_number = line_name[-1:]
    sector_start_number = arc_name[:1]
    sector_end_number = arc_name[1:]
    start_cell = f's.cell.{arc_name}.b{beam_number}'
    end_cell = f'e.cell.{arc_name}.b{beam_number}'
    start_arc = f'e.ds.r{sector_start_number}.b{beam_number}'
    end_arc = f's.ds.l{sector_end_number}.b{beam_number}'

    line = collider[line_name]

    twinit_cell = line.twiss(
                ele_start=start_cell,
                ele_stop=end_cell,
                twiss_init='periodic',
                only_twiss_init=True)

    tw_to_end_arc = line.twiss(
        ele_start=twinit_cell.element_name,
        ele_stop=end_arc,
        twiss_init=twinit_cell,
        )

    tw_to_start_arc = line.twiss(
        ele_start=start_arc,
        ele_stop=twinit_cell.element_name,
        twiss_init=twinit_cell)

    res = xt.TwissTable.concatenate([tw_to_start_arc, tw_to_end_arc])
    res['mux'] = res['mux'] - res['mux', start_arc]
    res['muy'] = res['muy'] - res['muy', start_arc]

    return res


class ActionArcPhaseAdvanceFromCell(xt.Action):

    def __init__(self, collider, line_name, arc_name):

        self.collider = collider
        self.line_name = line_name
        self.arc_name = arc_name

    def run(self):

        tw_arc = get_arc_periodic_solution(
            self.collider, line_name=self.line_name, arc_name=self.arc_name)

        return {'table': tw_arc,
                'mux': tw_arc['mux', -1] - tw_arc['mux', 0],
                'muy': tw_arc['muy', -1] - tw_arc['muy', 0]}

def match_arc_phase_advance(collider, arc_name,
                            target_mux_b1, target_muy_b1,
                            target_mux_b2, target_muy_b2,
                            solve=True):

    assert collider.lhcb1.twiss_default.get('reverse', False) is False
    assert collider.lhcb2.twiss_default['reverse'] is True

    assert arc_name in ARC_NAMES

    action_phase_b1 = ActionArcPhaseAdvanceFromCell(
                    collider=collider, line_name='lhcb1', arc_name=arc_name)
    action_phase_b2 = ActionArcPhaseAdvanceFromCell(
                        collider=collider, line_name='lhcb2', arc_name=arc_name)

    opt=collider.match(
        solve=False,
        targets=[
            action_phase_b1.target('mux', target_mux_b1),
            action_phase_b1.target('muy', target_muy_b1),
            action_phase_b2.target('mux', target_mux_b2),
            action_phase_b2.target('muy', target_muy_b2),
        ],
        vary=[
            xt.VaryList([f'kqtf.a{arc_name}b1', f'kqtd.a{arc_name}b1',
                        f'kqtf.a{arc_name}b2', f'kqtd.a{arc_name}b2',
                        f'kqf.a{arc_name}', f'kqd.a{arc_name}'
                        ]),
        ])
    if solve:
        opt.solve()

    return opt



def propagate_optics_from_beta_star(collider, ip_name, line_name,
                                    beta_star_x, beta_star_y,
                                    ele_start, ele_stop):

    assert collider.lhcb1.twiss_default.get('reverse', False) is False
    assert collider.lhcb2.twiss_default['reverse'] is True
    assert collider.lhcb1.element_names[1] == 'ip1'
    assert collider.lhcb2.element_names[1] == 'ip1.l1'
    assert collider.lhcb1.element_names[-2] == 'ip1.l1'
    assert collider.lhcb2.element_names[-2] == 'ip1'

    if ip_name == 'ip1':
        ele_stop_left = 'ip1.l1'
        ele_start_right = 'ip1'
    else:
        ele_stop_left = ip_name
        ele_start_right = ip_name

    tw_left = collider[line_name].twiss(ele_start=ele_start, ele_stop=ele_stop_left,
                    twiss_init=xt.TwissInit(line=collider[line_name],
                                            element_name=ele_stop_left,
                                            betx=beta_star_x,
                                            bety=beta_star_y))
    tw_right = collider[line_name].twiss(ele_start=ele_start_right, ele_stop=ele_stop,
                        twiss_init=xt.TwissInit(line=collider[line_name],
                                                element_name=ele_start_right,
                                                betx=beta_star_x,
                                                bety=beta_star_y))

    tw_ip = xt.TwissTable.concatenate([tw_left, tw_right])

    return tw_ip

class ActionPhase_23_34(xt.Action):

    def __init__(self, collider):
        self.collider = collider

    def run(self):
        try:
            tw_arc = get_arc_periodic_solution(self.collider, arc_name=['23', '34'])
        except ValueError:
            # Twiss failed
            return {
                'mux_23_34_b1': 1e100,
                'muy_23_34_b1': 1e100,
                'mux_23_34_b2': 1e100,
                'muy_23_34_b2': 1e100,
            }
        tw_23_b1 = tw_arc['lhcb1']['23']
        tw_23_b2 = tw_arc['lhcb2']['23']
        mux_23_b1 = tw_23_b1['mux', 's.ds.l3.b1'] - tw_23_b1['mux', 'e.ds.r2.b1']
        muy_23_b1 = tw_23_b1['muy', 's.ds.l3.b1'] - tw_23_b1['muy', 'e.ds.r2.b1']
        mux_23_b2 = tw_23_b2['mux', 's.ds.l3.b2'] - tw_23_b2['mux', 'e.ds.r2.b2']
        muy_23_b2 = tw_23_b2['muy', 's.ds.l3.b2'] - tw_23_b2['muy', 'e.ds.r2.b2']

        tw34_b1 = tw_arc['lhcb1']['34']
        tw34_b2 = tw_arc['lhcb2']['34']
        mux_34_b1 = tw34_b1['mux', 's.ds.l4.b1'] - tw34_b1['mux', 'e.ds.r3.b1']
        muy_34_b1 = tw34_b1['muy', 's.ds.l4.b1'] - tw34_b1['muy', 'e.ds.r3.b1']
        mux_34_b2 = tw34_b2['mux', 's.ds.l4.b2'] - tw34_b2['mux', 'e.ds.r3.b2']
        muy_34_b2 = tw34_b2['muy', 's.ds.l4.b2'] - tw34_b2['muy', 'e.ds.r3.b2']

        return {
            'mux_23_34_b1': mux_23_b1 + mux_34_b1,
            'muy_23_34_b1': muy_23_b1 + muy_34_b1,
            'mux_23_34_b2': mux_23_b2 + mux_34_b2,
            'muy_23_34_b2': muy_23_b2 + muy_34_b2
        }

class ActionPhase_67_78(xt.Action):

    def __init__(self, collider):
        self.collider = collider

    def run(self):
        try:
            tw_arc = get_arc_periodic_solution(self.collider, arc_name=['67', '78'])
        except ValueError:
            # Twiss failed
            return {
                'mux_67_78_b1': 1e100,
                'muy_67_78_b1': 1e100,
                'mux_67_78_b2': 1e100,
                'muy_67_78_b2': 1e100,
            }
        tw_67_b1 = tw_arc['lhcb1']['67']
        tw_67_b2 = tw_arc['lhcb2']['67']
        mux_67_b1 = tw_67_b1['mux', 's.ds.l7.b1'] - tw_67_b1['mux', 'e.ds.r6.b1']
        muy_67_b1 = tw_67_b1['muy', 's.ds.l7.b1'] - tw_67_b1['muy', 'e.ds.r6.b1']
        mux_67_b2 = tw_67_b2['mux', 's.ds.l7.b2'] - tw_67_b2['mux', 'e.ds.r6.b2']
        muy_67_b2 = tw_67_b2['muy', 's.ds.l7.b2'] - tw_67_b2['muy', 'e.ds.r6.b2']

        tw78_b1 = tw_arc['lhcb1']['78']
        tw78_b2 = tw_arc['lhcb2']['78']
        mux_78_b1 = tw78_b1['mux', 's.ds.l8.b1'] - tw78_b1['mux', 'e.ds.r7.b1']
        muy_78_b1 = tw78_b1['muy', 's.ds.l8.b1'] - tw78_b1['muy', 'e.ds.r7.b1']
        mux_78_b2 = tw78_b2['mux', 's.ds.l8.b2'] - tw78_b2['mux', 'e.ds.r7.b2']
        muy_78_b2 = tw78_b2['muy', 's.ds.l8.b2'] - tw78_b2['muy', 'e.ds.r7.b2']

        return {
            'mux_67_78_b1': mux_67_b1 + mux_78_b1,
            'muy_67_78_b1': muy_67_b1 + muy_78_b1,
            'mux_67_78_b2': mux_67_b2 + mux_78_b2,
            'muy_67_78_b2': muy_67_b2 + muy_78_b2
        }

def change_phase_non_ats_arcs(collider,
    d_mux_15_b1=None, d_muy_15_b1=None, d_mux_15_b2=None, d_muy_15_b2=None,
    solve=True):

    assert (d_mux_15_b1 is not None or d_muy_15_b1 is not None
            or d_mux_15_b2 is not None or d_muy_15_b2 is not None), (
        "At least one of the phase advance changes must be non-zero"
            )

    action_phase_23_34 = ActionPhase_23_34(collider)
    action_phase_67_78 = ActionPhase_67_78(collider)

    phase_23_34_0 = action_phase_23_34.run()
    phase_67_78_0 = action_phase_67_78.run()

    mux_23_34_b1_target = phase_23_34_0['mux_23_34_b1']
    muy_23_34_b1_target = phase_23_34_0['muy_23_34_b1']
    mux_23_34_b2_target = phase_23_34_0['mux_23_34_b2']
    muy_23_34_b2_target = phase_23_34_0['muy_23_34_b2']
    mux_67_78_b1_target = phase_67_78_0['mux_67_78_b1']
    muy_67_78_b1_target = phase_67_78_0['muy_67_78_b1']
    mux_67_78_b2_target = phase_67_78_0['mux_67_78_b2']
    muy_67_78_b2_target = phase_67_78_0['muy_67_78_b2']

    n_contraints = 0
    targets = []
    if d_mux_15_b1 is not None:
        mux_23_34_b1_target += d_mux_15_b1
        mux_67_78_b1_target -= d_mux_15_b1
        targets.append(action_phase_23_34.target('mux_23_34_b1', mux_23_34_b1_target))
        targets.append(action_phase_67_78.target('mux_67_78_b1', mux_67_78_b1_target))
        n_contraints += 1

    if d_muy_15_b1 is not None:
        muy_23_34_b1_target += d_muy_15_b1
        muy_67_78_b1_target -= d_muy_15_b1
        targets.append(action_phase_23_34.target('muy_23_34_b1', muy_23_34_b1_target))
        targets.append(action_phase_67_78.target('muy_67_78_b1', muy_67_78_b1_target))
        n_contraints += 1

    if d_mux_15_b2 is not None:
        mux_23_34_b2_target += d_mux_15_b2
        mux_67_78_b2_target -= d_mux_15_b2
        targets.append(action_phase_23_34.target('mux_23_34_b2', mux_23_34_b2_target))
        targets.append(action_phase_67_78.target('mux_67_78_b2', mux_67_78_b2_target))
        n_contraints += 1

    if d_muy_15_b2 is not None:
        muy_23_34_b2_target += d_muy_15_b2
        muy_67_78_b2_target -= d_muy_15_b2
        targets.append(action_phase_23_34.target('muy_23_34_b2', muy_23_34_b2_target))
        targets.append(action_phase_67_78.target('muy_67_78_b2', muy_67_78_b2_target))
        n_contraints += 1

    vary = [
        xt.VaryList(['kqf.a23', 'kqd.a23', 'kqf.a34', 'kqd.a34'], weight=5),
        xt.VaryList(['kqf.a67', 'kqd.a67', 'kqf.a78', 'kqd.a78'], weight=5),
    ]
    if n_contraints > 2:
        vary += [
            xt.VaryList(['kqtf.a23b1', 'kqtd.a23b1', 'kqtf.a34b1', 'kqtd.a34b1',
                        'kqtf.a23b2', 'kqtd.a23b2', 'kqtf.a34b2', 'kqtd.a34b2']),
            xt.VaryList(['kqtf.a67b1', 'kqtd.a67b1', 'kqtf.a78b1', 'kqtd.a78b1',
                        'kqtf.a67b2', 'kqtd.a67b2', 'kqtf.a78b2', 'kqtd.a78b2']),
        ]

    opt = collider.match(
        solve=False,
        solver_options={'n_bisections': 5},
        vary=vary,
        targets=targets,
    )

    if solve:
        opt.solve()

    return opt