from lettuce import step, world

@step(u'Given the mode is (.*)')
def given_the_mode_is(step, mode):
    world.selected_mode = mode

@step(u'When the input is set to (0|1|2)')
def when_the_input_is_set_to(step, val):
    world.last_input = val

@step(u'Then the output is (0|1|4|5)')
def then_the_output_is(step, expected_val):
    if world.selected_mode == 'pass through':
        assert expected_val == world.last_input
    elif world.selected_mode == 'offset':
        assert int(expected_val) == int(world.last_input)+1
    elif world.selected_mode == 'squared':
        assert int(expected_val) == int(world.last_input)**2
    else:
        assert False, 'Unknown mode: ' + expected_val

@step(u'this test step passes')
def given_this_test_step_passes(step):
    assert True

@step(u'this test step fails')
def this_test_step_fails(step):
    assert False
