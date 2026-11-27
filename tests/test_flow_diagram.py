"""Tests of the flow diagram: which step runs after each agent event, and how it is drawn."""

from scanya_ae_afa_updated0209_2_5 import flow_diagram


def test_stages_follow_the_agent_events():
    """Guard, then model, search, model, work product, model, answer."""
    events = [
        ("usage", ""),  # The guard's request: the guard is done.
        ("usage", ""),  # A request of the chat model: still the model.
        ("tool_call", "search_documentation"),
        ("tool_result", "search_documentation"),
        ("tool_call", "write_document"),
        ("tool_result", "write_document"),
        ("answer", ""),
    ]
    stage, stages = "guard", []
    for kind, tool in events:
        stage = flow_diagram.next_stage(stage, kind, tool)
        stages.append(stage)
    assert stages == ["model", "model", "search", "model", "write", "model", "answer"]
    assert flow_diagram.next_stage("guard", "blocked") == "end"


def test_diagram_marks_the_running_and_the_finished_steps():
    html = flow_diagram.diagram_html("search", {"you", "guard", "model"}, guard_on=False)
    assert 'class="flow-node active"><b>Knowledge base' in html
    assert 'class="flow-node done"><b>Model' in html
    assert 'class="flow-node done off"><b>Guard' in html
    assert 'class="flow-node"><b>Answer' in html


def test_a_step_that_just_ended_fades_from_where_it_was():
    """The search ended 0.4 s ago: it fades, starting 0.4 s in; the guard ended long ago: no fade."""
    html = flow_diagram.diagram_html("model", {"you", "guard", "search"}, fading={"search": 0.4, "guard": 9.0})
    assert "animation-delay: -0.40s\" class=\"flow-node done recent\"><b>Knowledge base" in html
    assert 'class="flow-node done"><b>Guard' in html
