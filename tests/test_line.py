import numpy as np
import xtrack as xt

def test_simplification_methods():

    line = xt.Line(
        elements = [xt.Drift(length=1) for _ in range(5)]
    )
    line.insert_element(element=xt.Cavity(), name="cav", at_s=3.3)
    line.merge_consecutive_drifts(inplace=True)
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5
    assert np.isclose(line[0].length, 3.3, rtol=0, atol=1e-12)
    assert isinstance(line[1], xt.Cavity)
    assert np.isclose(line[2].length, 1.7, rtol=0, atol=1e-12)

    line.insert_element(element=xt.Drift(length=0), name="marker", at_s=3.3)
    assert len(line.element_names) == 4
    line.remove_zero_length_drifts(inplace=True)
    assert len(line.element_names) == 3

    line.insert_element(element=xt.Multipole(knl=[1, 0, 3], ksl=[0, 20, 0]), name="m1", at_s=3.3)
    line.insert_element(element=xt.Multipole(knl=[4, 2], ksl=[10, 40]), name="m2", at_s=3.3)
    assert len(line.element_names) == 5
    line.merge_consecutive_multipoles(inplace=True)
    assert len(line.element_names) == 4
    assert np.allclose(line[1].knl, [5,2,3], rtol=0, atol=1e-15)
    assert np.allclose(line[1].ksl, [10,60,0], rtol=0, atol=1e-15)

    line.remove_inactive_multipoles(inplace=True)
    assert len(line.element_names) == 4
    line[1].knl[:] = 0
    line[1].ksl[:] = 0
    line.remove_inactive_multipoles(inplace=True)
    assert len(line.element_names) == 3

def test_insert():

    line0 = xt.Line(
        elements = [xt.Drift(length=1) for _ in range(5)]
    )

    line = line0.copy()
    assert np.all(np.array([0,1,2,3,4]) == np.array(line.get_s_elements()))
    assert np.all(np.array([0,1,2,3,4]) == np.array(line.get_s_elements(mode='upstream')))
    assert np.all(np.array([1,2,3,4,5]) == np.array(line.get_s_elements(mode='downstream')))

    assert line.get_s_position(at_elements='e3') == 3.
    assert np.isscalar(line.get_s_position(at_elements='e3'))
    assert len(line.get_s_position(at_elements=['e3'])) == 1
    assert np.all(np.array([4,2]) == np.array(line.get_s_position(at_elements=['e4', 'e2'])))

    line.insert_element(element=xt.Cavity(), name="cav", at_s=3.3)
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5
    assert line.get_s_position('cav') == 3.3
    assert len(line.elements) == 7

    line = line0.copy()
    line.insert_element(element=xt.Drift(length=0.2), at_s=0.11, name='inserted_drift')
    assert line.get_s_position('inserted_drift') == 0.11
    assert len(line.elements) == 7
    assert np.all([nn==nnref for nn, nnref in list(zip(line.element_names,
                ['e0_part0', 'inserted_drift', 'e0_part1', 'e1', 'e2', 'e3', 'e4']))])
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5

    line = line0.copy()
    line.insert_element(element=xt.Drift(length=0.2), at_s=0.95, name='inserted_drift')
    assert line.get_s_position('inserted_drift') == 0.95
    assert len(line.elements) == 6
    assert np.all([nn==nnref for nn, nnref in list(zip(line.element_names,
                ['e0_part0', 'inserted_drift', 'e1_part1', 'e2', 'e3', 'e4']))])
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5

    line = line0.copy()
    line.insert_element(element=xt.Drift(length=0.2), at_s=1.0, name='inserted_drift')
    assert line.get_s_position('inserted_drift') == 1.
    assert len(line.elements) == 6
    assert np.all([nn==nnref for nn, nnref in list(zip(line.element_names,
                ['e0', 'inserted_drift', 'e1_part1', 'e2', 'e3', 'e4']))])
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5

    line = line0.copy()
    line.insert_element(element=xt.Drift(length=0.2), at_s=0.8, name='inserted_drift')
    assert line.get_s_position('inserted_drift') == 0.8
    assert len(line.elements) == 6
    assert np.all([nn==nnref for nn, nnref in list(zip(line.element_names,
                ['e0_part0', 'inserted_drift', 'e1', 'e2', 'e3', 'e4']))])
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5

    line = line0.copy()
    line.insert_element(element=xt.LimitEllipse(a=1, b=1), at_s=2.1, name='aper')
    assert line.get_s_position('aper') == 2.1
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5
    assert np.all([nn==nnref for nn, nnref in list(zip(line.element_names,
                ['e0', 'e1', 'e2_part0', 'aper', 'e2_part1', 'e3', 'e4']))])
    line.insert_element(element=xt.Drift(length=0.8), at_s=1.9, name="newdrift")
    assert line.get_s_position('newdrift') == 1.9
    assert np.all([nn==nnref for nn, nnref in list(zip(line.element_names,
                ['e0', 'e1_part0', 'newdrift', 'e2_part1_part1', 'e3', 'e4']))])

    # Check preservation of markers
    elements = []
    enames = []

    for ii in range(5):
        elements.append(xt.Drift(length=1))
        enames.append(f'd{ii}')
        elements.append(xt.Drift(length=0))
        enames.append(f'm{ii}')

    line = xt.Line(elements=elements, element_names=enames)
    line.insert_element(element=xt.Drift(length=1.), at_s=1.0, name='inserted_drift')
    assert line.get_s_position('inserted_drift') == 1.
    assert len(line.elements) == 10
    assert np.all([nn==nnref for nn, nnref in list(zip(line.element_names,
        ['d0', 'm0', 'inserted_drift', 'm1', 'd2', 'm2', 'd3', 'm3', 'd4', 'm4']))])
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5

    line.insert_element(element=xt.Cavity(), at_s=3.0, name='cav0')
    line.insert_element(element=xt.Cavity(), at_s=3.0, name='cav1')
    assert len(line.elements) == 12
    assert np.all([nn==nnref for nn, nnref in list(zip(line.element_names,
        ['d0', 'm0', 'inserted_drift', 'm1', 'd2', 'cav1', 'cav0', 'm2', 'd3',
        'm3', 'd4', 'm4']))])
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5
    assert line.get_s_position('cav0') == 3.
    assert line.get_s_position('cav1') == 3.

    line = xt.Line(elements=elements, element_names=enames)
    line.insert_element(element=xt.Drift(length=0.2), at_s=0.95, name='inserted_drift')
    assert line.get_s_position('inserted_drift') == 0.95
    assert len(line.elements) == 10
    assert np.all([nn==nnref for nn, nnref in list(zip(line.element_names,
                ['d0_part0', 'inserted_drift', 'd1_part1', 'm1', 'd2', 'm2', 'd3',
                'm3', 'd4', 'm4']))])
    assert line.get_length() == line.get_s_elements(mode='downstream')[-1] == 5