import acc_py_index.simple.model as m


def test_ProjectListElement__normalized_name() -> None:
    prj = m.ProjectListElement('some-.name')
    assert prj.normalized_name == 'some-name'
